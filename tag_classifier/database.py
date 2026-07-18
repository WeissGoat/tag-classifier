"""Tag database — unified JSON storage for tag → type mappings.

Single source of truth for all tag classifications.
Replaces the old TagTypeCache with a cleaner interface.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .normalizer import normalize_tag
from .types import TagClassification, TagType


class TagDatabase:
    """In-memory tag database backed by a JSON file.

    The JSON file is a flat dict: ``{"normalized_tag": "type_value", ...}``

    Usage::

        db = TagDatabase(Path("data/tags_db.json"))
        db.get("red_eyes")        # -> TagClassification or None
        db.set("red_eyes", TagType.FEATURE)
        db.save()
    """

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else None
        self._data: dict[str, str] = {}   # normalized_tag -> type value
        if self.db_path and self.db_path.exists():
            self._load()

    # ── Core API ─────────────────────────────────────────────────────────────

    def get(self, tag: str) -> TagClassification | None:
        """Look up a tag. Returns None on miss."""
        key = normalize_tag(tag)
        type_val = self._data.get(key)
        if type_val is None:
            return None
        return TagClassification(
            tag=tag,
            normalized=key,
            tag_type=TagType.from_string(type_val),
            confidence=1.0,
            source="local_db",
        )

    def set(self, tag: str, tag_type: TagType | str) -> None:
        """Store a tag → type mapping."""
        key = normalize_tag(tag)
        value = tag_type.value if isinstance(tag_type, TagType) else tag_type
        self._data[key] = value

    def contains(self, tag: str) -> bool:
        return normalize_tag(tag) in self._data

    def remove(self, tag: str) -> bool:
        key = normalize_tag(tag)
        if key in self._data:
            del self._data[key]
            return True
        return False

    def bulk_set(self, entries: dict[str, str | TagType]) -> int:
        """Bulk insert. Returns count of entries added."""
        count = 0
        for tag, tag_type in entries.items():
            key = normalize_tag(tag)
            value = tag_type.value if isinstance(tag_type, TagType) else tag_type
            self._data[key] = value
            count += 1
        return count

    @property
    def size(self) -> int:
        return len(self._data)

    def all_entries(self) -> dict[str, str]:
        """Return a copy of all entries."""
        return dict(self._data)

    def entries_by_type(self, tag_type: TagType) -> list[str]:
        """Get all tags of a specific type."""
        return [tag for tag, val in self._data.items() if val == tag_type.value]

    def stats(self) -> dict[str, int]:
        """Count entries per type."""
        counts: dict[str, int] = {}
        for val in self._data.values():
            counts[val] = counts.get(val, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.db_path or not self.db_path.exists():
            return
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"[TagDatabase] Warning: could not load {self.db_path}: {e}")

    def save(self, path: Path | str | None = None) -> None:
        """Save database to JSON file."""
        target = Path(path) if path else self.db_path
        if not target:
            raise ValueError("No path specified for save")
        os.makedirs(target.parent, exist_ok=True)
        # Sort by type then by tag for human readability
        sorted_data = dict(sorted(self._data.items(), key=lambda x: (x[1], x[0])))
        with open(target, "w", encoding="utf-8") as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
        print(f"[TagDatabase] Saved {len(self._data)} entries to {target}")

    # ── Legacy compat ────────────────────────────────────────────────────────

    def __getitem__(self, tag: str) -> str | None:
        result = self.get(tag)
        return result.tag_type.value if result else None

    def __setitem__(self, tag: str, value: str | TagType) -> None:
        self.set(tag, value)

    def __contains__(self, tag: str) -> bool:
        return self.contains(tag)

    def __len__(self) -> int:
        return self.size
