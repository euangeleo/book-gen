"""Render the semantic print-book model as LuaLaTeX source.

This module is the final transformation stage before LaTeX compilation.

The renderer knows about:
    * the semantic model;
    * RenderingStyle;
    * print-book configuration;
    * memoir;
    * LuaLaTeX/fontspec conventions.

It does not know about:
    * XHTML;
    * CSS selectors or classes;
    * EPUB files;
    * CSS cascading;
    * source-file paths.

The renderer produces LaTeX source but does not invoke LuaLaTeX.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from configuration import PrintBookConfiguration
from model import (
    Block,
    BlockQuote,
    Bold,
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
    """The three title forms required by memoir's \\chapter command."""

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

    def render(self, book) -> str:
        """Return complete LuaLaTeX source for a semantic book."""
        self._validate_book(book)
        self._collect_configured_fonts()

        lines: list[str] = []

        lines.extend(self._render_preamble(book))
        lines.append(r"\begin{document}")
        lines.append("")

        lines.extend(self._render_book(book))

        lines.append("")
        lines.append(r"\end{document}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_book(self, book) -> None:
        """Validate structural assumptions required by the renderer."""
        sections = book.sections

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

        chapters = [
            section
            for section in sections
            if section.section_type == SectionType.CHAPTER
        ]

        if not chapters:
            raise LatexRenderingError(
                "Book must contain at least one chapter."
            )

        toc_sections = [
            section
            for section in sections
            if section.section_type
            == SectionType.TABLE_OF_CONTENTS
        ]

        if len(toc_sections) != 1:
            raise LatexRenderingError(
                "Book must contain exactly one table-of-contents section."
            )

        toc = self._find_table_of_contents(toc_sections[0])

        if len(toc.entries) != len(chapters):
            raise LatexRenderingError(
                "The number of table-of-contents entries "
                f"({len(toc.entries)}) does not match the number "
                f"of chapters ({len(chapters)})."
            )

        for chapter_number, chapter in enumerate(chapters, start=1):
            self._find_chapter_heading(
                chapter,
                chapter_number,
            )

    # ------------------------------------------------------------------
    # Preamble
    # ------------------------------------------------------------------

    def _render_preamble(self, book) -> list[str]:
        """Render the LaTeX document preamble."""
        lines = [
            r"\documentclass[oneside]{memoir}",
            "",
            r"\usepackage{fontspec}",
            r"\usepackage{lettrine}",
            r"\usepackage{changepage}",
            r"\usepackage{tabularx}",
            r"\usepackage{array}",
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
        """Render memoir page geometry."""
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

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------

    def _collect_configured_fonts(self) -> None:
        """Assign deterministic LaTeX macros to configured font families."""
        self._font_macros.clear()

        font_paths = self.configuration.fonts.paths

        for index, family_name in enumerate(
            sorted(font_paths),
            start=1,
        ):
            self._font_macros[family_name] = (
                rf"\BookFont{index}"
            )

    def _render_fonts(self) -> list[str]:
        """Render fontspec declarations for configured fonts."""
        lines: list[str] = []

        for family_name in sorted(
            self.configuration.fonts.paths
        ):
            macro = self._font_macros[family_name]
            font_path = self.configuration.fonts.paths[family_name]

            lines.append(
                rf"\newfontfamily{macro}"
                rf"[Path={self._latex_directory(font_path)}]"
                rf"{{{self._latex_font_filename(font_path)}}}"
            )

        body_family = self.configuration.fonts.body

        if body_family is not None:
            body_macro = self._font_macro(body_family)
            lines.append(
                rf"\renewcommand{{\familydefault}}{{{body_macro}}}"
            )

        return lines

    def _font_macro(self, family_name: str) -> str:
        """Return the LaTeX macro associated with a font family."""
        try:
            return self._font_macros[family_name]
        except KeyError as error:
            raise LatexRenderingError(
                f"Font family {family_name!r} is not configured."
            ) from error

    # ------------------------------------------------------------------
    # Book structure
    # ------------------------------------------------------------------

    def _render_book(self, book) -> list[str]:
        """Render all sections in source order."""
        lines: list[str] = []

        current_division: str | None = None

        for section in book.sections:
            division = self._division_for_section(section)

            if division != current_division:
                lines.append(division)
                lines.append("")
                current_division = division

            lines.extend(self._render_section(section))
            lines.append("")

        return lines

    @staticmethod
    def _division_for_section(section: Section) -> str:
        """Return the memoir division command for a section."""
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
            f"Unsupported section type: {section.section_type}"
        )

    def _render_section(self, section: Section) -> list[str]:
        """Render one semantic book section."""
        if section.section_type == SectionType.TABLE_OF_CONTENTS:
            return self._render_toc_section(section)

        if section.section_type == SectionType.CHAPTER:
            return self._render_chapter(section)

        if section.section_type == SectionType.TITLE_PAGE:
            return self._render_title_page(section)

        return self._render_blocks(section.content)

    # ------------------------------------------------------------------
    # Title page
    # ------------------------------------------------------------------

    def _render_title_page(
        self,
        section: Section,
    ) -> list[str]:
        """Render the title-page section."""
        lines = [
            r"\begin{titlingpage}",
            "",
        ]

        lines.extend(self._render_blocks(section.content))

        lines.extend(
            [
                "",
                r"\end{titlingpage}",
            ]
        )

        return lines

    # ------------------------------------------------------------------
    # Table of contents
    # ------------------------------------------------------------------

    def _render_toc_section(
        self,
        section: Section,
    ) -> list[str]:
        """Render a semantic TOC as a generated LaTeX TOC."""
        toc = self._find_table_of_contents(section)

        lines: list[str] = []

        # The source TOC heading is retained semantically, but the printed
        # entries themselves are generated by LaTeX.
        if toc.heading:
            lines.extend(
                self._render_inline_content(
                    toc.heading,
                )
            )
            lines.append("")

        lines.append(r"\tableofcontents")

        return lines

    @staticmethod
    def _find_table_of_contents(
        section: Section,
    ) -> TableOfContents:
        """Find the TableOfContents block in a TOC section."""
        toc_blocks = [
            block
            for block in section.content
            if isinstance(block, TableOfContents)
        ]

        if len(toc_blocks) != 1:
            raise LatexRenderingError(
                "The table-of-contents section must contain exactly "
                "one TableOfContents block."
            )

        return toc_blocks[0]

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    def _render_chapter(
        self,
        section: Section,
    ) -> list[str]:
        """Render one chapter."""
        heading = self._find_chapter_heading(
            section,
            None,
        )

        toc = self._find_toc_for_chapter(section)

        title = self._rendered_chapter_title(
            heading,
            toc,
        )

        lines = [
            (
                r"\chapter"
                f"[{title.toc_title}]"
                f"[{title.head_title}]"
                f"{{{title.title}}}"
            ),
            "",
        ]

        remaining_blocks = [
            block
            for block in section.content
            if block is not heading
        ]

        lines.extend(
            self._render_blocks(remaining_blocks)
        )

        return lines

    def _find_chapter_heading(
        self,
        section: Section,
        chapter_number: int | None,
    ) -> Heading:
        """Return the chapter's required H1 heading."""
        headings = [
            block
            for block in section.content
            if isinstance(block, Heading)
            and block.level == 1
        ]

        if len(headings) != 1:
            number_text = (
                f" {chapter_number}"
                if chapter_number is not None
                else ""
            )

            raise LatexRenderingError(
                f"Chapter{number_text} must contain exactly one "
                "level-1 heading."
            )

        return headings[0]

    def _find_toc_for_chapter(
        self,
        chapter: Section,
    ) -> TableOfContentsEntry:
        """Return the TOC entry corresponding to a chapter.

        This method is intentionally implemented by positional lookup in
        _render_book's chapter sequence.
        """
        chapters = [
            section
            for section in self.configuration._book.sections
            if section.section_type == SectionType.CHAPTER
        ]

        chapter_index = chapters.index(chapter)

        toc_section = next(
            section
            for section in self.configuration._book.sections
            if section.section_type
            == SectionType.TABLE_OF_CONTENTS
        )

        toc = self._find_table_of_contents(toc_section)

        return toc.entries[chapter_index]

    def _rendered_chapter_title(
        self,
        heading: Heading,
        toc_entry: TableOfContentsEntry,
    ) -> RenderedChapterTitle:
        """Construct memoir's three chapter-title forms."""
        toc_title = self._render_inline_content(
            toc_entry.title
        )

        head_content: list[Inline] = []

        for inline in heading.content:
            if isinstance(inline, LineBreak):
                break

            head_content.append(inline)

        head_title = self._render_inline_content(
            head_content
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
        """Render a sequence of block objects."""
        lines: list[str] = []

        for block in blocks:
            rendered = self._render_block(block)

            if rendered:
                lines.extend(rendered)
                lines.append("")

        return lines[:-1] if lines else lines

    def _render_block(
        self,
        block: Block,
    ) -> list[str]:
        """Render one semantic block."""
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
                "Level-1 headings are rendered only as chapter titles."
            )

        content = self._render_inline_content(
            heading.content
        )

        return self._render_styled_block(
            content,
            heading.rendering_style,
        )

    def _render_paragraph(
        self,
        paragraph: Paragraph,
    ) -> list[str]:
        """Render one paragraph."""
        content = self._render_inline_content(
            paragraph.content
        )

        if paragraph.style == ParagraphStyle.FIRST_INDENT:
            content = r"\indent " + content

        return self._render_styled_block(
            content,
            paragraph.rendering_style,
        )

    def _render_block_quote(
        self,
        block_quote: BlockQuote,
    ) -> list[str]:
        """Render a block quotation."""
        lines = [
            r"\begin{adjustwidth}{2em}{2em}",
        ]

        lines.extend(
            self._render_blocks(block_quote.content)
        )

        lines.append(r"\end{adjustwidth}")

        return self._wrap_block_style(
            lines,
            block_quote.rendering_style,
        )

    def _render_section_break(
        self,
        section_break: SectionBreak,
    ) -> list[str]:
        """Render a deliberate section break."""
        content = self._render_inline_content(
            section_break.content
        )

        return self._render_styled_block(
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

        lines = [rf"\begin{{{environment}}}"]

        for item in list_block.items:
            lines.extend(
                self._render_list_item(item)
            )

        lines.append(
            rf"\end{{{environment}}}"
        )

        return self._wrap_block_style(
            lines,
            list_block.rendering_style,
        )

    def _render_list_item(
        self,
        item: ListItem,
    ) -> list[str]:
        """Render one list item."""
        lines = [r"\item"]

        content = self._render_blocks(item.content)

        if content:
            lines.extend(
                "    " + line
                for line in content
            )

        return self._wrap_block_style(
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
        """Render a semantic table."""
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
            rf"\begin{{tabularx}}{{\linewidth}}{{{specification}}}",
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

        lines.append(r"\end{tabularx}")

        return self._wrap_block_style(
            lines,
            table.rendering_style,
        )

    @staticmethod
    def _table_column_count(
        table: Table,
    ) -> int:
        """Determine the number of table columns."""
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
        """Create a tabularx column specification."""
        columns = table.columns

        if not columns:
            return " ".join(
                "X"
                for _ in range(column_count)
            )

        if len(columns) != column_count:
            raise LatexRenderingError(
                "Table column metadata does not match "
                "the number of table columns."
            )

        specification: list[str] = []

        for column in columns:
            if column.width is None:
                specification.append("X")
            else:
                specification.append(
                    ">{\\raggedright\\arraybackslash}"
                    f"p{{{self._length("column.width,
                        percent_reference=r'\\linewidth',
                    )}}}"
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

        return content

    # ------------------------------------------------------------------
    # Inline content
    # ------------------------------------------------------------------

    def _render_inline_content(
        self,
        content: Iterable[Inline],
    ) -> str:
        """Render an ordered sequence of inline objects."""
        return "".join(
            self._render_inline(inline)
            for inline in content
        )

    def _render_inline(
        self,
        inline: Inline,
    ) -> str:
        """Render one semantic inline object."""
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
        """Render ordinary text with LaTeX escaping."""
        escaped = self._escape_latex(text.text)

        return self._apply_rendering_style(
            escaped,
            text.rendering_style,
        )

    def _render_inline_wrapper(
        self,
        inline,
        command: str,
    ) -> str:
        """Render an inline semantic wrapper."""
        content = self._render_inline_content(
            inline.content
        )

        rendered = rf"{command}{{{content}}}"

        return self._apply_rendering_style(
            rendered,
            inline.rendering_style,
        )

    def _render_handwriting(
        self,
        handwriting: Handwriting,
    ) -> str:
        """Render handwriting using the configured font family."""
        configuration = self.configuration.fonts.handwriting

        variant = handwriting.variant

        if variant == HandwritingVariant.PRINT:
            family = configuration.print
        elif variant == HandwritingVariant.SCRIPT:
            family = configuration.script
        else:
            raise LatexRenderingError(
                f"Unsupported handwriting variant: {variant}"
            )

        if family is None:
            default_variant = configuration.default_variant

            if default_variant == HandwritingVariant.PRINT:
                family = configuration.print
            else:
                family = configuration.script

        if family is None:
            raise LatexRenderingError(
                f"No font configured for handwriting variant "
                f"{variant.value!r}."
            )

        macro = self._font_macro(family)

        content = self._render_inline_content(
            handwriting.content
        )

        rendered = rf"{{{macro} {content}}}"

        return self._apply_rendering_style(
            rendered,
            handwriting.rendering_style,
        )

    def _render_sms(
        self,
        sms: SMS,
    ) -> str:
        """Render SMS content using the configured SMS font."""
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

        return self._apply_rendering_style(
            rendered,
            sms.rendering_style,
        )

    def _render_drop_cap(
        self,
        drop_cap: DropCap,
    ) -> str:
        """Render a semantic drop cap with lettrine."""
        content = self._render_inline_content(
            drop_cap.content
        )

        if not content:
            return ""

        first_character = content[0]
        remainder = content[1:]

        rendered = rf"\lettrine{{{first_character}}}{{{remainder}}}"

        return self._apply_rendering_style(
            rendered,
            drop_cap.rendering_style,
        )

    # ------------------------------------------------------------------
    # RenderingStyle
    # ------------------------------------------------------------------

    def _render_styled_block(
        self,
        content: str,
        style: RenderingStyle | None,
    ) -> list[str]:
        """Render content while applying its block rendering style."""
        lines: list[str] = []

        if style is not None and style.page_break_before:
            lines.append(r"\clearpage")

        rendered = self._apply_rendering_style(
            content,
            style,
        )

        lines.append(rendered)

        return lines

    def _wrap_block_style(
        self,
        lines: list[str],
        style: RenderingStyle | None,
    ) -> list[str]:
        """Apply block-level style requiring an environment."""
        if style is None:
            return lines

        if style.page_break_before:
            lines.insert(0, r"\clearpage")

        left = style.margin_left
        right = style.margin_right

        if left is None and right is None:
            return lines

        left_value = (
            self._length(
                left,
                percent_reference=r"\linewidth",
            )
            if left is not None
            else "0pt"
        )

        right_value = (
            self._length(
                right,
                percent_reference=r"\linewidth",
            )
            if right is not None
            else "0pt"
        )

        return [
            rf"\begin{{adjustwidth}}{{{left_value}}}"
            rf"{{{right_value}}}",
            *lines,
            r"\end{adjustwidth}",
        ]

    def _apply_rendering_style(
        self,
        content: str,
        style: RenderingStyle | None,
    ) -> str:
        """Apply inline-compatible RenderingStyle properties."""
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

        if style.font_family is not None:
            macro = self._font_macro(style.font_family)
            result = rf"{{{macro} {result}}}"

        if style.font_size is not None:
            size = self._length(
                style.font_size,
                percent_reference=r"\f@size pt",
            )

            result = rf"{{\fontsize{{{size}}}{{\baselineskip}}"
            result += rf"\selectfont {content}}}"

        return result

    # ------------------------------------------------------------------
    # Lengths and measurements
    # ------------------------------------------------------------------

    def _measurement(self, measurement) -> str:
        """Convert a configuration Measurement to LaTeX."""
        return f"{measurement.value}{measurement.unit}"

    def _length(
        self,
        length: Length,
        *,
        percent_reference: str,
    ) -> str:
        """Convert a semantic Length into a LaTeX length."""
        value = str(length.value)

        if length.unit == LengthUnit.EM:
            return f"{value}em"

        if length.unit == LengthUnit.PT:
            return f"{value}pt"

        if length.unit == LengthUnit.MM:
            return f"{value}mm"

        if length.unit == LengthUnit.PX:
            # TeX does not have a native px unit. CSS px is traditionally
            # interpreted as 96 dpi, so convert it to points.
            points = length.value * 72 / 96
            return f"{points.normalize()}pt"

        if length.unit == LengthUnit.PERCENT:
            factor = length.value / 100
            return f"{factor.normalize()}{percent_reference}"

        raise LatexRenderingError(
            f"Unsupported LengthUnit: {length.unit}"
        )

    # ------------------------------------------------------------------
    # LaTeX escaping
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
            replacements.get(character, character)
            for character in text
        )

    # ------------------------------------------------------------------
    # Font paths
    # ------------------------------------------------------------------

    @staticmethod
    def _latex_directory(path: Path) -> str:
        """Return the directory portion of a font path."""
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
    def _latex_font_filename(path: Path) -> str:
        """Return the filename portion of a font path."""
        return path.name