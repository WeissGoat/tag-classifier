"""CLI entry point for the tag classifier.

Usage:
    python -m tag_classifier classify "red eyes, ciloranko, school uniform"
    python -m tag_classifier filter --exclude artist,character "ciloranko, 1girl, red eyes"
    python -m tag_classifier select --type artist "ciloranko, 1girl, red eyes"
    python -m tag_classifier import-legacy --cache path/to/cache.json --filter-data path/to/filter_data/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .classifier import TagClassifier
from .database import TagDatabase
from .types import TagType


def _resolve_db(args: argparse.Namespace) -> TagDatabase:
    """Load the tag database from --db or default location."""
    db_path = getattr(args, "db", None)
    if db_path:
        db_path = Path(db_path)
    else:
        # Default: look relative to this package
        db_path = Path(__file__).parent.parent / "data" / "tags_db.json"
    if not db_path.exists():
        print(f"Warning: database not found at {db_path}, using empty DB", file=sys.stderr)
        return TagDatabase()
    return TagDatabase(db_path)


def _parse_types(type_str: str) -> list[TagType]:
    """Parse comma-separated type names into TagType list."""
    types = []
    for t in type_str.split(","):
        t = t.strip().lower()
        if not t:
            continue
        try:
            types.append(TagType(t))
        except ValueError:
            print(f"Warning: unknown type '{t}', skipping", file=sys.stderr)
    return types


def _read_input(args: argparse.Namespace) -> list[str]:
    """Read input from args.text, args.file, or stdin."""
    if hasattr(args, "file") and args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    if hasattr(args, "text") and args.text:
        return [args.text]
    # Read from stdin
    if not sys.stdin.isatty():
        return [line.strip() for line in sys.stdin if line.strip()]
    print("Error: no input provided. Use positional text, -f file, or pipe stdin.", file=sys.stderr)
    sys.exit(1)


def cmd_classify(args: argparse.Namespace) -> None:
    """Classify each tag and print a table."""
    db = _resolve_db(args)
    classifier = TagClassifier(db)
    lines = _read_input(args)

    for line in lines:
        result = classifier.classify_prompt(line)
        # Print header
        print(f"\n{'Tag':<30s} {'Type':<12s} {'Source':<12s}")
        print("─" * 54)
        for tc in result.classifications:
            print(f"{tc.tag:<30s} {tc.tag_type.value:<12s} {tc.source:<12s}")


def cmd_filter(args: argparse.Namespace) -> None:
    """Remove tags of specified types."""
    db = _resolve_db(args)
    classifier = TagClassifier(db)
    exclude = _parse_types(args.exclude)
    lines = _read_input(args)

    results = []
    for line in lines:
        filtered = classifier.filter_prompt(line, exclude)
        results.append(filtered)

    output = "\n".join(results)
    if hasattr(args, "output") and args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Wrote {len(results)} lines to {args.output}")
    else:
        print(output)


def cmd_select(args: argparse.Namespace) -> None:
    """Keep only tags of specified types."""
    db = _resolve_db(args)
    classifier = TagClassifier(db)
    include = _parse_types(args.type)
    lines = _read_input(args)

    results = []
    for line in lines:
        selected = classifier.select_prompt(line, include)
        results.append(selected)

    output = "\n".join(results)
    if hasattr(args, "output") and args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Wrote {len(results)} lines to {args.output}")
    else:
        print(output)


def cmd_import_legacy(args: argparse.Namespace) -> None:
    """Import from legacy ThreeState data."""
    from .import_legacy import import_all

    db = TagDatabase()  # Start fresh

    import_all(
        db,
        cache_path=args.cache,
        filter_data_dir=args.filter_data,
    )

    output_path = Path(args.output)
    db.save(output_path)
    print(f"\nDone. Saved {db.size} entries to {output_path}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Print database statistics."""
    db = _resolve_db(args)
    print(f"Database: {db.db_path}")
    print(f"Total entries: {db.size}")
    print()
    for type_name, count in db.stats().items():
        print(f"  {type_name:<12s}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tag-classifier",
        description="Classify and filter AI image prompt tags by type.",
    )
    parser.add_argument("--db", help="Path to tags_db.json (default: data/tags_db.json)")
    subparsers = parser.add_subparsers(dest="command")

    # classify
    p_classify = subparsers.add_parser("classify", help="Classify tags by type")
    p_classify.add_argument("text", nargs="?", help="Comma-separated tags")
    p_classify.add_argument("-f", "--file", help="Input file (one prompt per line)")

    # filter
    p_filter = subparsers.add_parser("filter", help="Remove tags of specified types")
    p_filter.add_argument("text", nargs="?", help="Comma-separated tags")
    p_filter.add_argument("--exclude", required=True, help="Types to exclude (comma-separated)")
    p_filter.add_argument("-f", "--file", help="Input file")
    p_filter.add_argument("-o", "--output", help="Output file")

    # select
    p_select = subparsers.add_parser("select", help="Keep only tags of specified types")
    p_select.add_argument("text", nargs="?", help="Comma-separated tags")
    p_select.add_argument("--type", required=True, help="Types to keep (comma-separated)")
    p_select.add_argument("-f", "--file", help="Input file")
    p_select.add_argument("-o", "--output", help="Output file")

    # import-legacy
    p_import = subparsers.add_parser("import-legacy", help="Import from legacy ThreeState data")
    p_import.add_argument("--cache", help="Path to tags_type_cache.json")
    p_import.add_argument("--filter-data", help="Path to filter_data/ directory")
    p_import.add_argument("--output", default="data/tags_db.json", help="Output DB path")

    # stats
    subparsers.add_parser("stats", help="Print database statistics")

    args = parser.parse_args()

    if args.command == "classify":
        cmd_classify(args)
    elif args.command == "filter":
        cmd_filter(args)
    elif args.command == "select":
        cmd_select(args)
    elif args.command == "import-legacy":
        cmd_import_legacy(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
