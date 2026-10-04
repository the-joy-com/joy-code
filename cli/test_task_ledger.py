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


def test_add_numbers_tasks_as_not_started(state):
    run(state, "add", "first")
    run(state, "add", "second")
    assert [(t["id"], t["state"]) for t in ledger(state)["tasks"]] == [("T-1", "not_started"), ("T-2", "not_started")]


def test_activation_is_refused_while_vcr_below_one(state, capsys):
    run(state, "add", "first")
    run(state, "add", "second")
    assert run(state, "activate", "T-1") == 0
    assert run(state, "activate", "T-2") == 1
    assert "VCR is 0/1" in capsys.readouterr().err
    assert task(state, "T-2")["state"] == "not_started"


def test_blocked_task_still_blocks_others_but_can_resume(state):
    run(state, "add", "first")
    run(state, "add", "second")
    run(state, "activate", "T-1")
    assert run(state, "block", "T-1", "--reason", "needs a human") == 0
    assert task(state, "T-1")["blocker"] == "needs a human"
    assert run(state, "activate", "T-2") == 1
    assert run(state, "activate", "T-1") == 0
    assert "blocker" not in task(state, "T-1")


def test_pass_records_evidence_and_unlocks_next_activation(state):
    run(state, "add", "first")
    run(state, "add", "second")
    run(state, "activate", "T-1")
    assert run(state, "pass", "T-1") == 0
    [archived] = archive(state)
    assert archived["id"] == "T-1" and archived["state"] == "passing"
    assert archived["evidence"]["exit_code"] == 0
    assert archived["evidence"]["output_tail"] == ["bootstrap ran"]
    assert run(state, "activate", "T-2") == 0


def test_pass_is_refused_when_bootstrap_fails(state):
    run(state, "add", "first")
    run(state, "activate", "T-1")
    set_bootstrap_exit(state, 12)
    assert run(state, "pass", "T-1") == 1
    assert task(state, "T-1")["state"] == "active"


def test_pass_requires_an_active_task(state):
    run(state, "add", "first")
    assert run(state, "pass", "T-1") == 1


def test_dropped_task_leaves_the_vcr_denominator(state, monkeypatch):
    run(state, "add", "first")
    run(state, "add", "second")
    run(state, "activate", "T-1")
    type_at_terminal(monkeypatch, "T-1")
    assert run(state, "drop", "T-1", "--reason", "human cancelled it") == 0
    assert run(state, "activate", "T-2") == 0


def test_status_reports_vcr(state, capsys):
    run(state, "add", "first")
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


def test_status_fails_on_hand_edited_ledger_breaking_wip1(state):
    run(state, "add", "first")
    run(state, "add", "second")
    data = ledger(state)
    for t in data["tasks"]:
        t["state"] = "active"
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


def test_status_fails_on_passing_task_without_evidence(state):
    run(state, "add", "first")
    data = ledger(state)
    data["tasks"][0]["state"] = "passing"
    task_ledger.ledger_path(state).write_text(json.dumps(data))
    assert run(state, "status") == 1


def test_finished_tasks_leave_the_ledger_but_still_count(state, capsys, monkeypatch):
    for title in ("first", "second", "third"):
        run(state, "add", title)
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


def test_evidence_keeps_only_the_output_tail(state):
    script = task_ledger.ledger_path(state).parent.parent / "init.sh"
    script.write_text("#!/bin/sh\nfor i in 1 2 3 4 5 6; do echo line $i; done\n")
    run(state, "add", "first")
    run(state, "activate", "T-1")
    run(state, "pass", "T-1")
    assert archive(state)[0]["evidence"]["output_tail"] == ["line 4", "line 5", "line 6"]


def test_ids_keep_increasing_after_archiving(state):
    run(state, "add", "first")
    run(state, "activate", "T-1")
    run(state, "pass", "T-1")
    run(state, "add", "second")
    assert [t["id"] for t in ledger(state)["tasks"]] == ["T-2"]


def test_ledger_without_archive_fields_is_migrated(state):
    task_ledger.ledger_path(state).write_text(json.dumps({
        "version": 1,
        "bootstrap": "./init.sh",
        "tasks": [
            {"id": "T-1", "title": "old", "state": "passing", "evidence": {"exit_code": 0}},
            {"id": "T-2", "title": "open", "state": "not_started"},
        ],
    }))
    assert run(state, "add", "new") == 0
    data = ledger(state)
    assert [t["id"] for t in data["tasks"]] == ["T-2", "T-3"]
    assert data["archived"] == {"passing": 1, "dropped": 0}
    assert data["next_id"] == 4


def test_drop_is_refused_without_an_interactive_terminal(state, monkeypatch, capsys):
    run(state, "add", "first")
    monkeypatch.setattr("sys.stdin", io.StringIO("T-1\n"))
    assert run(state, "drop", "T-1", "--reason", "agent gave up") == 1
    assert "needs a human" in capsys.readouterr().err
    assert task(state, "T-1")["state"] == "not_started"


def test_drop_is_refused_when_confirmation_does_not_match(state, monkeypatch):
    run(state, "add", "first")
    type_at_terminal(monkeypatch, "yes")
    assert run(state, "drop", "T-1", "--reason", "typo") == 1
    assert task(state, "T-1")["state"] == "not_started"


def test_human_can_raise_wip_to_work_on_two_tasks(state, monkeypatch):
    for title in ("first", "second", "third"):
        run(state, "add", title)
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


def test_wip_cannot_go_below_the_work_in_progress(state, monkeypatch):
    for title in ("first", "second"):
        run(state, "add", title)
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
