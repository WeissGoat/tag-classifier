"""Tests for tag normalizer."""

from tag_classifier.normalizer import (
    normalize_tag,
    split_tags,
    standardize_artist,
    includes_substring,
    filter_inner_substrings,
    strip_weight,
)


class TestNormalizeTag:
    def test_basic(self):
        assert normalize_tag("Red_Eyes") == "red eyes"

    def test_weight_brackets(self):
        assert normalize_tag("{ciloranko}") == "ciloranko"
        assert normalize_tag("[[[ke-ta]]]") == "ke-ta"

    def test_artist_prefix(self):
        assert normalize_tag("artist: Ciloranko") == "ciloranko"
        assert normalize_tag("Artist:wlop") == "wlop"

    def test_whitespace(self):
        assert normalize_tag("  red   eyes  ") == "red eyes"

    def test_encoding_artifacts(self):
        assert normalize_tag("red\xa0eyes") == "red eyes"
        assert normalize_tag("red，eyes") == "red,eyes"


class TestSplitTags:
    def test_basic(self):
        assert split_tags("red eyes, 1girl, blue hair") == ["red eyes", "1girl", "blue hair"]

    def test_skip_blank(self):
        assert split_tags("a, , b, ,c") == ["a", "b", "c"]

    def test_custom_pattern(self):
        assert split_tags("a\n\nb\n\nc", "\n\n") == ["a", "b", "c"]


class TestStripWeight:
    def test_basic(self):
        assert strip_weight("{{{red eyes}}}") == "red eyes"
        assert strip_weight("[ke-ta]") == "ke-ta"


class TestStandardizeArtist:
    def test_basic(self):
        assert standardize_artist("ciloranko") == "ciloranko"

    def test_with_prefix(self):
        assert standardize_artist("artist: Ciloranko") == "ciloranko"

    def test_with_brackets(self):
        assert standardize_artist("{ke-ta}") == "ke-ta"


class TestIncludesSubstring:
    def test_found(self):
        assert includes_substring("hatsune miku vocaloid", ["miku", "reimu"]) == "miku"

    def test_not_found(self):
        assert includes_substring("red eyes", ["blue", "green"]) is None

    def test_dict_keys(self):
        assert includes_substring("ciloranko", {"cilo": True, "wlop": True}) == "cilo"


class TestFilterInnerSubstrings:
    def test_basic(self):
        # filter_inner_substrings removes items that contain other items as substrings
        # "red eyes" contains "red", so "red eyes" is removed
        result = filter_inner_substrings(["red", "red eyes", "blue"])
        assert "red" in result
        assert "red eyes" not in result
        assert "blue" in result
