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
