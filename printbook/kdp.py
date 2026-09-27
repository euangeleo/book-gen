"""KDP-specific print requirements.

This module contains rules specific to Amazon KDP paperback manuscript
requirements. It should not contain book-specific configuration.

The minimum inside (gutter) margin depends on the final page count.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GutterRequirement:
    """A KDP minimum gutter requirement for a page-count range."""

    minimum_pages: int
    maximum_pages: int
    minimum_gutter_inches: Decimal


KDP_GUTTER_REQUIREMENTS: tuple[GutterRequirement, ...] = (
    GutterRequirement(24, 150, Decimal("0.375")),
    GutterRequirement(151, 300, Decimal("0.500")),
    GutterRequirement(301, 500, Decimal("0.625")),
    GutterRequirement(501, 700, Decimal("0.750")),
    GutterRequirement(701, 828, Decimal("0.875")),
)


def get_minimum_gutter_inches(page_count: int) -> Decimal:
    """Return the KDP minimum gutter for a given page count.

    Raises:
        ValueError: If the page count is outside the KDP range represented
            by this module.
    """
    for requirement in KDP_GUTTER_REQUIREMENTS:
        if requirement.minimum_pages <= page_count <= requirement.maximum_pages:
            return requirement.minimum_gutter_inches

    raise ValueError(
        f"KDP gutter requirements do not cover {page_count} pages."
    )