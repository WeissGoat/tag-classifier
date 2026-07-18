"""Tag type definitions and data models for tag classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TagType(str, Enum):
    """Supported tag types — 6 values only.

    Using str mixin so values serialize naturally to JSON and compare with plain strings.
    """

    CHARACTER = "character"     # 角色名 + 作品/IP 名
    FEATURE = "feature"         # 外貌特征: red hair, red eyes, twintails
    CLOTHES = "clothes"         # 穿着/配饰: dress, skirt, boots
    ARTIST = "artist"           # 画师串: 画师名 + 质量词 (best quality, absurdres, year tags 等)
    OTHER = "other"             # 动作, 表情, 场景, 其他
    UNKNOWN = "unknown"         # 未分类

    @classmethod
    def from_string(cls, value: str) -> TagType:
        """Flexible string → TagType conversion with legacy compatibility."""
        value = value.strip().lower()
        try:
            return cls(value)
        except ValueError:
            pass
        # Legacy aliases from old Danbooru-based system
        aliases = {
            "normal": cls.OTHER,
            "topic": cls.CHARACTER,
            "meta": cls.OTHER,
            "special": cls.OTHER,
            "general": cls.OTHER,
            "copyright": cls.CHARACTER,
            "tag-type-0": cls.OTHER,
            "tag-type-1": cls.ARTIST,
            "tag-type-3": cls.CHARACTER,
            "tag-type-4": cls.CHARACTER,
            "tag-type-5": cls.OTHER,
        }
        return aliases.get(value, cls.UNKNOWN)


@dataclass
class TagClassification:
    """Result of classifying a single tag."""

    tag: str                    # Original tag as provided
    normalized: str             # Normalized form used for matching
    tag_type: TagType = TagType.UNKNOWN
    confidence: float = 1.0     # 0.0 ~ 1.0
    source: str = "none"        # Which source provided this classification


@dataclass
class PromptTagResult:
    """Structured result of tagging a complete prompt.

    Groups tags by their classified type for easy access.
    """

    original: str
    classifications: list[TagClassification] = field(default_factory=list)

    def by_type(self, tag_type: TagType) -> list[str]:
        """Get all tags of a specific type."""
        return [tc.tag for tc in self.classifications if tc.tag_type == tag_type]

    @property
    def artists(self) -> list[str]:
        return self.by_type(TagType.ARTIST)

    @property
    def characters(self) -> list[str]:
        return self.by_type(TagType.CHARACTER)

    @property
    def features(self) -> list[str]:
        return self.by_type(TagType.FEATURE)

    @property
    def clothes(self) -> list[str]:
        return self.by_type(TagType.CLOTHES)

    @property
    def other(self) -> list[str]:
        return self.by_type(TagType.OTHER)

    @property
    def unknown(self) -> list[str]:
        return self.by_type(TagType.UNKNOWN)

    def to_dict(self) -> dict[str, list[str]]:
        """Group all classified tags by type name."""
        result: dict[str, list[str]] = {}
        for tc in self.classifications:
            key = tc.tag_type.value
            if key not in result:
                result[key] = []
            result[key].append(tc.tag)
        return result

    def filter(self, exclude: list[TagType]) -> str:
        """Return prompt with specified types removed."""
        exclude_set = set(exclude)
        return ", ".join(
            tc.tag for tc in self.classifications
            if tc.tag_type not in exclude_set
        )

    def select(self, include: list[TagType]) -> str:
        """Return prompt with only specified types kept."""
        include_set = set(include)
        return ", ".join(
            tc.tag for tc in self.classifications
            if tc.tag_type in include_set
        )
