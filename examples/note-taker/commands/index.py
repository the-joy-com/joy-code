import re

from store.io import read_notes, write_json
from store.types import IndexEntry

STOP = {"the", "and", "for", "with", "a", "an", "of", "to", "is", "in", "on"}


def tokenize(s: str) -> list[str]:
    """
    Extracts lowercase word tokens from the input string, skipping common stop words.

    - Converts `s` to lowercase.
    - Finds all sequences of at least 3 consecutive letters or digits ([a-z0-9]{3,}).
    - Ignores any tokens present in the STOP set (common uninformative words).
    - Returns a list of non-stopword tokens.

    Used to build a search index by isolating meaningful words from note titles and bodies.
    """
    return [t for t in re.findall(r"[a-z0-9]{3,}", s.lower()) if t not in STOP]


async def run_index() -> int:
    notes = (await read_notes())["notes"]
    inv: dict[str, set[str]] = {}
    for n in notes:
        for tok in set(tokenize(f"{n['title']} {n['body']}")):
            inv.setdefault(tok, set()).add(n["id"])
    # Tokens are only [a-z0-9], so a plain sort matches JavaScript's localeCompare.
    tokens: list[IndexEntry] = [
        {"token": token, "note_ids": sorted(ids)} for token, ids in sorted(inv.items())
    ]
    await write_json("index.json", {"tokens": tokens})
    print(f"indexed {len(notes)} note(s); {len(tokens)} token(s)")
    return 0
