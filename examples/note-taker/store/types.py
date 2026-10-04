# A TypedDict is a special type in Python's typing module that allows you to define
# dictionaries with a fixed set of keys and associated value types.
# This enables better type checking by specifying the expected structure of dict-like objects.
from typing import TypedDict


class Note(TypedDict):
    id: str  # sha1(path) truncated to 12
    path: str  # absolute path, source of truth
    title: str  # first H1, or filename
    body: str  # raw markdown
    imported_at: str  # ISO 8601


class IndexEntry(TypedDict):
    token: str
    note_ids: list[str]


class NotesFile(TypedDict):
    notes: list[Note]


class IndexFile(TypedDict):
    tokens: list[IndexEntry]
