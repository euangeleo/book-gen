```python
"""Semantic model for print books.

This module defines the intermediate representation used by the print-book
pipeline.  It intentionally contains no EPUB, XHTML, CSS, YAML, or LaTeX
logic.

The model represents the semantic structure of a book and the meaningful
typographic distinctions that must survive conversion from EPUB to print.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias


class SectionType(Enum):
    """Types of major sections in a print book."""

    FRONT_MATTER = "front_matter"
    TITLE_PAGE = "title_page"
    TABLE_OF_CONTENTS = "table_of_contents"
    CHAPTER = "chapter"
    BACK_MATTER = "back_matter"


class ParagraphStyle(Enum):
    """Semantic paragraph styles supported by the initial model."""

    NORMAL = "normal"
    FIRST_INDENT = "first_indent"
    SPACING_AFTER = "spacing_after"
    SPACING_BEFORE_AND_AFTER = "spacing_before_and_after"
    FRONT_MATTER = "front_matter"


class ListType(Enum):
    """Types of lists supported by the semantic model."""

    ORDERED = "ordered"
    UNORDERED = "unordered"


class HandwritingVariant(Enum):
    """Variants of handwriting-style text."""

    SCRIPT = "script"
    PRINT = "print"


class Inline:
    """Base class for all inline content."""


class Block:
    """Base class for all block-level content."""


@dataclass(frozen=True)
class Text(Inline):
    """Ordinary, unstyled textual content."""

    text: str


@dataclass(frozen=True)
class StyledInline(Inline):
    """Base class for inline content containing other inline content."""

    content: list[Inline] = field(default_factory=list)


@dataclass(frozen=True)
class Italic(StyledInline):
    """Text that should be rendered in italic."""


@dataclass(frozen=True)
class Bold(StyledInline):
    """Text that should be rendered in bold."""


@dataclass(frozen=True)
class SmallCaps(StyledInline):
    """Text that should be rendered in small capitals."""


@dataclass(frozen=True)
class Handwriting(StyledInline):
    """Text intended to be rendered in a handwriting-style typeface."""

    variant: HandwritingVariant = HandwritingVariant.SCRIPT


@dataclass(frozen=True)
class SMS(StyledInline):
    """Text intended to be rendered as SMS or text-message content."""


InlineContent: TypeAlias = list[Inline]


@dataclass(frozen=True)
class Heading(Block):
    """A heading at a particular structural level."""

    level: int
    content: InlineContent = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the heading level."""
        if not 1 <= self.level <= 4:
            raise ValueError("Heading level must be between 1 and 4.")


@dataclass(frozen=True)
class Paragraph(Block):
    """A paragraph of text with a semantic paragraph style."""

    content: InlineContent = field(default_factory=list)
    style: ParagraphStyle = ParagraphStyle.NORMAL


@dataclass(frozen=True)
class BlockQuote(Block):
    """Text presented as a quotation.

    The spacing, indentation, and other block-level formatting of a BlockQuote apply
    to the quote as a whole. Paragraphs contained within the block quote retain their
    own paragraph-level formatting.
    """

    content: list[Block] = field(default_factory=list)


@dataclass(frozen=True)
class SectionBreak(Block):
    """A deliberate break between textual sections.

    A section break may contain text.  Its visual representation is determined
    by the LaTeX renderer and print configuration.
    """

    content: InlineContent = field(default_factory=list)


@dataclass(frozen=True)
class ListItem(Block):
    """One item within an ordered or unordered list."""

    content: list[Block] = field(default_factory=list)


@dataclass(frozen=True)
class List(Block):
    """An ordered or unordered collection of list items."""

    list_type: ListType
    items: list[ListItem] = field(default_factory=list)


BlockContent: TypeAlias = list[Block]


@dataclass(frozen=True)
class Section:
    """A major sequential section of a print book."""

    section_type: SectionType
    content: BlockContent = field(default_factory=list)


@dataclass(frozen=True)
class Book:
    """The complete semantic representation of a print book."""

    sections: list[Section] = field(default_factory=list)
    title: str | None = None
    author: str | None = None
```
