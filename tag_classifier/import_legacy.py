"""Import and clean legacy data from ThreeState into the unified TagDatabase.

Handles:
1. tags_type_cache.json — old cache with mixed type values and dirty keys
2. filter_data/*.txt — per-type text lists with mixed/misclassified entries

Run via CLI:
    python -m tag_classifier import-legacy --cache path/to/cache.json --filter-data path/to/filter_data/
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .database import TagDatabase
from .normalizer import normalize_tag, split_tags
from .types import TagType


# ── Known misclassifications ────────────────────────────────────────────────
#
# NOTE: "artist" type = 画师串 (artist string), which INCLUDES quality/style
# words like best_quality, absurdres, year_2023 etc.  These are NOT false
# positives and must stay as artist.

# These appear in character.txt but are actually artists
ARTIST_IN_CHARACTER_LIST: set[str] = {
    "as109", "wlop", "ciloranko", "ogipote", "morikura en",
    "rurudo", "tkhs", "yabuki kentaro", "yabuki kentarou",
    "tomose shunsaku", "tottotonero", "wsman", "gsusart",
    "healthyman", "bigrbear", "kankan33333", "hokori sakuni",
    "dagashiya", "yamamoto souichirou", "menthako", "jehyun",
    "yutokamizu", "happoubi jin", "ame hagi", "muririn",
    "suujiniku", "aaca", "joynet", "lk149", "somray",
    "nii manabu", "kim eb", "nyahu 77", "atte nanakusa",
    "nagatsukiin", "pononozo", "kobinbin", "haneru",
    "alice vu", "houraku", "kanzarin", "yatanukikey",
    "uni ikura", "dk.senie", "zurikisi", "ayanepuna",
    "kanabun", "usashiro mani", "azumi kazuki", "daidai ookami",
    "misyune", "suyamori", "m alexa", "d elete", "bm tol",
    "karasu raven", "otokuyou", "yamashita shun'ya", "yoi naosuke",
    "andou shuki", "gogalking", "q azieru", "mx2j",
    "tantanmen", "hxxg", "cha goma", "nikorashi-ka", "majamari",
    "observerz", "laserflip", "hungry clicker", "orangemaru",
    "muchi maro", "padoruu", "sugiyama kazutaka", "sakamoto masaru",
    "kadowaki miku", "toosaka1", "kuroboshi kouhaku", "kishida mel",
    "okuda yousuke", "shal.e", "krenz",
    "iuui",  # Also sometimes used as an artist
    "misekai 555",
    "kuo shenlin", "wang yujia",
    "gffewuoutgblubh",
    "rekaerb maerd", "yijian ma",
    "fallenshadow",
    "kowiru",
}

# These appear in clothes.txt but are actually features (body/hair)
FEATURE_IN_CLOTHES_LIST: set[str] = {
    "two side up", "one side up", "sidelocks", "hime-cut", "hime cut",
    "double bun", "half updo", "twin drills", "updo",
    "twintails", "bangs", "braid", "ahoge",
    "wolf", "ears", "cat girl", "fox",
    "halo", "horns", "wings", "tail",
    "huge breasts", "chest",
    "antennae",
}

# Tags in artist.txt that are clearly character/IP names, not artist-string content
NON_ARTIST_IN_ARTIST_LIST: set[str] = {
    "isekai", "arona", "exusiai", "mostima", "octopus", "kyonko",
    "shononome ena", "herrscher of flamescion",
}

# ── Pattern-based auto-classification for "normal" type ──────────────────────

# Regex patterns to auto-classify tags previously marked "normal"
FEATURE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r".*_hair$"),
    re.compile(r".*hair$"),
    re.compile(r".*_eyes$"),
    re.compile(r".*eyes$"),
    re.compile(r".*_skin$"),
    re.compile(r".*_ears$"),
    re.compile(r".*_horns?$"),
    re.compile(r".*_wings?$"),
    re.compile(r".*_tail$"),
    re.compile(r"^long_hair$"),
    re.compile(r"^short_hair$"),
    re.compile(r"^very_long_hair$"),
    re.compile(r"^ponytail$"),
    re.compile(r"^twintails?$"),
    re.compile(r"^breasts?$"),
    re.compile(r"^large_breasts$"),
    re.compile(r"^fang$"),
    re.compile(r"^pale_skin$"),
    re.compile(r"^thick_eyebrows$"),
    re.compile(r"^messy_hair$"),
    re.compile(r"^loose_hair_strand$"),
    re.compile(r"^ahoge$"),
]

CLOTHES_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r".*_dress$"),
    re.compile(r".*_skirt$"),
    re.compile(r".*_shirt$"),
    re.compile(r".*_shorts$"),
    re.compile(r".*_boots$"),
    re.compile(r".*_coat$"),
    re.compile(r".*_thighhighs$"),
    re.compile(r".*_panties$"),
    re.compile(r".*_uniform$"),
    re.compile(r".*_sleeves$"),
    re.compile(r"^hoodie$"),
    re.compile(r"^yukata$"),
    re.compile(r"^headphones$"),
    re.compile(r"^hairband$"),
    re.compile(r"^skirt$"),
    re.compile(r"^robe$"),
    re.compile(r"^sundress$"),
    re.compile(r"^headwear$"),
    re.compile(r"^frills$"),
    re.compile(r"^sash$"),
    re.compile(r"^top_hat$"),
    re.compile(r"^pointy_hat$"),
    re.compile(r"^halo$"),
    re.compile(r".*_clothes$"),
    re.compile(r".*_wristwear$"),
]


def _is_dirty_key(key: str) -> bool:
    """Check if a cache key is garbage / uncleanable."""
    # Contains newlines
    if "\n" in key:
        return True
    # Extremely long (full prompt pasted as key)
    if len(key) > 80:
        return True
    # Weight patterns like :________0.907
    if re.search(r":_{2,}", key):
        return True
    # Numeric weight prefix like "1.3:_:_"
    if re.match(r"^\d+\.?\d*:", key):
        return True
    return False


def _classify_normal_tag(tag: str) -> TagType:
    """Try to auto-classify a tag previously marked 'normal' using patterns."""
    # Use underscore form for pattern matching
    tag_u = tag.replace(" ", "_").lower()

    for pattern in FEATURE_PATTERNS:
        if pattern.match(tag_u):
            return TagType.FEATURE

    for pattern in CLOTHES_PATTERNS:
        if pattern.match(tag_u):
            return TagType.CLOTHES

    # Default: normal → other
    return TagType.OTHER


def import_cache_json(db: TagDatabase, cache_path: str | Path) -> dict[str, int]:
    """Import from tags_type_cache.json with cleaning.

    Returns stats dict with counts per action taken.
    """
    cache_path = Path(cache_path)
    if not cache_path.exists():
        print(f"[import] Cache file not found: {cache_path}")
        return {}

    with open(cache_path, "r", encoding="utf-8") as f:
        raw_data: dict[str, str] = json.load(f)

    stats = {"total": 0, "imported": 0, "skipped_dirty": 0,
             "reclassified": 0}

    for raw_key, raw_type in raw_data.items():
        stats["total"] += 1

        # Skip dirty keys
        if _is_dirty_key(raw_key):
            stats["skipped_dirty"] += 1
            continue

        key = normalize_tag(raw_key)
        if not key:
            stats["skipped_dirty"] += 1
            continue

        # Map legacy type to new type
        tag_type = TagType.from_string(raw_type)

        # Auto-classify "normal" → feature/clothes/other
        if raw_type == "normal":
            tag_type = _classify_normal_tag(key)
            if tag_type != TagType.OTHER:
                stats["reclassified"] += 1

        db.set(key, tag_type)
        stats["imported"] += 1

    return stats


def import_filter_data(db: TagDatabase, filter_data_dir: str | Path) -> dict[str, int]:
    """Import from filter_data/*.txt files with cleaning.

    Files are expected to be: artist.txt, character.txt, clothes.txt, feature.txt
    Each file name (without extension) maps to a TagType.
    """
    filter_data_dir = Path(filter_data_dir)
    if not filter_data_dir.exists():
        print(f"[import] Filter data dir not found: {filter_data_dir}")
        return {}

    stats = {"total": 0, "imported": 0, "skipped": 0, "corrected": 0}

    # Normalize correction sets once
    artist_in_char = _normalize_set(ARTIST_IN_CHARACTER_LIST)
    feature_in_clothes = _normalize_set(FEATURE_IN_CLOTHES_LIST)
    non_artist = _normalize_set(NON_ARTIST_IN_ARTIST_LIST)

    file_type_map = {
        "artist": TagType.ARTIST,
        "character": TagType.CHARACTER,
        "clothes": TagType.CLOTHES,
        "feature": TagType.FEATURE,
    }

    for filename, tag_type in file_type_map.items():
        filepath = filter_data_dir / f"{filename}.txt"
        if not filepath.exists():
            continue

        tags = _parse_filter_file(filepath)

        for tag in tags:
            stats["total"] += 1
            key = normalize_tag(tag)
            if not key:
                stats["skipped"] += 1
                continue

            actual_type = tag_type

            # Corrections for artist.txt
            if tag_type == TagType.ARTIST and key in non_artist:
                stats["skipped"] += 1
                continue  # Skip completely — not useful

            # Corrections for character.txt
            if tag_type == TagType.CHARACTER and key in artist_in_char:
                actual_type = TagType.ARTIST
                stats["corrected"] += 1

            # Corrections for clothes.txt
            if tag_type == TagType.CLOTHES and key in feature_in_clothes:
                actual_type = TagType.FEATURE
                stats["corrected"] += 1

            # Only set if not already classified with higher confidence
            # (cache entries take priority since they were explicitly classified)
            if not db.contains(key):
                db.set(key, actual_type)
                stats["imported"] += 1
            else:
                # Override only if the existing entry is UNKNOWN or OTHER
                existing = db.get(key)
                if existing and existing.tag_type in (TagType.UNKNOWN, TagType.OTHER):
                    if actual_type not in (TagType.UNKNOWN, TagType.OTHER):
                        db.set(key, actual_type)
                        stats["corrected"] += 1

    return stats


def import_all(
    db: TagDatabase,
    cache_path: str | Path | None = None,
    filter_data_dir: str | Path | None = None,
) -> None:
    """Run the full import pipeline and print stats."""
    if cache_path:
        print(f"\n── Importing cache: {cache_path}")
        cache_stats = import_cache_json(db, cache_path)
        _print_stats("Cache", cache_stats)

    if filter_data_dir:
        print(f"\n── Importing filter_data: {filter_data_dir}")
        filter_stats = import_filter_data(db, filter_data_dir)
        _print_stats("Filter Data", filter_stats)

    print(f"\n── Database totals:")
    for type_name, count in db.stats().items():
        print(f"  {type_name:12s}: {count}")
    print(f"  {'TOTAL':12s}: {db.size}")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _normalize_set(s: set[str]) -> set[str]:
    """Normalize all strings in a set for comparison."""
    return {normalize_tag(x) for x in s}


def _parse_filter_file(filepath: Path) -> list[str]:
    """Parse a filter_data text file, handling comments, * prefix, blank lines."""
    tags = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip comments
            if line.startswith("#"):
                continue
            # * prefix: comma-separated batch
            if line.startswith("*"):
                batch = split_tags(line[1:])
                tags.extend(batch)
                continue
            # Regular single tag (may contain commas for multi-tag lines)
            if "," in line:
                tags.extend(split_tags(line))
            else:
                tags.append(line)
    return tags


def _print_stats(label: str, stats: dict[str, int]) -> None:
    for key, val in stats.items():
        print(f"  {label} {key}: {val}")
