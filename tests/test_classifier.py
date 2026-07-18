"""Tests for TagDatabase and TagClassifier."""

import json
import tempfile
from pathlib import Path

from tag_classifier.classifier import TagClassifier
from tag_classifier.database import TagDatabase
from tag_classifier.types import TagType


class TestTagDatabase:
    def _make_db(self, entries: dict[str, str] | None = None) -> TagDatabase:
        db = TagDatabase()
        if entries:
            db.bulk_set(entries)
        return db

    def test_set_and_get(self):
        db = self._make_db()
        db.set("ciloranko", TagType.ARTIST)
        result = db.get("ciloranko")
        assert result is not None
        assert result.tag_type == TagType.ARTIST

    def test_normalization(self):
        db = self._make_db()
        db.set("Red_Eyes", TagType.FEATURE)
        result = db.get("red eyes")
        assert result is not None
        assert result.tag_type == TagType.FEATURE

    def test_get_miss(self):
        db = self._make_db()
        assert db.get("nonexistent") is None

    def test_contains(self):
        db = self._make_db({"ciloranko": "artist"})
        assert db.contains("ciloranko")
        assert not db.contains("nonexistent")

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_db.json"
            db = TagDatabase()
            db.set("ciloranko", TagType.ARTIST)
            db.set("red eyes", TagType.FEATURE)
            db.save(path)

            db2 = TagDatabase(path)
            assert db2.get("ciloranko").tag_type == TagType.ARTIST
            assert db2.get("red eyes").tag_type == TagType.FEATURE
            assert db2.size == 2

    def test_stats(self):
        db = self._make_db({
            "ciloranko": "artist",
            "wlop": "artist",
            "red eyes": "feature",
            "1girl": "other",
        })
        stats = db.stats()
        assert stats["artist"] == 2
        assert stats["feature"] == 1
        assert stats["other"] == 1

    def test_legacy_getitem(self):
        db = self._make_db({"ciloranko": "artist"})
        assert db["ciloranko"] == "artist"
        assert db["missing"] is None

    def test_entries_by_type(self):
        db = self._make_db({
            "ciloranko": "artist",
            "wlop": "artist",
            "red eyes": "feature",
        })
        artists = db.entries_by_type(TagType.ARTIST)
        assert len(artists) == 2
        assert "ciloranko" in artists


class TestTagClassifier:
    def _make_classifier(self, entries: dict[str, str]) -> TagClassifier:
        db = TagDatabase()
        db.bulk_set(entries)
        return TagClassifier(db)

    def test_classify_known(self):
        c = self._make_classifier({"ciloranko": "artist", "red eyes": "feature"})
        result = c.classify_tag("ciloranko")
        assert result.tag_type == TagType.ARTIST

    def test_classify_unknown(self):
        c = self._make_classifier({})
        result = c.classify_tag("something_random")
        assert result.tag_type == TagType.UNKNOWN
        assert result.confidence == 0.0

    def test_classify_prompt(self):
        c = self._make_classifier({
            "ciloranko": "artist",
            "1girl": "other",
            "red eyes": "feature",
            "school uniform": "clothes",
            "hatsune miku": "character",
        })
        result = c.classify_prompt("ciloranko, 1girl, red eyes, school uniform, hatsune miku")
        assert result.artists == ["ciloranko"]
        assert result.characters == ["hatsune miku"]
        assert result.features == ["red eyes"]
        assert result.clothes == ["school uniform"]
        assert result.other == ["1girl"]

    def test_filter_prompt(self):
        c = self._make_classifier({
            "ciloranko": "artist",
            "1girl": "other",
            "red eyes": "feature",
        })
        result = c.filter_prompt("ciloranko, 1girl, red eyes", [TagType.ARTIST])
        assert "ciloranko" not in result
        assert "1girl" in result
        assert "red eyes" in result

    def test_select_prompt(self):
        c = self._make_classifier({
            "ciloranko": "artist",
            "1girl": "other",
            "hatsune miku": "character",
        })
        result = c.select_prompt("ciloranko, 1girl, hatsune miku", [TagType.ARTIST, TagType.CHARACTER])
        assert "ciloranko" in result
        assert "hatsune miku" in result
        assert "1girl" not in result

    def test_prompt_tag_result_to_dict(self):
        c = self._make_classifier({
            "ciloranko": "artist",
            "red eyes": "feature",
        })
        result = c.classify_prompt("ciloranko, red eyes")
        d = result.to_dict()
        assert "artist" in d
        assert "feature" in d


class TestTagTypeFromString:
    def test_direct(self):
        assert TagType.from_string("artist") == TagType.ARTIST
        assert TagType.from_string("character") == TagType.CHARACTER

    def test_legacy_normal(self):
        assert TagType.from_string("normal") == TagType.OTHER

    def test_legacy_topic(self):
        assert TagType.from_string("topic") == TagType.CHARACTER

    def test_legacy_meta(self):
        assert TagType.from_string("meta") == TagType.OTHER

    def test_unknown(self):
        assert TagType.from_string("garbage") == TagType.UNKNOWN
