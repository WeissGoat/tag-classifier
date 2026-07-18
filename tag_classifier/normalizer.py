"""Tag normalization utilities.

Pure functions extracted from uai.py and ustring.py — zero external dependencies.
All normalization should go through `normalize_tag()` as the single entry point.
"""

from __future__ import annotations

import re


def split_tags(prompt: str, pattern: str = ",", skip_blank: bool = True) -> list[str]:
    """Split a prompt string into individual tags.

    >>> split_tags("red eyes, 1girl, , blue hair")
    ['red eyes', '1girl', 'blue hair']
    """
    parts = prompt.split(pattern)
    if skip_blank:
        return [p.strip() for p in parts if p.strip()]
    return [p.strip() for p in parts]


def normalize_tag(tag: str) -> str:
    """Primary normalization: lowercase, strip, underscores → spaces, remove weight brackets.

    This is the canonical normalization used for cache keys and matching.

    >>> normalize_tag("{Artist: Ciloranko}")
    'ciloranko'
    >>> normalize_tag("red_eyes")
    'red eyes'
    """
    tag = _filter_tag(tag)
    tag = _strip_weight_brackets(tag)
    tag = _strip_artist_prefix(tag)
    tag = tag.replace("_", " ")
    # Collapse multiple spaces
    tag = re.sub(r"\s+", " ", tag).strip()
    return tag


def normalize_tag_underscore(tag: str) -> str:
    """Normalize to underscore-separated form (Danbooru style).

    >>> normalize_tag_underscore("Red Eyes")
    'red_eyes'
    """
    tag = normalize_tag(tag)
    return tag.replace(" ", "_")


def standardize_artist(tag: str) -> str:
    """Normalize specifically for artist name matching.

    Equivalent to the old `uai.standardization_artist()`.

    >>> standardize_artist("artist: Ciloranko")
    'ciloranko'
    >>> standardize_artist("{ke-ta}")
    'ke-ta'
    """
    tag = _filter_tag(tag)
    tag = _strip_weight_brackets(tag)
    tag = tag.replace("  ", " ").replace(" :", ":").replace(":", ": ")
    tag = _strip_artist_prefix(tag)
    tag = tag.strip().replace(" ", "_")
    # Split and rejoin to handle comma-separated compound tags
    parts = split_tags(tag)
    return ",".join(parts)


def get_raw_tag(tag: str) -> str:
    """Strip all formatting to get the raw semantic content.

    Removes weight brackets, underscores → spaces, normalizes whitespace.
    Equivalent to the old `uai.get_raw_tags()` for a single tag.
    """
    tag = _filter_tag(tag)
    tag = _strip_weight_brackets(tag)
    tag = tag.replace("_", " ").replace("  ", " ")
    parts = split_tags(tag)
    return ",".join(parts)


def strip_weight(tag: str) -> str:
    """Remove NAI weight markers { } [ ] from a tag.

    >>> strip_weight("{{{red eyes}}}")
    'red eyes'
    """
    return _strip_weight_brackets(tag)


def includes_substring(needle: str, haystack: list[str] | dict[str, object]) -> str | None:
    """Check if any item in haystack is a substring of needle. Returns the match.

    Equivalent to the old `ustring.include()`.

    >>> includes_substring("hatsune miku vocaloid", ["miku", "reimu"])
    'miku'
    """
    items = haystack if isinstance(haystack, list) else list(haystack.keys())
    for item in items:
        if item in needle:
            return item
    return None


def filter_inner_substrings(tags: list[str]) -> list[str]:
    """Remove tags that are substrings of other tags in the list.

    Equivalent to the old `ustring.filter_sting_iner_list()`.

    >>> filter_inner_substrings(["red", "red eyes", "blue"])
    ['red eyes', 'blue']
    """
    result = []
    for i, item in enumerate(tags):
        others = tags[:i] + tags[i + 1:]
        if includes_substring(item, others) is not None:
            continue
        result.append(item)
    return result


# ── Private helpers ──────────────────────────────────────────────────────────


def _filter_tag(tag: str) -> str:
    """Basic cleanup: lowercase, fix encoding artifacts."""
    return tag.lower().replace("，", ",").replace("\xa0", " ").strip()


def _strip_weight_brackets(tag: str) -> str:
    """Remove { } [ ] weight brackets."""
    return tag.replace("{", "").replace("}", "").replace("[", "").replace("]", "")


def _strip_artist_prefix(tag: str) -> str:
    """Remove 'artist:' prefix if present."""
    tag = re.sub(r"^artist:\s*", "", tag)
    return tag
