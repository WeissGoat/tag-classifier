"""TagClassifier — the main classification engine.

Looks up tags in the TagDatabase. Simple and direct.
"""

from __future__ import annotations

from .database import TagDatabase
from .normalizer import normalize_tag, split_tags
from .types import PromptTagResult, TagClassification, TagType


class TagClassifier:
    """Classify tags by looking them up in a local TagDatabase.

    Usage::

        db = TagDatabase(Path("data/tags_db.json"))
        classifier = TagClassifier(db)

        result = classifier.classify_tag("ciloranko")
        # -> TagClassification(tag='ciloranko', tag_type=TagType.ARTIST, ...)

        result = classifier.classify_prompt("ciloranko, 1girl, red eyes")
        # -> PromptTagResult with structured access
    """

    def __init__(self, db: TagDatabase):
        self.db = db

    def classify_tag(self, tag: str) -> TagClassification:
        """Classify a single tag."""
        result = self.db.get(tag)
        if result:
            return result
        return TagClassification(
            tag=tag,
            normalized=normalize_tag(tag),
            tag_type=TagType.UNKNOWN,
            confidence=0.0,
            source="none",
        )

    def classify_prompt(self, prompt: str) -> PromptTagResult:
        """Classify all tags in a comma-separated prompt string."""
        tags = split_tags(prompt)
        result = PromptTagResult(original=prompt)
        for tag in tags:
            classification = self.classify_tag(tag)
            result.classifications.append(classification)
        return result

    def filter_prompt(self, prompt: str, exclude: list[TagType]) -> str:
        """Remove tags of specified types from a prompt."""
        result = self.classify_prompt(prompt)
        return result.filter(exclude)

    def select_prompt(self, prompt: str, include: list[TagType]) -> str:
        """Keep only tags of specified types from a prompt."""
        result = self.classify_prompt(prompt)
        return result.select(include)

    def classify_batch(self, prompts: list[str]) -> list[PromptTagResult]:
        """Classify multiple prompts."""
        return [self.classify_prompt(p) for p in prompts]
