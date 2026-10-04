import shutil

import pytest

import store.io
from commands.import_ import run_import
from store.io import read_notes


@pytest.mark.asyncio
async def test_import_ingests_md_files_and_writes_notes_json(tmp_path, monkeypatch):
    src = tmp_path / "noted-src"
    src.mkdir()
    (src / "a.md").write_text("# Alpha\nbody-a", encoding="utf-8")
    (src / "b.md").write_text("# Bravo\nbody-b", encoding="utf-8")

    # The store always lives in <repo>/tmp/.note-taker whatever the working
    # directory, so point it at <repo>/tmp/.note-taker-tests instead of changing
    # directory. monkeypatch puts the real store back after the test.
    work = store.io.DIR.parent / ".note-taker-tests"
    shutil.rmtree(work, ignore_errors=True)
    monkeypatch.setattr(store.io, "DIR", work)
    try:
        code = await run_import(str(src))
        assert code == 0
        notes = (await read_notes())["notes"]
        assert len(notes) == 2
        assert sorted(n["title"] for n in notes) == ["Alpha", "Bravo"]
    finally:
        shutil.rmtree(work, ignore_errors=True)
