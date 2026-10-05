"""Render a semantic print book as LuaLaTeX source.

This module is the final transformation stage before LaTeX compilation.

The renderer knows about:

* the semantic book model;
* RenderingStyle;
* print-book configuration;
* memoir;
* LuaLaTeX;
* fontspec;
* the LaTeX packages required by the supported semantic model.

It does not know about:

* XHTML;
* CSS selectors or classes;
* EPUB files;
* CSS cascading;
* source-file paths.

The renderer produces LaTeX source but does not invoke LuaLaTeX.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from configuration import PrintBookConfiguration
from model import (
    Block,
    BlockQuote,
    Bold,
    Border,
    BorderSide,
    BorderStyle,
    DropCap,
    FontStyle,
    FontWeight,
    Handwriting,
    HandwritingVariant,
    Heading,
    Inline,
    Italic,
    Length,
    LengthUnit,
    LineBreak,
    List,
    ListItem,
    ListType,
    Paragraph,
    ParagraphStyle,
    RenderingStyle,
    Section,
    SectionBreak,
    SectionType,
    SMS,
    SmallCaps,
    Table,
    TableCell,
    TableColumn,
    TableOfContents,
    TableOfContentsEntry,
    TableRow,
    Text,
    TextAlignment,
    TextDecoration,
    TextTransform,
)


class LatexRenderingError(ValueError):
    """Raised when the semantic model cannot be rendered as LaTeX."""


@dataclass(frozen=True)
class RenderedChapterTitle:
    """The three title forms required by memoir's chapter command."""

    toc_title: str
    head_title: str
    title: str


class LatexRenderer:
    """Render a semantic Book as LuaLaTeX source."""

    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        self.configuration = configuration
        self._font_macros: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, book) -> str:
        """Render a complete semantic book as LuaLaTeX source."""
        self._validate_book(book)
        self._collect_configured_fonts()

        toc_entries = self._table_of_contents_entries(book)
        chapters = self._chapters(book)

        lines: list[str] = []

        lines.extend(self._render_preamble())
        lines.extend(
            [
                "",
                r"\begin{document}",
                "",
            ]
        )

        lines.extend(
            self._render_book(
                book,
                toc_entries=toc_entries,
                chapters=chapters,
            )
        )

        lines.extend(
            [
                "",
                r"\end{document}",
                "",
            ]
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_book(self, book) -> None:
        """Validate the structural assumptions of the renderer."""
        sections = book.sections

        if not sections:
            raise LatexRenderingError(
                "The book contains no sections."
            )

        chapters = self._chapters(book)

        if not chapters:
            raise LatexRenderingError(
                "Book must contain at least one chapter."
            )

        counts = {
            section_type: sum(
                section.section_type == section_type
                for section in sections
            )
            for section_type in SectionType
        }

        for section_type in (
            SectionType.TITLE_PAGE,
            SectionType.FRONT_MATTER,
            SectionType.TABLE_OF_CONTENTS,
            SectionType.BACK_MATTER,
        ):
            if counts[section_type] > 1:
                raise LatexRenderingError(
                    f"Book contains more than one "
                    f"{section_type.value} section."
                )

        toc_sections = [
            section
            for section in sections
            if section.section_type
            == SectionType.TABLE_OF_CONTENTS
        ]

        if len(toc_sections) != 1:
            raise LatexRenderingError(
                "Book must contain exactly one "
                "table-of-contents section."
            )

        toc = self._find_table_of_contents(toc_sections[0])

        if len(toc.entries) != len(chapters):
            raise LatexRenderingError(
                "The number of table-of-contents entries "
                f"({len(toc.entries)}) does not match the number "
                f"of chapters ({len(chapters)})."
            )

        for number, chapter in enumerate(chapters, start=1):
            self._find_chapter_heading(
                chapter,
                chapter_number=number,
            )

        self._validate_font_configuration(book)

    def _validate_font_configuration(self, book) -> None:
        """Validate fonts required by the semantic model."""
        configured_paths = self.configuration.fonts.paths

        required_families: set[str] = set()

        if self.configuration.fonts.body is not None:
            required_families.add(
                self.configuration.fonts.body
            )

        if self.configuration.fonts.sms is not None:
            required_families.add(
                self.configuration.fonts.sms
            )

        handwriting = self.configuration.fonts.handwriting

        for family in (
            handwriting.print,
            handwriting.script,
        ):
            if family is not None:
                required_families.add(family)

        for section in book.sections:
            for block in section.content:
                self._collect_block_font_families(
                    block,
                    required_families,
                )

        missing = sorted(
            family
            for family in required_families
            if family not in configured_paths
        )

        if missing:
            names = ", ".join(repr(name) for name in missing)

            raise LatexRenderingError(
                "The following font families are used or configured "
                f"but have no entry in fonts.paths: {names}."
            )

    def _collect_block_font_families(
        self,
        block: Block,
        families: set[str],
    ) -> None:
        """Collect font families referenced by a semantic block."""
        style = getattr(block, "rendering_style", None)

        if style is not None and style.font_family is not None:
            families.add(style.font_family)

        if isinstance(block, Paragraph):
            self._collect_inline_font_families(
                block.content,
                families,
            )
            return

        if isinstance(block, Heading):
            self._collect_inline_font_families(
                block.content,
                families,
            )
            return

        if isinstance(block, BlockQuote):
            for child in block.content:
                self._collect_block_font_families(
                    child,
                    families,
                )
            return

        if isinstance(block, SectionBreak):
            self._collect_inline_font_families(
                block.content,
                families,
            )
            return

        if isinstance(block, List):
            for item in block.items:
                self._collect_block_font_families(
                    item,
                    families,
                )
            return

        if isinstance(block, ListItem):
            for child in block.content:
                self._collect_block_font_families(
                    child,
                    families,
                )
            return

        if isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    self._collect_block_font_families(
                        cell,
                        families,
                    )
            return

        if isinstance(block, TableRow):
            for cell in block.cells:
                self._collect_block_font_families(
                    cell,
                    families,
                )
            return

        if isinstance(block, TableCell):
            for child in block.content:
                self._collect_block_font_families(
                    child,
                    families,
                )

    def _collect_inline_font_families(
        self,
        content: Iterable[Inline],
        families: set[str],
    ) -> None:
        """Collect font families referenced by inline content."""
        for inline in content:
            style = getattr(
                inline,
                "rendering_style",
                None,
            )

            if (
                style is not None
                and style.font_family is not None
            ):
                families.add(style.font_family)

            if isinstance(inline, Handwriting):
                configuration = (
                    self.configuration.fonts.handwriting
                )

                family = (
                    configuration.print
                    if inline.variant
                    == HandwritingVariant.PRINT
                    else configuration.script
                )

                if family is None:
                    family = (
                        configuration.print
                        if configuration.default_variant
                        == HandwritingVariant.PRINT
                        else configuration.script
                    )

                if family is not None:
                    families.add(family)

            elif isinstance(inline, SMS):
                if self.configuration.fonts.sms is not None:
                    families.add(
                        self.configuration.fonts.sms
                    )

            if isinstance(inline, DropCap):
                self._collect_inline_font_families(
                    inline.content,
                    families,
                )

            elif isinstance(inline, (
                Italic,
                Bold,
                SmallCaps,
                Handwriting,
                SMS,
            )):
                self._collect_inline_font_families(
                    inline.content,
                    families,
                )

    # ------------------------------------------------------------------
    # Book structure
    # ------------------------------------------------------------------

    @staticmethod
    def _chapters(book) -> list[Section]:
        """Return chapter sections in source order."""
        return [
            section
            for section in book.sections
            if section.section_type == SectionType.CHAPTER
        ]

    @staticmethod
    def _table_of_contents_entries(
        book,
    ) -> list[TableOfContentsEntry]:
        """Return semantic TOC entries in source order."""
        sections = [
            section
            for section in book.sections
            if section.section_type
            == SectionType.TABLE_OF_CONTENTS
        ]

        if len(sections) != 1:
            raise LatexRenderingError(
                "Book must contain exactly one TOC section."
            )

        toc = LatexRenderer._find_table_of_contents(
            sections[0]
        )

        return toc.entries

    @staticmethod
    def _find_table_of_contents(
        section: Section,
    ) -> TableOfContents:
        """Find the single TableOfContents block."""
        blocks = [
            block
            for block in section.content
            if isinstance(block, TableOfContents)
        ]

        if len(blocks) != 1:
            raise LatexRenderingError(
                "The TOC section must contain exactly one "
                "TableOfContents block."
            )

        return blocks[0]

    @staticmethod
    def _find_chapter_heading(
        section: Section,
        chapter_number: int | None,
    ) -> Heading:
        """Return the required H1 heading for a chapter."""
        headings = [
            block
            for block in section.content
            if isinstance(block, Heading)
            and block.level == 1
        ]

        if len(headings) != 1:
            number = (
                f" {chapter_number}"
                if chapter_number is not None
                else ""
            )

            raise LatexRenderingError(
                f"Chapter{number} must contain exactly one "
                "level-1 heading."
            )

        return headings[0]

    # ------------------------------------------------------------------
    # Preamble
    # ------------------------------------------------------------------

    def _render_preamble(self) -> list[str]:
        """Render the LuaLaTeX document preamble."""
        lines = [
            r"\documentclass[oneside]{memoir}",
            "",
            r"\usepackage{fontspec}",
            r"\usepackage{lettrine}",
            r"\usepackage{changepage}",
            r"\usepackage{tabularx}",
            r"\usepackage{array}",
            r"\usepackage{ragged2e}",
            "",
            r"\setsecnumdepth{chapter}",
            r"\settocdepth{chapter}",
            "",
        ]

        lines.extend(self._render_geometry())
        lines.append("")

        lines.extend(self._render_fonts())
        lines.append("")

        return lines

    def _render_geometry(self) -> list[str]:
        """Render memoir page dimensions and margins."""
        page = self.configuration.page
        margins = self.configuration.margins

        return [
            (
                r"\setstocksize"
                f"{{{self._measurement(page.height)}}}"
                f"{{{self._measurement(page.width)}}}"
            ),
            (
                r"\settrimmedsize"
                f"{{{self._measurement(page.height)}}}"
                f"{{{self._measurement(page.width)}}}"
                r"{*}"
            ),
            (
                r"\setlrmarginsandblock"
                f"{{{self._measurement(margins.outer)}}}"
                f"{{{self._measurement(margins.inner)}}}"
                r"{*}"
            ),
            (
                r"\setulmarginsandblock"
                f"{{{self._measurement(margins.top)}}}"
                f"{{{self._measurement(margins.bottom)}}}"
                r"{*}"
            ),
            r"\checkandfixthelayout",
        ]

    def _collect_configured_fonts(self) -> None:
        """Assign deterministic LaTeX command names to font families."""
        self._font_macros.clear()

        for number, family in enumerate(
            sorted(self.configuration.fonts.paths),
            start=1,
        ):
            self._font_macros[family] = (
                rf"\BookFont{number}"
            )

    def _render_fonts(self) -> list[str]:
        """Render fontspec declarations."""
        lines: list[str] = []

        for family in sorted(
            self.configuration.fonts.paths
        ):
            path = Path(
                self.configuration.fonts.paths[family]
            )

            macro = self._font_macro(family)

            directory = self._latex_directory(path)
            filename = self._latex_font_filename(path)

            options = (
                f"Path={{{directory}}}"
                if directory
                else ""
            )

            if options:
                lines.append(
                    rf"\newfontfamily{macro}"
                    f"[{options}]"
                    rf"{{{filename}}}"
                )
            else:
                lines.append(
                    rf"\newfontfamily{macro}"
                    rf"{{{filename}}}"
                )

        body = self.configuration.fonts.body

        if body is not None:
            macro = self._font_macro(body)

            lines.append(
                rf"\renewcommand{{\familydefault}}{{{macro}}}"
            )

        return lines

    def _font_macro(self, family_name: str) -> str:
        """Return the generated LaTeX macro for a font family."""
        try:
            return self._font_macros[family_name]
        except KeyError as error:
            raise LatexRenderingError(
                f"Font family {family_name!r} is not configured."
            ) from error

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _render_book(
        self,
        book,
        *,
        toc_entries: list[TableOfContentsEntry],
        chapters: list[Section],
    ) -> list[str]:
        """Render sections while associating chapters with TOC entries."""
        lines: list[str] = []

        chapter_index = 0
        current_division: str | None = None

        for section in book.sections:
            division = self._division_for_section(section)

            if division != current_division:
                lines.extend(
                    [
                        division,
                        "",
                    ]
                )
                current_division = division

            if section.section_type == SectionType.CHAPTER:
                toc_entry = toc_entries[chapter_index]

                lines.extend(
                    self._render_chapter(
                        section,
                        toc_entry,
                    )
                )

                chapter_index += 1

            else:
                lines.extend(
                    self._render_section(section)
                )

            lines.append("")

        return self._remove_final_blank_line(lines)

    @staticmethod
    def _division_for_section(
        section: Section,
    ) -> str:
        """Return the memoir division associated with a section."""
        if section.section_type in {
            SectionType.TITLE_PAGE,
            SectionType.FRONT_MATTER,
            SectionType.TABLE_OF_CONTENTS,
        }:
            return r"\frontmatter"

        if section.section_type == SectionType.CHAPTER:
            return r"\mainmatter"

        if section.section_type == SectionType.BACK_MATTER:
            return r"\backmatter"

        raise LatexRenderingError(
            f"Unsupported section type: {section.section_type!r}"
        )

    def _render_section(
        self,
        section: Section,
    ) -> list[str]:
        """Render a non-chapter section."""
        if section.section_type == SectionType.TITLE_PAGE:
            return self._render_title_page(section)

        if section.section_type == SectionType.TABLE_OF_CONTENTS:
            return self._render_toc_section(section)

        return self._render_blocks(section.content)

    def _render_title_page(
        self,
        section: Section,
    ) -> list[str]:
        """Render a title-page section."""
        lines = [
            r"\begin{titlingpage}",
            "",
        ]

        lines.extend(
            self._render_blocks(section.content)
        )

        lines.extend(
            [
                "",
                r"\end{titlingpage}",
            ]
        )

        return lines

    def _render_toc_section(
        self,
        section: Section,
    ) -> list[str]:
        """Render the semantic TOC using memoir's generated TOC."""
        toc = self._find_table_of_contents(section)

        lines: list[str] = []

        if toc.heading:
            lines.append(
                self._render_inline_content(
                    toc.heading
                )
            )
            lines.append("")

        lines.append(r"\tableofcontents")

        return lines

    def _render_chapter(
        self,
        section: Section,
        toc_entry: TableOfContentsEntry,
    ) -> list[str]:
        """Render one chapter and its associated TOC entry."""
        heading = self._find_chapter_heading(
            section,
            chapter_number=None,
        )

        title = self._render_chapter_title(
            heading,
            toc_entry,
        )

        chapter_command = (
            r"\chapter"
            f"[{title.toc_title}]"
            f"[{title.head_title}]"
            f"{{{title.title}}}"
        )

        lines = [
            chapter_command,
            "",
        ]

        remaining = [
            block
            for block in section.content
            if block is not heading
        ]

        lines.extend(
            self._render_blocks(remaining)
        )

        return lines

    def _render_chapter_title(
        self,
        heading: Heading,
        toc_entry: TableOfContentsEntry,
    ) -> RenderedChapterTitle:
        """Construct memoir's TOC, running-head, and full title forms."""
        toc_title = self._render_inline_content(
            toc_entry.title
        )

        before_break: list[Inline] = []

        for inline in heading.content:
            if isinstance(inline, LineBreak):
                break

            before_break.append(inline)

        head_title = self._render_inline_content(
            before_break
        )

        title = self._render_inline_content(
            heading.content
        )

        return RenderedChapterTitle(
            toc_title=toc_title,
            head_title=head_title,
            title=title,
        )

    # ------------------------------------------------------------------
    # Blocks
    # ------------------------------------------------------------------

    def _render_blocks(
        self,
        blocks: Iterable[Block],
    ) -> list[str]:
        """Render a sequence of blocks."""
        lines: list[str] = []

        for block in blocks:
            rendered = self._render_block(block)

            if rendered:
                lines.extend(rendered)
                lines.append("")

        return self._remove_final_blank_line(lines)

    def _render_block(
        self,
        block: Block,
    ) -> list[str]:
        """Render one block."""
        if isinstance(block, Heading):
            return self._render_heading(block)

        if isinstance(block, Paragraph):
            return self._render_paragraph(block)

        if isinstance(block, BlockQuote):
            return self._render_block_quote(block)

        if isinstance(block, SectionBreak):
            return self._render_section_break(block)

        if isinstance(block, List):
            return self._render_list(block)

        if isinstance(block, Table):
            return self._render_table(block)

        raise LatexRenderingError(
            f"Unsupported block type: {type(block).__name__}"
        )

    def _render_heading(
        self,
        heading: Heading,
    ) -> list[str]:
        """Render a non-chapter heading."""
        if heading.level == 1:
            raise LatexRenderingError(
                "Level-1 headings are reserved for chapter titles."
            )

        content = self._render_inline_content(
            heading.content
        )

        return self._render_block_with_style(
            content,
            heading.rendering_style,
        )

    def _render_paragraph(
        self,
        paragraph: Paragraph,
    ) -> list[str]:
        """Render a paragraph and its paragraph-level style."""
        content = self._render_inline_content(
            paragraph.content
        )

        if paragraph.style == ParagraphStyle.FIRST_INDENT:
            content = r"\indent " + content

        elif paragraph.style == ParagraphStyle.FRONT_MATTER:
            content = rf"\centering {content}"

        return self._render_block_with_style(
            content,
            paragraph.rendering_style,
        )

    def _render_block_quote(
        self,
        block_quote: BlockQuote,
    ) -> list[str]:
        """Render a block quote."""
        lines = self._render_blocks(
            block_quote.content
        )

        return self._render_box(
            lines,
            block_quote.rendering_style,
            default_left="2em",
            default_right="2em",
        )

    def _render_section_break(
        self,
        section_break: SectionBreak,
    ) -> list[str]:
        """Render a deliberate section break."""
        content = self._render_inline_content(
            section_break.content
        )

        return self._render_block_with_style(
            content,
            section_break.rendering_style,
        )

    # ------------------------------------------------------------------
    # Lists
    # ------------------------------------------------------------------

    def _render_list(
        self,
        list_block: List,
    ) -> list[str]:
        """Render an ordered or unordered list."""
        environment = (
            "enumerate"
            if list_block.list_type == ListType.ORDERED
            else "itemize"
        )

        lines = [
            rf"\begin{{{environment}}}",
        ]

        for item in list_block.items:
            lines.extend(
                self._render_list_item(item)
            )

        lines.append(
            rf"\end{{{environment}}}"
        )

        return self._render_box(
            lines,
            list_block.rendering_style,
        )

    def _render_list_item(
        self,
        item: ListItem,
    ) -> list[str]:
        """Render one list item."""
        lines = [
            r"\item",
        ]

        content = self._render_blocks(
            item.content
        )

        lines.extend(
            f"    {line}"
            for line in content
        )

        return self._render_box(
            lines,
            item.rendering_style,
        )

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------

    def _render_table(
        self,
        table: Table,
    ) -> list[str]:
        """Render a semantic table using tabularx."""
        column_count = self._table_column_count(table)

        if column_count == 0:
            raise LatexRenderingError(
                "Cannot render a table without columns."
            )

        specification = self._table_column_specification(
            table,
            column_count,
        )

        lines = [
            (
                r"\begin{tabularx}"
                rf"{{\linewidth}}{{{specification}}}"
            ),
        ]

        for row_number, row in enumerate(
            table.rows,
            start=1,
        ):
            lines.extend(
                self._render_table_row(
                    row,
                    column_count,
                    row_number,
                )
            )

        lines.append(
            r"\end{tabularx}"
        )

        return self._render_box(
            lines,
            table.rendering_style,
        )

    @staticmethod
    def _table_column_count(
        table: Table,
    ) -> int:
        """Return the number of columns in a table."""
        if table.columns:
            return len(table.columns)

        if not table.rows:
            return 0

        return max(
            len(row.cells)
            for row in table.rows
        )

    def _table_column_specification(
        self,
        table: Table,
        column_count: int,
    ) -> str:
        """Create the tabularx column specification."""
        if not table.columns:
            return " ".join(
                ">{\\raggedright\\arraybackslash}X"
                for _ in range(column_count)
            )

        if len(table.columns) != column_count:
            raise LatexRenderingError(
                "Table column metadata does not match "
                "the number of table columns."
            )

        specification: list[str] = []

        for column in table.columns:
            if column.width is None:
                specification.append(
                    r">{\raggedright\arraybackslash}X"
                )
            else:
                width = self._length(
                    column.width,
                    percent_reference=r"\linewidth",
                )

                specification.append(
                    r">{\raggedright\arraybackslash}"
                    rf"p{{{width}}}"
                )

        return " ".join(specification)

    def _render_table_row(
        self,
        row: TableRow,
        column_count: int,
        row_number: int,
    ) -> list[str]:
        """Render one table row."""
        if len(row.cells) != column_count:
            raise LatexRenderingError(
                f"Table row {row_number} contains "
                f"{len(row.cells)} cells; expected "
                f"{column_count}."
            )

        cells = [
            self._render_table_cell(cell)
            for cell in row.cells
        ]

        return [
            " & ".join(cells) + r" \\",
        ]

    def _render_table_cell(
        self,
        cell: TableCell,
    ) -> str:
        """Render one table cell."""
        content = "\n".join(
            self._render_blocks(cell.content)
        )

        if cell.is_header:
            content = rf"\textbf{{{content}}}"

        return self._apply_block_style_to_inline_content(
            content,
            cell.rendering_style,
        )

    # ------------------------------------------------------------------
    # Inline content
    # ------------------------------------------------------------------

    def _render_inline_content(
        self,
        content: Iterable[Inline],
    ) -> str:
        """Render inline objects in source order."""
        return "".join(
            self._render_inline(inline)
            for inline in content
        )

    def _render_inline(
        self,
        inline: Inline,
    ) -> str:
        """Render one inline object."""
        if isinstance(inline, Text):
            return self._render_text(inline)

        if isinstance(inline, LineBreak):
            return r"\\"

        if isinstance(inline, Italic):
            return self._render_inline_wrapper(
                inline,
                r"\textit",
            )

        if isinstance(inline, Bold):
            return self._render_inline_wrapper(
                inline,
                r"\textbf",
            )

        if isinstance(inline, SmallCaps):
            return self._render_inline_wrapper(
                inline,
                r"\textsc",
            )

        if isinstance(inline, Handwriting):
            return self._render_handwriting(inline)

        if isinstance(inline, SMS):
            return self._render_sms(inline)

        if isinstance(inline, DropCap):
            return self._render_drop_cap(inline)

        raise LatexRenderingError(
            f"Unsupported inline type: {type(inline).__name__}"
        )

    def _render_text(
        self,
        text: Text,
    ) -> str:
        """Render ordinary text."""
        escaped = self._escape_latex(
            text.text
        )

        return self._render_inline_style(
            escaped,
            text.rendering_style,
        )

    def _render_inline_wrapper(
        self,
        inline: Italic
        | Bold
        | SmallCaps
        | Handwriting
        | SMS,
        command: str,
    ) -> str:
        """Render an inline semantic wrapper."""
        content = self._render_inline_content(
            inline.content
        )

        rendered = rf"{command}{{{content}}}"

        return self._render_inline_style(
            rendered,
            inline.rendering_style,
        )

    def _render_handwriting(
        self,
        handwriting: Handwriting,
    ) -> str:
        """Render handwriting using the configured font family."""
        configuration = (
            self.configuration.fonts.handwriting
        )

        if handwriting.variant == HandwritingVariant.PRINT:
            family = configuration.print
        else:
            family = configuration.script

        if family is None:
            if (
                configuration.default_variant
                == HandwritingVariant.PRINT
            ):
                family = configuration.print
            else:
                family = configuration.script

        if family is None:
            raise LatexRenderingError(
                "No font is configured for handwriting "
                f"variant {handwriting.variant.value!r}."
            )

        macro = self._font_macro(family)

        content = self._render_inline_content(
            handwriting.content
        )

        rendered = rf"{{{macro} {content}}}"

        return self._render_inline_style(
            rendered,
            handwriting.rendering_style,
        )

    def _render_sms(
        self,
        sms: SMS,
    ) -> str:
        """Render SMS content using fonts.sms."""
        family = self.configuration.fonts.sms

        if family is None:
            raise LatexRenderingError(
                "SMS content requires fonts.sms to be configured."
            )

        macro = self._font_macro(family)

        content = self._render_inline_content(
            sms.content
        )

        rendered = rf"{{{macro} {content}}}"

        return self._render_inline_style(
            rendered,
            sms.rendering_style,
        )

    def _render_drop_cap(
        self,
        drop_cap: DropCap,
    ) -> str:
        """Render a drop cap using lettrine."""
        content = self._render_inline_content(
            drop_cap.content
        )

        if not content:
            return ""

        # DropCap content is expected to begin with ordinary text.
        # The semantic parser should normally produce a single Text
        # object for the initial drop-cap sequence.
        first = content[0]
        remainder = content[1:]

        rendered = (
            rf"\lettrine{{{first}}}"
            rf"{{{remainder}}}"
        )

        return self._render_inline_style(
            rendered,
            drop_cap.rendering_style,
        )

    # ------------------------------------------------------------------
    # Rendering styles
    # ------------------------------------------------------------------

    def _render_inline_style(
        self,
        content: str,
        style: RenderingStyle | None,
    ) -> str:
        """Apply style properties whose scope is inline content."""
        if style is None:
            return content

        result = content

        if style.text_transform == TextTransform.UPPERCASE:
            result = rf"\MakeUppercase{{{result}}}"

        if style.text_decoration == TextDecoration.UNDERLINE:
            result = rf"\underline{{{result}}}"

        if style.font_weight == FontWeight.BOLD:
            result = rf"\textbf{{{result}}}"

        if style.font_style == FontStyle.ITALIC:
            result = rf"\textit{{{result}}}"

        if style.text_alignment is not None:
            result = self._wrap_inline_alignment(
                result,
                style.text_alignment,
            )

        if style.font_family is not None:
            macro = self._font_macro(
                style.font_family
            )

            result = rf"{{{macro} {result}}}"

        if style.font_size is not None:
            size = self._length(
                style.font_size,
                percent_reference=r"\f@size pt",
            )

            result = (
                rf"{{\fontsize{{{size}}}"
                r"{\baselineskip}"
                rf"\selectfont {result}}}"
            )

        if style.foreground_color is not None:
            result = self._apply_foreground_color(
                result,
                style.foreground_color.value,
            )

        return result

    def _render_paragraph_style(
        self,
        content: str,
        style: RenderingStyle | None,
    ) -> str:
        """Apply paragraph-level style properties."""
        if style is None:
            return content

        result = content

        if style.text_alignment is not None:
            result = self._wrap_paragraph_alignment(
                result,
                style.text_alignment,
            )

        if style.line_height is not None:
            result = self._wrap_line_height(
                result,
                style.line_height,
            )

        if style.text_indent is not None:
            indent = self._length(
                style.text_indent,
                percent_reference=r"\linewidth",
            )

            result = (
                rf"\setlength{{\parindent}}{{{indent}}}"
                "\n"
                + result
            )

        return result

    def _render_block_with_style(
        self,
        content: str,
        style: RenderingStyle | None,
    ) -> list[str]:
        """Render a block with paragraph and box-level styles."""
        if style is None:
            return [content]

        lines: list[str] = []

        if style.page_break_before:
            lines.append(r"\clearpage")

        paragraph_content = self._render_paragraph_style(
            content,
            style,
        )

        boxed = self._render_box(
            [paragraph_content],
            style,
        )

        lines.extend(boxed)

        return lines

    def _apply_block_style_to_inline_content(
        self,
        content: str,
        style: RenderingStyle | None,
    ) -> str:
        """Apply appropriate style properties to table-cell content."""
        if style is None:
            return content

        return self._render_inline_style(
            content,
            style,
        )

    # ------------------------------------------------------------------
    # Boxes, margins, padding, borders
    # ------------------------------------------------------------------

    def _render_box(
        self,
        lines: list[str],
        style: RenderingStyle | None,
        *,
        default_left: str | None = None,
        default_right: str | None = None,
    ) -> list[str]:
        """Wrap block content in any required box-level constructs."""
        if style is None:
            if (
                default_left is None
                and default_right is None
            ):
                return lines

            left = default_left or "0pt"
            right = default_right or "0pt"

            return [
                rf"\begin{{adjustwidth}}{{{left}}}{{{right}}}",
                *lines,
                r"\end{adjustwidth}",
            ]

        result = list(lines)

        if style.page_break_before:
            result.insert(0, r"\clearpage")

        left = style.margin_left
        right = style.margin_right

        if (
            left is not None
            or right is not None
            or default_left is not None
            or default_right is not None
        ):
            left_value = (
                self._length(
                    left,
                    percent_reference=r"\linewidth",
                )
                if left is not None
                else default_left or "0pt"
            )

            right_value = (
                self._length(
                    right,
                    percent_reference=r"\linewidth",
                )
                if right is not None
                else default_right or "0pt"
            )

            result = [
                (
                    rf"\begin{{adjustwidth}}"
                    rf"{{{left_value}}}{{{right_value}}}"
                ),
                *result,
                r"\end{adjustwidth}",
            ]

        padding = style.padding

        if padding is not None:
            result = self._wrap_padding(
                result,
                padding,
            )

        border = style.border

        if border is not None:
            result = self._wrap_border(
                result,
                border,
            )

        return result

    def _wrap_padding(
        self,
        lines: list[str],
        padding,
    ) -> list[str]:
        """Apply box padding."""
        top = self._length_or_zero(
            padding.top,
            percent_reference=r"\linewidth",
        )
        right = self._length_or_zero(
            padding.right,
            percent_reference=r"\linewidth",
        )
        bottom = self._length_or_zero(
            padding.bottom,
            percent_reference=r"\linewidth",
        )
        left = self._length_or_zero(
            padding.left,
            percent_reference=r"\linewidth",
        )

        return [
            (
                r"\begin{adjustwidth}"
                rf"{{{left}}}{{{right}}}"
            ),
            rf"\vspace*{{{top}}}",
            *lines,
            rf"\vspace*{{{bottom}}}",
            r"\end{adjustwidth}",
        ]

    def _wrap_border(
        self,
        lines: list[str],
        border: Border,
    ) -> list[str]:
        """Render supported border styles."""
        sides = (
            border.top,
            border.right,
            border.bottom,
            border.left,
        )

        if all(
            side is None
            or side.style == BorderStyle.NONE
            for side in sides
        ):
            return lines

        # The initial semantic model supports solid borders, but does
        # not require a particular visual implementation.  Use
        # LaTeX's \fbox for a simple all-sides border.  For asymmetric
        # borders, generate a warning-worthy semantic error rather
        # than silently rendering the wrong appearance.
        if not self._is_uniform_solid_border(border):
            raise LatexRenderingError(
                "Only uniform solid borders are currently "
                "supported by the LaTeX renderer."
            )

        width = self._border_width(
            border.top
            or border.right
            or border.bottom
            or border.left
        )

        return [
            rf"\setlength{{\fboxrule}}{{{width}}}",
            r"\fbox{%",
            r"\begin{minipage}{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}",
            *lines,
            r"\end{minipage}%",
            r"}",
        ]

    @staticmethod
    def _is_uniform_solid_border(
        border: Border,
    ) -> bool:
        """Determine whether all specified borders are equivalent."""
        sides = [
            border.top,
            border.right,
            border.bottom,
            border.left,
        ]

        specified = [
            side
            for side in sides
            if side is not None
        ]

        if not specified:
            return False

        if any(
            side.style != BorderStyle.SOLID
            for side in specified
        ):
            return False

        first = specified[0]

        for side in specified[1:]:
            if side.width != first.width:
                return False

            if side.color != first.color:
                return False

        return True

    def _border_width(
        self,
        side: BorderSide,
    ) -> str:
        """Return the width of a border side."""
        if side.width is None:
            return "0.4pt"

        return self._length(
            side.width,
            percent_reference=r"\linewidth",
        )

    # ------------------------------------------------------------------
    # Alignment and line height
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_inline_alignment(
        content: str,
        alignment: TextAlignment,
    ) -> str:
        """Apply alignment to inline content when meaningful."""
        commands = {
            TextAlignment.LEFT: r"\makebox[0pt][l]",
            TextAlignment.CENTER: r"\makebox[0pt][c]",
            TextAlignment.RIGHT: r"\makebox[0pt][r]",
            TextAlignment.JUSTIFY: r"\makebox[0pt][l]",
        }

        return (
            f"{commands[alignment]}"
            rf"{{{content}}}"
        )

    @staticmethod
    def _wrap_paragraph_alignment(
        content: str,
        alignment: TextAlignment,
    ) -> str:
        """Apply block-level text alignment."""
        commands = {
            TextAlignment.LEFT: r"\raggedright",
            TextAlignment.CENTER: r"\centering",
            TextAlignment.RIGHT: r"\raggedleft",
            TextAlignment.JUSTIFY: r"\justifying",
        }

        return (
            commands[alignment]
            + "\n"
            + content
        )

    def _wrap_line_height(
        self,
        content: str,
        line_height: Length,
    ) -> str:
        """Apply a semantic line-height value."""
        value = self._length(
            line_height,
            percent_reference=r"\baselineskip",
        )

        return (
            rf"\setlength{{\baselineskip}}{{{value}}}"
            "\n"
            + content
        )

    # ------------------------------------------------------------------
    # Colors
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_foreground_color(
        content: str,
        value: str,
    ) -> str:
        """Apply a color using xcolor."""
        # xcolor is deliberately included only when color is actually
        # needed; see _render_preamble_with_colors below if this
        # capability is enabled globally.
        #
        # The semantic model stores colors independently of CSS.
        # The renderer currently expects values suitable for xcolor,
        # such as named colors or hexadecimal values.
        normalized = value.strip()

        if normalized.startswith("#"):
            normalized = normalized[1:]

            if len(normalized) not in {3, 6}:
                raise LatexRenderingError(
                    f"Unsupported hexadecimal color: {value!r}"
                )

            return (
                rf"\textcolor[HTML]{{{normalized}}}"
                rf"{{{content}}}"
            )

        return (
            rf"\textcolor{{{normalized}}}"
            rf"{{{content}}}"
        )

    # ------------------------------------------------------------------
    # Lengths and measurements
    # ------------------------------------------------------------------

    @staticmethod
    def _measurement(measurement) -> str:
        """Convert a configuration measurement to LaTeX."""
        return (
            f"{measurement.value}"
            f"{measurement.unit}"
        )

    def _length(
        self,
        length: Length,
        *,
        percent_reference: str,
    ) -> str:
        """Convert a semantic Length to a LaTeX dimension."""
        value = str(length.value)

        if length.unit == LengthUnit.EM:
            return f"{value}em"

        if length.unit == LengthUnit.PT:
            return f"{value}pt"

        if length.unit == LengthUnit.MM:
            return f"{value}mm"

        if length.unit == LengthUnit.PX:
            points = (
                length.value
                * Decimal(72)
                / Decimal(96)
            )

            return (
                f"{points.normalize()}pt"
            )

        if length.unit == LengthUnit.PERCENT:
            factor = length.value / Decimal(100)

            return (
                f"{factor.normalize()}"
                f"{percent_reference}"
            )

        raise LatexRenderingError(
            f"Unsupported LengthUnit: {length.unit!r}"
        )

    def _length_or_zero(
        self,
        length: Length | None,
        *,
        percent_reference: str,
    ) -> str:
        """Convert an optional length, using zero for None."""
        if length is None:
            return "0pt"

        return self._length(
            length,
            percent_reference=percent_reference,
        )

    # ------------------------------------------------------------------
    # LaTeX escaping and filesystem paths
    # ------------------------------------------------------------------

    @staticmethod
    def _escape_latex(text: str) -> str:
        """Escape characters with special meaning in LaTeX."""
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }

        return "".join(
            replacements.get(
                character,
                character,
            )
            for character in text
        )

    @staticmethod
    def _latex_directory(
        path: Path,
    ) -> str:
        """Return a LaTeX-compatible font directory."""
        parent = path.parent

        if str(parent) in {"", "."}:
            return ""

        return (
            str(parent)
            .replace("\\", "/")
            .rstrip("/")
            + "/"
        )

    @staticmethod
    def _latex_font_filename(
        path: Path,
    ) -> str:
        """Return the font filename."""
        return path.name

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_final_blank_line(
        lines: list[str],
    ) -> list[str]:
        """Remove redundant blank lines from the end of a result."""
        result = list(lines)

        while result and result[-1] == "":
            result.pop()

        return result
