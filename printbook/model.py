"""Semantic model for print books.

This module defines the intermediate representation used by the print-book
pipeline. It intentionally contains no EPUB, XHTML, CSS, YAML, or LaTeX
logic.

The model represents the semantic structure of a book and the meaningful
typographic and rendering distinctions that must survive conversion from EPUB
to print.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
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


class FontWeight(Enum):
    """Font weights supported by the initial rendering model."""

    NORMAL = "normal"
    BOLD = "bold"


class FontStyle(Enum):
    """Font styles supported by the initial rendering model."""

    NORMAL = "normal"
    ITALIC = "italic"


class TextAlignment(Enum):
    """Text alignment values supported by the rendering model."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class TextTransform(Enum):
    """Text transformations supported by the rendering model."""

    NONE = "none"
    UPPERCASE = "uppercase"


class TextDecoration(Enum):
    """Text decorations supported by the rendering model."""

    NONE = "none"
    UNDERLINE = "underline"


class BorderStyle(Enum):
    """Border styles supported by the initial rendering model."""

    NONE = "none"
    SOLID = "solid"


class LengthUnit(Enum):
    """Units that may occur in source rendering measurements."""

    EM = "em"
    PT = "pt"
    MM = "mm"
    PERCENT = "%"
    PX = "px"


@dataclass(frozen=True)
class Length:
    """A numeric rendering measurement together with its unit.

    The value is retained without prematurely converting relative units such
    as em or percent to an absolute measurement.
    """

    value: Decimal
    unit: LengthUnit


@dataclass(frozen=True)
class Color:
    """A rendering color represented independently of CSS syntax."""

    value: str


@dataclass(frozen=True)
class Padding:
    """Padding measurements for the four sides of a box."""

    top: Length | None = None
    right: Length | None = None
    bottom: Length | None = None
    left: Length | None = None


@dataclass(frozen=True)
class BorderSide:
    """Rendering information for one side of a border."""

    width: Length | None = None
    color: Color | None = None
    style: BorderStyle = BorderStyle.NONE


@dataclass(frozen=True)
class Border:
    """Border rendering information for the four sides of a box."""

    top: BorderSide | None = None
    right: BorderSide | None = None
    bottom: BorderSide | None = None
    left: BorderSide | None = None


@dataclass(frozen=True)
class LineBreak(Inline):
    """A deliberate line break within inline content."""


@dataclass(frozen=True)
class RenderingStyle:
    """Resolved rendering information associated with model content.

    This object represents rendering requirements derived from the source
    content and its styles. It contains no CSS selectors, CSS class names,
    CSS property names, or LaTeX-specific constructs.
    """

    font_family: str | None = None
    font_size: Length | None = None
    font_weight: FontWeight | None = None
    font_style: FontStyle | None = None
    line_height: Length | None = None
    letter_spacing: Length | None = None

    text_alignment: TextAlignment | None = None
    text_indent: Length | None = None
    margin_top: Length | None = None
    margin_right: Length | None = None
    margin_bottom: Length | None = None
    margin_left: Length | None = None

    text_transform: TextTransform | None = None
    text_decoration: TextDecoration | None = None
    foreground_color: Color | None = None
    background_color: Color | None = None

    padding: Padding | None = None
    border: Border | None = None

    page_break_before: bool = False


class Inline:
    """Base class for all inline content."""


class Block:
    """Base class for all block-level content."""


@dataclass(frozen=True)
class Text(Inline):
    """Ordinary textual content."""

    text: str
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class StyledInline(Inline):
    """Base class for inline content containing other inline content."""

    content: list[Inline] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


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


@dataclass(frozen=True)
class DropCap(StyledInline):
    """Text receiving a drop-cap typographic treatment."""


InlineContent: TypeAlias = list[Inline]


@dataclass(frozen=True)
class Heading(Block):
    """A heading at a particular structural level."""

    level: int
    content: InlineContent = field(default_factory=list)
    rendering_style: RenderingStyle | None = None

    def __post_init__(self) -> None:
        """Validate the heading level."""
        if not 1 <= self.level <= 4:
            raise ValueError("Heading level must be between 1 and 4.")


@dataclass(frozen=True)
class Paragraph(Block):
    """A paragraph of text with a semantic paragraph style."""

    content: InlineContent = field(default_factory=list)
    style: ParagraphStyle = ParagraphStyle.NORMAL
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class BlockQuote(Block):
    """Text presented as a quotation.

    The rendering style of a BlockQuote applies to the quote as a whole.
    Paragraphs contained within the block quote retain their own paragraph-
    level formatting.
    """

    content: list[Block] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class SectionBreak(Block):
    """A deliberate break between textual sections.

    A section break may contain text. Its visual representation is determined
    by the rendering style and the LaTeX renderer.
    """

    content: InlineContent = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class ListItem(Block):
    """One item within an ordered or unordered list."""

    content: list[Block] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class List(Block):
    """An ordered or unordered collection of list items."""

    list_type: ListType
    items: list[ListItem] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class TableCell(Block):
    """A cell within a table."""

    content: list[Block] = field(default_factory=list)
    is_header: bool = False
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class TableRow(Block):
    """A row within a table."""

    cells: list[TableCell] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


@dataclass(frozen=True)
class TableColumn:
    """Rendering information for one table column."""

    width: Length | None = None


@dataclass(frozen=True)
class Table(Block):
    """Tabular content consisting of ordered rows."""

    columns: list[TableColumn] = field(default_factory=list)
    rows: list[TableRow] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None


BlockContent: TypeAlias = list[Block]


@dataclass(frozen=True)
class TableOfContentsEntry:
    """One chapter entry in the print book's table of contents."""

    title: InlineContent = field(default_factory=list)


@dataclass(frozen=True)
class TableOfContents(Block):
    """The semantic table of contents for the print book."""

    heading: InlineContent = field(default_factory=list)
    entries: list[TableOfContentsEntry] = field(
        default_factory=list
    )


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
