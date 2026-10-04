import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent


def run_cli(cli: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(cli), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path) -> Path:
    # The store always lives in <repo>/tmp/.note-taker, worked out from where the
    # source sits, so run a copy of the app laid out like the repo: its store then
    # goes in <tmp_path>/repo/tmp/.note-taker and the real one is never touched.
    repo = tmp_path / "repo"
    app = repo / "examples" / "note-taker"
    app.mkdir(parents=True)
    shutil.copy(APP / "cli.py", app)
    for pkg in ("store", "commands"):
        shutil.copytree(
            APP / pkg, app / pkg, ignore=shutil.ignore_patterns("__pycache__", "test_*")
        )
    return repo


def test_import_then_index_from_the_command_line(repo, tmp_path):
    cli = repo / "examples" / "note-taker" / "cli.py"
    store = repo / "tmp" / ".note-taker"

    sample = tmp_path / "sample-notes"
    sample.mkdir()
    (sample / "a.md").write_text("# First note\nThis is alpha.\n", encoding="utf-8")
    (sample / "b.md").write_text("# Second note\nThis is bravo.\n", encoding="utf-8")

    imported = run_cli(cli, "import", str(sample))
    assert imported.returncode == 0, imported.stderr
    assert imported.stdout == "imported 2 note(s); total 2\n"

    notes = json.loads((store / "notes.json").read_text(encoding="utf-8"))["notes"]
    assert sorted(n["title"] for n in notes) == ["First note", "Second note"]
    ids = {Path(n["path"]).name: n["id"] for n in notes}

    indexed = run_cli(cli, "index")
    assert indexed.returncode == 0, indexed.stderr
    assert indexed.stdout == "indexed 2 note(s); 6 token(s)\n"

    tokens = json.loads((store / "index.json").read_text(encoding="utf-8"))["tokens"]
    by_token = {t["token"]: t["note_ids"] for t in tokens}
    assert list(by_token) == ["alpha", "bravo", "first", "note", "second", "this"]
    assert by_token["alpha"] == [ids["a.md"]]
    assert by_token["bravo"] == [ids["b.md"]]
    assert by_token["note"] == sorted(ids.values())


def test_import_of_a_missing_folder_fails_without_writing_the_store(repo, tmp_path):
    cli = repo / "examples" / "note-taker" / "cli.py"
    result = run_cli(cli, "import", str(tmp_path / "nope"))
    assert result.returncode == 1
    assert result.stderr.startswith("error: ")
    assert not (repo / "tmp" / ".note-taker").exists()


def test_ask_cites_the_best_matching_notes_from_the_command_line(repo, tmp_path):
    cli = repo / "examples" / "note-taker" / "cli.py"

    sample = tmp_path / "sample-notes"
    sample.mkdir()
    (sample / "a.md").write_text("# Python tips\nUse asyncio for I/O.\n", encoding="utf-8")
    (sample / "b.md").write_text("# Cooking\nBoil pasta.\n", encoding="utf-8")
    assert run_cli(cli, "import", str(sample)).returncode == 0
    assert run_cli(cli, "index").returncode == 0

    # Unquoted words make up a single query.
    asked = run_cli(cli, "ask", "python", "asyncio")
    assert asked.returncode == 0, asked.stderr
    lines = asked.stdout.splitlines()
    assert len(lines) == 3
    assert lines[0].endswith("] Python tips")
    # The H1 title is skipped, so the preview is the first line of prose.
    assert lines[1] == "    Use asyncio for I/O."
    assert lines[2] == f"    cite: {sample / 'a.md'}"

    missing = run_cli(cli, "ask", "zebra")
    assert missing.returncode == 0
    assert missing.stdout == "no matches\n"


def test_ask_without_a_query_or_an_index_fails(repo):
    cli = repo / "examples" / "note-taker" / "cli.py"

    no_query = run_cli(cli, "ask")
    assert no_query.returncode == 2
    assert no_query.stderr == "ask requires a query\n"

    no_index = run_cli(cli, "ask", "python")
    assert no_index.returncode == 1
    assert no_index.stderr.startswith("error: ")


def test_ask_k_limits_the_number_of_notes(repo, tmp_path):
    cli = repo / "examples" / "note-taker" / "cli.py"

    sample = tmp_path / "sample-notes"
    sample.mkdir()
    for name in ("a", "b", "c", "d"):
        (sample / f"{name}.md").write_text(f"# Note {name}\nshared words\n", encoding="utf-8")
    assert run_cli(cli, "import", str(sample)).returncode == 0
    assert run_cli(cli, "index").returncode == 0

    def count(*args: str) -> int:
        result = run_cli(cli, "ask", *args)
        assert result.returncode == 0, result.stderr
        return sum(line.startswith("[") for line in result.stdout.splitlines())

    assert count("shared") == 3
    assert count("shared", "-k", "1") == 1
    assert count("-k", "4", "shared", "words") == 4


@pytest.mark.parametrize("args", [["shared", "-k"], ["shared", "-k", "0"], ["shared", "-k", "two"]])
def test_ask_rejects_a_bad_k(repo, args):
    cli = repo / "examples" / "note-taker" / "cli.py"
    result = run_cli(cli, "ask", *args)
    assert result.returncode == 2
    assert result.stderr == "-k requires a positive integer\n"


def test_ask_with_only_k_still_requires_a_query(repo):
    cli = repo / "examples" / "note-taker" / "cli.py"
    result = run_cli(cli, "ask", "-k", "2")
    assert result.returncode == 2
    assert result.stderr == "ask requires a query\n"


def test_ask_reads_words_after_double_dash_as_the_query(repo, tmp_path):
    cli = repo / "examples" / "note-taker" / "cli.py"

    sample = tmp_path / "sample-notes"
    sample.mkdir()
    for name in ("a", "b", "c", "d"):
        (sample / f"{name}.md").write_text(f"# Note {name}\nshared words\n", encoding="utf-8")
    assert run_cli(cli, "import", str(sample)).returncode == 0
    assert run_cli(cli, "index").returncode == 0

    def ask(*args: str) -> subprocess.CompletedProcess[str]:
        result = run_cli(cli, "ask", *args)
        assert result.returncode == 0, result.stderr
        return result

    def count(result: subprocess.CompletedProcess[str]) -> int:
        return sum(line.startswith("[") for line in result.stdout.splitlines())

    # After `--`, `-k 1` is query text, not the option: the default of 3 applies.
    assert count(ask("shared", "--", "-k", "1")) == 3
    # Options before `--` still apply.
    assert count(ask("-k", "1", "--", "shared")) == 1
    # A lone `-k` after `--` is a query word, not a missing option value. The tokenizer
    # drops it (shorter than 3 characters), so nothing matches.
    assert ask("--", "-k").stdout == "no matches\n"
    # Only the first `--` ends the options.
    assert count(ask("--", "--", "shared")) == 3


def test_ask_with_only_double_dash_still_requires_a_query(repo):
    cli = repo / "examples" / "note-taker" / "cli.py"
    result = run_cli(cli, "ask", "-k", "2", "--")
    assert result.returncode == 2
    assert result.stderr == "ask requires a query\n"
