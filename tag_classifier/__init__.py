"""Tag Classifier — structured tag classification for AI image prompts.

Quick start::

    from tag_classifier import TagClassifier, TagDatabase, TagType

    db = TagDatabase("data/tags_db.json")
    classifier = TagClassifier(db)

    # Classify a prompt
    result = classifier.classify_prompt("ciloranko, 1girl, red eyes, school uniform")
    print(result.artists)      # ['ciloranko']
    print(result.features)     # ['red eyes']

    # Filter out artist tags
    clean = classifier.filter_prompt(prompt, exclude=[TagType.ARTIST])

    # Keep only character tags
    chars = classifier.select_prompt(prompt, include=[TagType.CHARACTER])
"""

from .classifier import TagClassifier
from .database import TagDatabase
from .normalizer import normalize_tag, split_tags
from .types import PromptTagResult, TagClassification, TagType

__all__ = [
    "TagClassifier",
    "TagDatabase",
    "TagType",
    "TagClassification",
    "PromptTagResult",
    "normalize_tag",
    "split_tags",
]
