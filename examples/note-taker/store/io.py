import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .types import NotesFile


def _store_dir() -> Path:
    # PyInstaller sets sys.frozen in the built binary, which lives in <repo>/bin:
    # the store then goes in <repo>/tmp, whatever the working directory.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent / "tmp" / ".note-taker"
    # From source, this file lives in <repo>/examples/note-taker/<folder>.
    return Path(__file__).resolve().parents[3] / "tmp" / ".note-taker"


DIR = _store_dir()


# The standard library has no async file API, so blocking calls run in a thread,
# like node:fs/promises does under the hood.
async def read_notes() -> NotesFile:
    try:
        return json.loads(
            await asyncio.to_thread((DIR / "notes.json").read_text, encoding="utf-8")
        )
    except FileNotFoundError:
        # No notes imported yet.
        return {"notes": []}


async def write_json(rel: str, data: Any) -> None:
    path = DIR / rel
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(
        path.write_text, json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
