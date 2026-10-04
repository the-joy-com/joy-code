import shutil

import pytest

import store.io
from commands.ask import run_ask, snippet_of
from store.io import write_json


@pytest.mark.asyncio
async def test_ask_ranks_by_matched_tokens_and_cites_paths(tmp_path, monkeypatch, capsys):
    # Same isolated store as the import tests: <repo>/tmp/.note-taker-tests.
    work = store.io.DIR.parent / ".note-taker-tests"
    shutil.rmtree(work, ignore_errors=True)
    monkeypatch.setattr(store.io, "DIR", work)
    try:
        await write_json(
            "notes.json",
            {
                "notes": [
                    {"id": "one", "path": "/n/one.md", "title": "One", "body": "only python", "imported_at": ""},
                    {"id": "two", "path": "/n/two.md", "title": "Two", "body": "\n\n  \npython asyncio\nmore", "imported_at": ""},
                    {"id": "three", "path": "/n/three.md", "title": "Three", "body": "x" * 200, "imported_at": ""},
                ]
            },
        )
        await write_json(
            "index.json",
            {
                "tokens": [
                    {"token": "asyncio", "note_ids": ["two"]},
                    {"token": "python", "note_ids": ["one", "two"]},
                    {"token": "xxx", "note_ids": ["three"]},
                ]
            },
        )

        # Repeated and stop-word query terms don't count twice or at all.
        assert await run_ask("Python python the asyncio") == 0
        assert capsys.readouterr().out == (
            "[two] Two\n    python asyncio\n    cite: /n/two.md\n"
            "[one] One\n    only python\n    cite: /n/one.md\n"
        )

        assert await run_ask("python asyncio", k=1) == 0
        assert capsys.readouterr().out.startswith("[two] Two\n")

        assert await run_ask("zebra") == 0
        assert capsys.readouterr().out == "no matches\n"
    finally:
        shutil.rmtree(work, ignore_errors=True)


@pytest.mark.asyncio
async def test_ask_truncates_the_snippet_to_120_chars(tmp_path, monkeypatch, capsys):
    work = store.io.DIR.parent / ".note-taker-tests"
    shutil.rmtree(work, ignore_errors=True)
    monkeypatch.setattr(store.io, "DIR", work)
    try:
        note = {"id": "long", "path": "/n/l.md", "title": "Long", "body": "word " * 60, "imported_at": ""}
        await write_json("notes.json", {"notes": [note]})
        await write_json("index.json", {"tokens": [{"token": "word", "note_ids": ["long"]}]})

        assert await run_ask("word") == 0
        snippet = capsys.readouterr().out.splitlines()[1]
        assert snippet == "    " + ("word " * 60)[:120]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_snippet_skips_blank_and_heading_lines():
    assert snippet_of("# Title\n\n## Sub\n  \nfirst prose\nnext") == "first prose"
    # `#tag` has no space after the `#`, so it's prose, not a heading.
    assert snippet_of("# Title\n#tag line") == "#tag line"
    assert snippet_of("# Only\n###\n") == ""
