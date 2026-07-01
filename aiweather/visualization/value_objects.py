"""Visualization value objects for AI Weather."""

from dataclasses import dataclass
from enum import StrEnum

from .normalizer import HtmlNormalizer


class VisualizationStatus(StrEnum):
    UP_TO_DATE = "up_to_date"
    OUTDATED = "outdated"
    GENERATING = "generating"


@dataclass(frozen=True, slots=True)
class Visualization:
    raw: str
    normalized: str

    @classmethod
    def from_raw(cls, raw: str, normalizer: HtmlNormalizer) -> "Visualization":
        return cls(raw=raw, normalized=normalizer.normalize(raw))
