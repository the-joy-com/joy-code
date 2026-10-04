import asyncio
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from store.io import read_notes, write_json
from store.types import Note


def id(path: str) -> str:
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]


def title_of(body: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return m.group(1).strip() if m else fallback


# The standard library has no async file API, so blocking calls run in a thread,
# like node:fs/promises does under the hood.
async def walk(dir: str) -> list[str]:
    out: list[str] = []
    with await asyncio.to_thread(os.scandir, dir) as entries:
        for entry in entries:
            p = os.path.join(dir, entry.name)
            # Like Node's Dirent, don't follow symlinks.
            if entry.is_dir(follow_symlinks=False):
                out.extend(await walk(p))
            elif entry.is_file(follow_symlinks=False) and p.endswith(".md"):
                out.append(p)
    return out


async def run_import(dir: str) -> int:
    root = os.path.abspath(dir)
    # Raises if the folder doesn't exist.
    await asyncio.to_thread(os.stat, root)
    paths = await walk(root)
    existing = await read_notes()
    by_path = {n["path"]: n for n in existing["notes"]}

    for p in paths:
        body = await asyncio.to_thread(Path(p).read_text, encoding="utf-8")
        note: Note = {
            "id": id(p),
            "path": p,
            "title": title_of(body, os.path.basename(p)),
            "body": body,
            # Same format as JavaScript's toISOString(), e.g. 2026-10-04T12:00:00.000Z.
            "imported_at": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        }
        by_path[p] = note

    notes = sorted(by_path.values(), key=lambda n: n["id"])
    await write_json("notes.json", {"notes": notes})
    print(f"imported {len(paths)} note(s); total {len(notes)}")
    return 0
