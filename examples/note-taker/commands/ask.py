import re

from commands.index import tokenize
from store.io import read_index, read_notes

# A markdown ATX heading: 1 to 6 `#` then a space or the end of the line (`#tag` is not one).
HEADING = re.compile(r"#{1,6}(\s|$)")


def snippet_of(body: str) -> str:
    # The first non-blank, non-heading line, so the preview doesn't repeat the title.
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped and not HEADING.match(stripped):
            return line
    return ""


async def run_ask(query: str, k: int = 3) -> int:
    # Reuses the index's tokenizer, so query tokens match indexed tokens exactly.
    tokens = {e["token"]: e["note_ids"] for e in (await read_index())["tokens"]}
    notes = {n["id"]: n for n in (await read_notes())["notes"]}
    score: dict[str, int] = {}
    for t in set(tokenize(query)):
        for note_id in tokens.get(t, []):
            score[note_id] = score.get(note_id, 0) + 1
    # sorted is stable, so ties keep first-match order, like JavaScript's sort.
    # Ids missing from notes (stale index) are dropped after the top-k cut.
    top = sorted(score.items(), key=lambda item: item[1], reverse=True)[:k]
    ranked = [notes[note_id] for note_id, _ in top if note_id in notes]

    if not ranked:
        print("no matches")
        return 0
    for n in ranked:
        print(f"[{n['id']}] {n['title']}")
        print(f"    {snippet_of(n['body'])[:120]}")
        print(f"    cite: {n['path']}")
    return 0
