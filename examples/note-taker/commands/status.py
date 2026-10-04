import store.io
from store.io import read_notes


async def run_status() -> int:
    notes = (await read_notes())["notes"]
    print(f"notes:    {len(notes)}")
    print(f"storage:  {store.io.DIR / 'notes.json'}")
    return 0
