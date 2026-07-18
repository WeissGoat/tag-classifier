"""Configuration for the tag classifier."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TagClassifierConfig:
    """Configuration — all paths configurable, no hardcoded defaults."""

    # Where the unified tags_db.json lives
    db_path: Path = field(default_factory=lambda: Path("data/tags_db.json"))

    # Where human-maintained per-type lists live (for reference / re-import)
    lists_dir: Path = field(default_factory=lambda: Path("data/lists"))

    @classmethod
    def from_env(cls, prefix: str = "TAG_CLASSIFIER_") -> TagClassifierConfig:
        """Build config from environment variables."""
        config = cls()
        val = os.environ.get(f"{prefix}DB_PATH")
        if val:
            config.db_path = Path(val)
        val = os.environ.get(f"{prefix}LISTS_DIR")
        if val:
            config.lists_dir = Path(val)
        return config

    def resolve_paths(self, base_dir: Path | None = None) -> None:
        """Resolve relative paths against a base directory."""
        if base_dir is None:
            base_dir = Path.cwd()
        base_dir = Path(base_dir)
        if not self.db_path.is_absolute():
            self.db_path = base_dir / self.db_path
        if not self.lists_dir.is_absolute():
            self.lists_dir = base_dir / self.lists_dir
