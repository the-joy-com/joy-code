import io
import json

import pytest

import task_ledger


@pytest.fixture
def state(tmp_path):
    """A state folder whose ledger bootstraps with a script that succeeds or fails on demand."""
    script = tmp_path / "init.sh"
    script.write_text('#!/bin/sh\necho "bootstrap ran"\nexit "$(cat "$(dirname "$0")/exit_code")"\n')
    script.chmod(0o755)
    (tmp_path / "exit_code").write_text("0")
    state = str(tmp_path / "state")
    assert run(state, "init", "--bootstrap", str(script)) == 0
    return state


class Terminal(io.StringIO):
    """Stdin of a human typing at an interactive terminal."""

    def isatty(self):
        return True


def type_at_terminal(monkeypatch, text):
    monkeypatch.setattr("sys.stdin", Terminal(text + "\n"))


def draft(tmp_path, title, verify=None, folder="instructions/drafts", **sections):
    """A spec draft as an agent writes it from instruction_template.md."""
    verify = verify or f'echo "checking {title}"; test -e "{tmp_path}/done/{title}"'
    body = {
        "TASK": f"Running `do {title}` prints `{title}` and exits 0.",
        "SCOPE": "- `cli/task_ledger.py`",
        "DONE WHEN": f"The verification command exits 0.\n\n```bash\n{verify}\n```",
        "STATE": "",
        "EVIDENCE": "",
    }
    body.update({k.replace("_", " "): v for k, v in sections.items()})
    text = f"# {title}\n\n" + "".join(f"## {name}\n\n{content}\n\n" for name, content in body.items() if content is not None)
    path = tmp_path / folder / f"{title}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return str(path)


def finish_work(tmp_path, title):
    (tmp_path / "done").mkdir(exist_ok=True)
    (tmp_path / "done" / title).write_text("")


@pytest.fixture
def add(state, tmp_path, monkeypatch):
    """Approve a spec draft as a human would; by default the work is then done, so it can pass."""

    def add(title, done=True):
        next_id = f"T-{task_ledger.load(state)['next_id']}"
        type_at_terminal(monkeypatch, next_id)
        code = run(state, "add", "--spec", draft(tmp_path, title))
        if done:
            finish_work(tmp_path, title)
        return code

    return add


def run(state, command, *args):
    return task_ledger.main([command, "--state", state, *args])


def ledger(state):
    return json.loads(task_ledger.ledger_path(state).read_text())


def task(state, tid):
    return next(t for t in ledger(state)["tasks"] if t["id"] == tid)


def archive(state):
    path = task_ledger.archive_path(state)
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def set_bootstrap_exit(state, code):
    (task_ledger.ledger_path(state).parent.parent / "exit_code").write_text(str(code))


def test_init_creates_empty_ledger_and_refuses_to_overwrite(state):
    assert ledger(state)["tasks"] == []
    assert run(state, "init", "--bootstrap", "./init.sh") == 1


def test_commands_fail_without_ledger(tmp_path, capsys):
    assert run(str(tmp_path), "status") == 1
    assert "joy task init" in capsys.readouterr().err


def test_add_numbers_tasks_as_not_started(state, add):
    add("first")
    add("second")
    assert [(t["id"], t["state"]) for t in ledger(state)["tasks"]] == [("T-1", "not_started"), ("T-2", "not_started")]


def test_activation_is_refused_while_vcr_below_one(state, capsys, add):
    add("first")
    add("second")
    assert run(state, "activate", "T-1") == 0
    assert run(state, "activate", "T-2") == 1
    assert "VCR is 0/1" in capsys.readouterr().err
    assert task(state, "T-2")["state"] == "not_started"


def test_blocked_task_still_blocks_others_but_can_resume(state, add):
    add("first")
    add("second")
    run(state, "activate", "T-1")
    assert run(state, "block", "T-1", "--reason", "needs a human") == 0
    assert task(state, "T-1")["blocker"] == "needs a human"
    assert run(state, "activate", "T-2") == 1
    assert run(state, "activate", "T-1") == 0
    assert "blocker" not in task(state, "T-1")


def test_pass_records_evidence_and_unlocks_next_activation(state, add):
    add("first")
    add("second")
    run(state, "activate", "T-1")
    assert run(state, "pass", "T-1") == 0
    [archived] = archive(state)
    assert archived["id"] == "T-1" and archived["state"] == "passing"
    assert archived["evidence"]["exit_code"] == 0
    assert archived["evidence"]["output_tail"] == ["bootstrap ran"]
    assert run(state, "activate", "T-2") == 0


def test_pass_is_refused_when_bootstrap_fails(state, add):
    add("first")
    run(state, "activate", "T-1")
    set_bootstrap_exit(state, 12)
    assert run(state, "pass", "T-1") == 1
    assert task(state, "T-1")["state"] == "active"


def test_pass_requires_an_active_task(state, add):
    add("first")
    assert run(state, "pass", "T-1") == 1


def test_dropped_task_leaves_the_vcr_denominator(state, monkeypatch, add):
    add("first")
    add("second")
    run(state, "activate", "T-1")
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "drop", "T-1", "--reason", "human cancelled it") == 0
    assert run(state, "activate", "T-2") == 0


def test_status_reports_vcr(state, capsys, add):
    add("first")
    run(state, "activate", "T-1")
    capsys.readouterr()
    assert run(state, "status", "--json") == 0
    status = json.loads(capsys.readouterr().out)
    assert status["vcr"] == {"passing": 0, "activated": 1}
    assert status["wip_limit"] == 1
    assert [t["id"] for t in status["current"]] == ["T-1"]
    assert run(state, "status") == 0
    out = capsys.readouterr().out
    assert "VCR 0/1, WIP limit 1 (new activations blocked)" in out
    assert "active: T-1 first" in out


def test_status_fails_on_hand_edited_ledger_breaking_wip1(state, add):
    add("first")
    add("second")
    data = ledger(state)
    for t in data["tasks"]:
        t["state"] = "active"
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


def test_status_fails_on_passing_task_without_evidence(state, add):
    add("first")
    data = ledger(state)
    data["tasks"][0]["state"] = "passing"
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


def test_finished_tasks_leave_the_ledger_but_still_count(state, capsys, monkeypatch, add):
    for title in ("first", "second", "third"):
        add(title)
    run(state, "activate", "T-1")
    run(state, "pass", "T-1")
    run(state, "activate", "T-2")
    type_at_terminal(monkeypatch, "T-2")
    run(state, "drop", "T-2", "--reason", "human cancelled it")
    data = ledger(state)
    assert [t["id"] for t in data["tasks"]] == ["T-3"]
    assert data["archived"] == {"passing": 1, "dropped": 1}
    assert [t["id"] for t in archive(state)] == ["T-1", "T-2"]
    run(state, "activate", "T-3")
    capsys.readouterr()
    run(state, "status", "--json")
    status = json.loads(capsys.readouterr().out)
    assert status == {
        "vcr": {"passing": 1, "activated": 2},
        "wip_limit": 1,
        "current": [task(state, "T-3")],
        "not_started": [],
    }


def test_evidence_keeps_only_the_output_tail(state, add):
    script = task_ledger.ledger_path(state).parent.parent / "init.sh"
    script.write_text("#!/bin/sh\nfor i in 1 2 3 4 5 6; do echo line $i; done\n")
    add("first")
    run(state, "activate", "T-1")
    run(state, "pass", "T-1")
    assert archive(state)[0]["evidence"]["output_tail"] == ["line 4", "line 5", "line 6"]


def test_ids_keep_increasing_after_archiving(state, add):
    add("first")
    run(state, "activate", "T-1")
    run(state, "pass", "T-1")
    add("second")
    assert [t["id"] for t in ledger(state)["tasks"]] == ["T-2"]


def test_ledger_without_archive_fields_is_migrated(state, add):
    task_ledger.ledger_path(state).write_text(json.dumps({
        "version": 1,
        "bootstrap": "./init.sh",
        "tasks": [
            {"id": "T-1", "title": "old", "state": "passing", "evidence": {"exit_code": 0}},
            {"id": "T-2", "title": "open", "state": "not_started"},
        ],
    }))
    assert add("new") == 0
    data = ledger(state)
    assert [t["id"] for t in data["tasks"]] == ["T-2", "T-3"]
    assert data["archived"] == {"passing": 1, "dropped": 0}
    assert data["next_id"] == 4


def test_drop_is_refused_without_an_interactive_terminal(state, monkeypatch, capsys, add):
    add("first")
    monkeypatch.setattr("sys.stdin", io.StringIO("T-1\n"))
    assert run(state, "drop", "T-1", "--reason", "agent gave up") == 1
    assert "needs a human" in capsys.readouterr().err
    assert task(state, "T-1")["state"] == "not_started"


def test_drop_is_refused_when_confirmation_does_not_match(state, monkeypatch, add):
    add("first")
    type_at_terminal(monkeypatch, "yes")
    assert run(state, "drop", "T-1", "--reason", "typo") == 1
    assert task(state, "T-1")["state"] == "not_started"


def test_human_can_raise_wip_to_work_on_two_tasks(state, monkeypatch, add):
    for title in ("first", "second", "third"):
        add(title)
    type_at_terminal(monkeypatch, "2")
    assert run(state, "wip", "2") == 0
    assert ledger(state)["wip_limit"] == 2
    assert run(state, "activate", "T-1") == 0
    assert run(state, "activate", "T-2") == 0
    assert run(state, "activate", "T-3") == 1
    assert run(state, "status") == 0


def test_wip_is_refused_without_an_interactive_terminal(state, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
    assert run(state, "wip", "2") == 1
    assert "needs a human" in capsys.readouterr().err
    assert "wip_limit" not in ledger(state)


def test_wip_is_refused_when_confirmation_does_not_match(state, monkeypatch):
    type_at_terminal(monkeypatch, "3")
    assert run(state, "wip", "2") == 1
    assert "wip_limit" not in ledger(state)


def test_wip_cannot_go_below_the_work_in_progress(state, monkeypatch, add):
    for title in ("first", "second"):
        add(title)
    type_at_terminal(monkeypatch, "2")
    run(state, "wip", "2")
    run(state, "activate", "T-1")
    run(state, "activate", "T-2")
    type_at_terminal(monkeypatch, "1")
    assert run(state, "wip", "1") == 1
    assert run(state, "wip", "0") == 1
    assert ledger(state)["wip_limit"] == 2


def test_status_fails_on_hand_edited_wip_limit(state):
    data = ledger(state)
    data["wip_limit"] = 0
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


@pytest.mark.parametrize("limit", ["two", "1.5"])
def test_wip_rejects_a_limit_that_is_not_a_whole_number(state, limit):
    with pytest.raises(SystemExit) as exc:
        run(state, "wip", limit)
    assert exc.value.code == 2
    assert "wip_limit" not in ledger(state)


@pytest.mark.parametrize("limit", ["2", 2.5, True])
def test_status_fails_on_hand_edited_wip_limit_that_is_not_a_whole_number(state, limit):
    data = ledger(state)
    data["wip_limit"] = limit
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


def spec_file(tmp_path, tid):
    return tmp_path / "instructions" / f"{tid}.md"


def test_add_without_a_spec_is_not_possible(state):
    with pytest.raises(SystemExit) as exc:
        run(state, "add", "first")
    assert exc.value.code == 2


def test_add_is_refused_without_an_interactive_terminal(state, tmp_path, monkeypatch, capsys):
    path = draft(tmp_path, "first")
    monkeypatch.setattr("sys.stdin", io.StringIO("T-1\n"))
    assert run(state, "add", "--spec", path) == 1
    assert "needs a human" in capsys.readouterr().err
    assert ledger(state)["tasks"] == []
    assert not spec_file(tmp_path, "T-1").exists()


def test_add_is_refused_when_confirmation_does_not_match(state, tmp_path, monkeypatch):
    path = draft(tmp_path, "first")
    type_at_terminal(monkeypatch, "yes")
    assert run(state, "add", "--spec", path) == 1
    assert ledger(state)["tasks"] == []


def test_add_shows_the_draft_then_writes_the_spec_named_after_the_task_id(state, tmp_path, monkeypatch, capsys):
    path = draft(tmp_path, "first")
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "add", "--spec", path) == 0
    out = capsys.readouterr().out
    assert "Running `do first`" in out and 'test -e' in out
    spec = spec_file(tmp_path, "T-1").read_text()
    assert spec.startswith("# T-1. first\n")
    assert "## SCOPE" in spec and "- Current state: `not_started`" in spec
    assert "exited 1" in spec and "checking first" in spec
    t = task(state, "T-1")
    assert t["title"] == "first"
    assert t["spec"]["path"] == str(spec_file(tmp_path, "T-1"))
    assert t["spec"]["verify"].startswith('echo "checking first"')
    assert t["before"]["exit_code"] == 1
    assert not (tmp_path / "instructions" / "drafts" / "first.md").exists()


@pytest.mark.parametrize("sections, error", [
    ({"SCOPE": None}, "sections"),
    ({"TASK": "<what the user observes>"}, "placeholder"),
    ({"SCOPE": "Somewhere in cli."}, "SCOPE"),
    ({"DONE_WHEN": "Tests pass."}, "bash"),
    ({"DONE_WHEN": "```bash\ntrue\n```\n\n```bash\ntrue\n```"}, "bash"),
])
def test_add_refuses_an_incomplete_draft(state, tmp_path, monkeypatch, capsys, sections, error):
    path = draft(tmp_path, "first", **sections)
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "add", "--spec", path) == 1
    assert error in capsys.readouterr().err
    assert ledger(state)["tasks"] == []


def test_placeholder_check_ignores_redirections_in_the_verification_command(state, tmp_path, monkeypatch):
    path = draft(tmp_path, "first", verify=f'grep -q x < "{tmp_path}/missing" > /dev/null')
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "add", "--spec", path) == 0


def test_add_refuses_a_verification_command_that_already_passes(state, tmp_path, monkeypatch, capsys):
    path = draft(tmp_path, "first", verify="true")
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "add", "--spec", path) == 1
    assert "already passes" in capsys.readouterr().err
    assert ledger(state)["tasks"] == []
    assert not spec_file(tmp_path, "T-1").exists()
    assert (tmp_path / "instructions" / "drafts" / "first.md").exists()


def test_activate_and_pass_refuse_a_spec_changed_after_approval(state, tmp_path, add, capsys):
    add("first")
    path = spec_file(tmp_path, "T-1")
    path.write_text(path.read_text().replace("- `cli/task_ledger.py`", "- `cli/`"))
    assert run(state, "activate", "T-1") == 1
    assert "changed since it was approved" in capsys.readouterr().err
    path.write_text(path.read_text().replace("- `cli/`", "- `cli/task_ledger.py`"))
    assert run(state, "activate", "T-1") == 0
    path.write_text(path.read_text().replace("exits 0.", "exits 0 or 1."))
    assert run(state, "pass", "T-1") == 1
    assert task(state, "T-1")["state"] == "active"


def test_edits_to_state_and_evidence_are_overwritten_not_refused(state, tmp_path, add):
    add("first")
    path = spec_file(tmp_path, "T-1")
    path.write_text(path.read_text() + "\nall good, trust me\n")
    assert run(state, "activate", "T-1") == 0
    assert "trust me" not in path.read_text()
    assert "- Current state: `active`" in path.read_text()


def test_pass_runs_the_task_verification_command_too(state, tmp_path, add, capsys):
    add("first", done=False)
    run(state, "activate", "T-1")
    assert run(state, "pass", "T-1") == 1
    assert "verification" in capsys.readouterr().err
    assert task(state, "T-1")["state"] == "active"
    finish_work(tmp_path, "first")
    assert run(state, "pass", "T-1") == 0
    [archived] = archive(state)
    assert archived["evidence"]["verification"]["exit_code"] == 0
    assert archived["evidence"]["verification"]["output_tail"] == ["checking first"]
    spec = spec_file(tmp_path, "T-1").read_text()
    assert "- Current state: `passing`" in spec
    assert "exited 0" in spec


def test_status_fails_on_passing_task_without_verification_evidence(state, add):
    add("first")
    data = ledger(state)
    data["tasks"][0]["state"] = "passing"
    data["tasks"][0]["evidence"] = {"exit_code": 0}
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


def test_a_task_without_a_spec_cannot_be_started(state, capsys):
    data = ledger(state)
    data["tasks"].append({"id": "T-1", "title": "legacy", "state": "not_started"})
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "activate", "T-1") == 1
    assert "no approved spec" in capsys.readouterr().err


@pytest.mark.parametrize("state_dir, instructions", [
    ("harness/state", "harness/instructions"),
    ("harness/state/note-taker", "harness/instructions/note-taker"),
])
def test_instructions_folder_mirrors_the_state_folder(state_dir, instructions):
    assert task_ledger.instructions_dir(state_dir) == task_ledger.Path(instructions)


@pytest.mark.parametrize("folder", ["elsewhere", "instructions", "instructions/drafts/nested"])
def test_add_refuses_a_draft_outside_the_drafts_folder(state, tmp_path, monkeypatch, capsys, folder):
    path = draft(tmp_path, "first", folder=folder)
    # Refused before the human is asked: no terminal is needed to see the error.
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert run(state, "add", "--spec", path) == 1
    err = capsys.readouterr().err
    assert str(tmp_path / "instructions" / "drafts") in err and "needs a human" not in err
    assert ledger(state)["tasks"] == []
    assert (tmp_path / folder / "first.md").exists()


def test_add_accepts_a_draft_in_the_application_drafts_folder(tmp_path, monkeypatch):
    app_state = str(tmp_path / "state" / "note-taker")
    assert run(app_state, "init", "--bootstrap", "./init.sh") == 0
    path = draft(tmp_path, "first", folder="instructions/note-taker/drafts")
    type_at_terminal(monkeypatch, "T-1")
    assert run(app_state, "add", "--spec", path) == 0
    assert (tmp_path / "instructions" / "note-taker" / "T-1.md").exists()
    assert not (tmp_path / "instructions" / "note-taker" / "drafts" / "first.md").exists()


def test_add_refuses_another_applications_drafts_folder(state, tmp_path, monkeypatch):
    path = draft(tmp_path, "first", folder="instructions/note-taker/drafts")
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "add", "--spec", path) == 1
    assert ledger(state)["tasks"] == []


def test_evidence_without_output_says_so_instead_of_an_empty_block(state, tmp_path, monkeypatch):
    type_at_terminal(monkeypatch, "T-1")
    run(state, "add", "--spec", draft(tmp_path, "quiet", verify=f'test -e "{tmp_path}/done/quiet"'))
    finish_work(tmp_path, "quiet")
    run(state, "activate", "T-1")
    assert run(state, "pass", "T-1") == 0
    evidence = spec_file(tmp_path, "T-1").read_text().split("## EVIDENCE\n")[1]
    assert "the verification command exited 1, with no output" in evidence
    assert "the verification command exited 0, with no output" in evidence
    assert "```text" not in evidence


def test_evidence_without_output_keeps_the_block_of_a_command_that_prints(state, tmp_path, add):
    add("first")
    evidence = spec_file(tmp_path, "T-1").read_text().split("## EVIDENCE\n")[1]
    assert "with no output" not in evidence
    assert "```text" in evidence
    assert "  checking first" in evidence
