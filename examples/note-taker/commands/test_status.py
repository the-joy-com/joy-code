import shutil

import pytest

import store.io
from commands.status import run_status
from store.io import write_json


@pytest.mark.asyncio
async def test_status_counts_notes_and_prints_the_store_path(monkeypatch, capsys):
    work = store.io.DIR.parent / ".note-taker-tests"
    shutil.rmtree(work, ignore_errors=True)
    monkeypatch.setattr(store.io, "DIR", work)
    try:
        assert await run_status() == 0
        assert capsys.readouterr().out == f"notes:    0\nstorage:  {work / 'notes.json'}\n"

        await write_json("notes.json", {"notes": [{"id": "x"}, {"id": "y"}]})
        assert await run_status() == 0
        assert capsys.readouterr().out.startswith("notes:    2\n")
    finally:
        shutil.rmtree(work, ignore_errors=True)
