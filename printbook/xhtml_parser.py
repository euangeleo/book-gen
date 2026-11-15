"""Convert XHTML sections into the semantic print-book model.

This module handles XHTML structure and semantic interpretation. CSS
resolution is delegated to css_parser.py, while CSS values are converted
to semantic rendering styles by rendering_style.py.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from lxml import etree

from .configuration import PrintBookConfiguration
from .css_parser import (
    CssCascadeResolver,
    CssStylesheet,
    ResolvedCssStyle,
    create_css_root,
)
from .model import (
    Block,
    BlockQuote,
    Bold,
    Book,
    DropCap,
    Handwriting,
    HandwritingVariant,
    Heading,
    Inline,
    Italic,
    LineBreak,
    List,
    ListItem,
    ListType,
    Paragraph,
    ParagraphStyle,
    Section,
    SectionType,
    SmallCaps,
    SMS,
    Table,
    TableCell,
    TableColumn,
    TableRow,
    Text,
)
from .rendering_style import RenderingStyleConverter


HANDWRITING_CLASS_MARKERS = (
    "handwriting",
)

SMS_CLASS_MARKERS = (
    "sms",
    "text_message",
    "text-message",
    "textmessage",
)

SMALL_CAPS_CLASS_MARKERS = (
    "smallcaps",
    "small_caps",
    "small-caps",
)

DROP_CAP_CLASS_MARKERS = (
    "dropcap",
    "drop_cap",
    "drop-cap",
)

_LENGTH_VALUE_PATTERN = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
    r"(?:[a-zA-Z%]+)?\s*$"
)


class XhtmlParser:
    """Parse configured XHTML sections into a semantic Book."""

    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        self.configuration = configuration
        self.style_converter = RenderingStyleConverter()

    def parse(self) -> Book:
        """Parse the complete configured print book."""
        sections = [
            self._parse_section(section_configuration)
            for section_configuration in self.configuration.sections
        ]

        return Book(sections=sections)

    def _parse_section(
        self,
        section_configuration,
    ) -> Section:
        """Parse one configured XHTML section."""
        root = self._load_xhtml(section_configuration.file)

        stylesheet = self._load_stylesheet(
            root,
            section_configuration.file.parent,
        )

        resolver = CssCascadeResolver(stylesheet)
        css_root = create_css_root(root)

        body = self._find_body(root)

        if body is None:
            raise ValueError(
                f"XHTML file has no <body>: "
                f"{section_configuration.file}"
            )

        body_wrapper = self._find_wrapper(css_root, body)
        body_style = resolver.resolve(body_wrapper, None)

        blocks = self._parse_nested_blocks(
            body,
            body_wrapper,
            resolver,
            section_configuration.section_type,
            body_style,
        )

        return Section(
            section_type=section_configuration.section_type,
            content=blocks,
        )

    @staticmethod
    def _load_xhtml(source_file: Path) -> etree._Element:
        """Parse one XHTML file."""
        parser = etree.XMLParser(
            recover=False,
            resolve_entities=False,
            remove_comments=True,
        )

        try:
            tree = etree.parse(str(source_file), parser)
        except etree.XMLSyntaxError as error:
            raise ValueError(
                f"Invalid XHTML in {source_file}: {error}"
            ) from error

        return tree.getroot()

    def _load_stylesheet(
        self,
        root: etree._Element,
        source_directory: Path,
    ) -> CssStylesheet:
        """Load all stylesheets referenced by an XHTML document."""
        css_text_parts: list[str] = []

        for stylesheet_path in self._find_stylesheet_paths(
            root,
            source_directory,
        ):
            try:
                css_text_parts.append(
                    stylesheet_path.read_text(encoding="utf-8")
                )
            except OSError as error:
                raise OSError(
                    f"Unable to read CSS stylesheet: {stylesheet_path}"
                ) from error

        return CssStylesheet(
            "\n".join(css_text_parts),
            source_name=str(source_directory),
        )

    @staticmethod
    def _find_stylesheet_paths(
        root: etree._Element,
        source_directory: Path,
    ) -> tuple[Path, ...]:
        """Find CSS stylesheets referenced by link elements."""
        stylesheet_paths: list[Path] = []

        for element in root.iter():
            if _local_name(element.tag) != "link":
                continue

            relationship = element.get("rel", "")

            if "stylesheet" not in relationship.lower().split():
                continue

            href = element.get("href")

            if not href:
                continue

            stylesheet_paths.append(
                (source_directory / href).resolve()
            )

        return tuple(stylesheet_paths)

    @staticmethod
    def _find_body(
        root: etree._Element,
    ) -> etree._Element | None:
        """Find the XHTML body element."""
        for element in root.iter():
            if _local_name(element.tag) == "body":
                return element

        return None

    @staticmethod
    def _find_wrapper(
        css_root,
        target: etree._Element,
    ):
        """Find the cssselect2 wrapper corresponding to an element."""
        for wrapper in css_root.iter_subtree():
            if wrapper.etree_element is target:
                return wrapper

        raise ValueError("Unable to create CSS wrapper for XHTML element.")

    def _parse_blocks(
        self,
        parent: etree._Element,
        parent_wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
    ) -> list[Block]:
        """Parse block-level children in source order."""
        parent_style = resolver.resolve(parent_wrapper, None)

        return self._parse_nested_blocks(
            parent,
            parent_wrapper,
            resolver,
            section_type,
            parent_style,
        )

    def _parse_block(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        parent_style: ResolvedCssStyle,
    ) -> list[Block]:
        """Parse one XHTML element into zero or more semantic blocks.

        Returning a list allows structural XHTML wrappers to be flattened
        into their parent's block sequence without discarding their contents.
        """
        tag_name = _local_name(element.tag)
        style = resolver.resolve(wrapper, parent_style)
        rendering_style = self.style_converter.convert(style)

        if tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return [
                Heading(
                    level=int(tag_name[1]),
                    content=self._parse_inline_content(
                        element,
                        wrapper,
                        resolver,
                        style,
                    ),
                    rendering_style=rendering_style,
                )
            ]

        if tag_name == "p":
            return [
                Paragraph(
                    content=self._parse_inline_content(
                        element,
                        wrapper,
                        resolver,
                        style,
                    ),
                    style=self._determine_paragraph_style(
                        style,
                        section_type,
                    ),
                    rendering_style=rendering_style,
                )
            ]

        if tag_name == "blockquote":
            return [
                BlockQuote(
                    content=self._parse_nested_blocks(
                        element,
                        wrapper,
                        resolver,
                        section_type,
                        style,
                    ),
                    rendering_style=rendering_style,
                )
            ]

        if tag_name in {"ol", "ul"}:
            return [
                self._parse_list(
                    element,
                    wrapper,
                    resolver,
                    section_type,
                    style,
                )
            ]

        if tag_name == "table":
            return [
                self._parse_table(
                    element,
                    wrapper,
                    resolver,
                    section_type,
                    style,
                )
            ]

        if self._is_block_container(element):
            return self._parse_nested_blocks(
                element,
                wrapper,
                resolver,
                section_type,
                style,
            )

        # Inline elements are handled by _parse_nested_blocks() when they
        # occur within a block container. They do not produce blocks here.
        return []

    def _parse_nested_blocks(
        self,
        parent: etree._Element,
        parent_wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        parent_style: ResolvedCssStyle,
    ) -> list[Block]:
        """Parse nested blocks while preserving interleaved inline content.

        Text directly inside a block container, and inline elements between
        block children, are grouped into Paragraph objects. This is important
        for list items and table cells that mix text with nested block markup.
        """
        blocks: list[Block] = []
        pending_inline: list[Inline] = []

        if parent.text:
            self._append_inline_text(
                pending_inline,
                parent.text,
                parent_style,
            )

        for child in parent:
            if not isinstance(child.tag, str):
                continue

            wrapper = self._find_wrapper(parent_wrapper, child)

            child_blocks = self._parse_block(
                child,
                wrapper,
                resolver,
                section_type,
                parent_style,
            )

            if child_blocks:
                self._flush_inline_content(
                    blocks,
                    pending_inline,
                    parent_style,
                )
                blocks.extend(child_blocks)
            else:
                child_style = resolver.resolve(wrapper, parent_style)

                pending_inline.extend(
                    self._parse_inline_element(
                        child,
                        wrapper,
                        resolver,
                        child_style,
                    )
                )

            if child.tail:
                self._append_inline_text(
                    pending_inline,
                    child.tail,
                    parent_style,
                )

        self._flush_inline_content(
            blocks,
            pending_inline,
            parent_style,
        )

        return blocks

    def _flush_inline_content(
        self,
        blocks: list[Block],
        pending_inline: list[Inline],
        parent_style: ResolvedCssStyle,
    ) -> None:
        """Convert accumulated inline content into a paragraph."""
        if not pending_inline:
            return

        # Ignore indentation and formatting whitespace between block tags.
        # Whitespace attached to actual inline content is retained.
        if not any(
            not isinstance(item, Text) or item.text.strip()
            for item in pending_inline
        ):
            pending_inline.clear()
            return

        blocks.append(
            Paragraph(
                content=list(pending_inline),
                style=ParagraphStyle.NORMAL,
                rendering_style=self.style_converter.convert(parent_style),
            )
        )

        pending_inline.clear()

    def _append_inline_text(
        self,
        content: list[Inline],
        text: str,
        style: ResolvedCssStyle,
    ) -> None:
        """Append text while ignoring whitespace-only block indentation."""
        if not text.strip():
            return

        content.append(
            Text(
                text,
                rendering_style=self.style_converter.convert(style),
            )
        )

    def _parse_list(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        style: ResolvedCssStyle,
    ) -> List:
        """Parse an ordered or unordered XHTML list."""
        list_type = (
            ListType.ORDERED
            if _local_name(element.tag) == "ol"
            else ListType.UNORDERED
        )

        items: list[ListItem] = []

        for child in element:
            if not isinstance(child.tag, str):
                continue

            if _local_name(child.tag) != "li":
                continue

            child_wrapper = self._find_wrapper(wrapper, child)
            item_style = resolver.resolve(child_wrapper, style)

            item_blocks = self._parse_nested_blocks(
                child,
                child_wrapper,
                resolver,
                section_type,
                item_style,
            )

            items.append(
                ListItem(
                    content=item_blocks,
                    rendering_style=self.style_converter.convert(
                        item_style
                    ),
                )
            )

        return List(
            list_type=list_type,
            items=items,
            rendering_style=self.style_converter.convert(style),
        )

    def _parse_table(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        style: ResolvedCssStyle,
    ) -> Table:
        """Parse an XHTML table, including column widths and cell styles."""
        rows: list[TableRow] = []

        # Incoming books do not contain nested tables, so collecting all
        # descendant rows is sufficient and includes rows in thead/tbody/tfoot.
        for row in element.iter():
            if row is element or _local_name(row.tag) != "tr":
                continue

            row_wrapper = self._find_wrapper(wrapper, row)
            row_style = resolver.resolve(row_wrapper, style)

            cells: list[TableCell] = []

            for cell in row:
                if not isinstance(cell.tag, str):
                    continue

                cell_tag = _local_name(cell.tag)

                if cell_tag not in {"th", "td"}:
                    continue

                cell_wrapper = self._find_wrapper(row_wrapper, cell)
                cell_style = resolver.resolve(cell_wrapper, row_style)

                cell_blocks = self._parse_nested_blocks(
                    cell,
                    cell_wrapper,
                    resolver,
                    section_type,
                    cell_style,
                )

                cells.append(
                    TableCell(
                        content=cell_blocks,
                        is_header=cell_tag == "th",
                        rendering_style=self.style_converter.convert(
                            cell_style
                        ),
                    )
                )

            rows.append(
                TableRow(
                    cells=cells,
                    rendering_style=self.style_converter.convert(
                        row_style
                    ),
                )
            )

        columns = self._parse_table_columns(
            element,
            wrapper,
            resolver,
            style,
            rows,
        )

        return Table(
            columns=columns,
            rows=rows,
            rendering_style=self.style_converter.convert(style),
        )

    def _parse_table_columns(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        table_style: ResolvedCssStyle,
        rows: list[TableRow],
    ) -> list[TableColumn]:
        """Read source column widths, leaving unspecified widths unset."""
        columns: list[TableColumn] = []

        for column in element.iter():
            if column is element or _local_name(column.tag) != "col":
                continue

            column_wrapper = self._find_wrapper(wrapper, column)
            column_style = resolver.resolve(
                column_wrapper,
                table_style,
            )

            width = column.get("width") or column_style.get("width")

            if width is not None:
                width = width.strip()

                # Legacy HTML width attributes sometimes omit a unit.
                if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", width):
                    width = f"{width}px"

                parsed_width = self.style_converter.parse_length(
                    width,
                    property_name="width",
                )
            else:
                parsed_width = None

            columns.append(
                TableColumn(width=parsed_width)
            )

        if columns:
            return columns

        # When no col/colgroup definitions are supplied, retain the table's
        # column count. The renderer can distribute unspecified widths evenly.
        column_count = max(
            (len(row.cells) for row in rows),
            default=0,
        )

        return [
            TableColumn(width=None)
            for _ in range(column_count)
        ]

    def _parse_inline_content(
        self,
        parent: etree._Element,
        parent_wrapper,
        resolver: CssCascadeResolver,
        parent_style: ResolvedCssStyle,
        *,
        apply_parent_style: bool = False,
    ) -> list[Inline]:
        """Parse inline content while preserving source order."""
        inline_content: list[Inline] = []

        if parent.text:
            inline_content.append(
                Text(
                    parent.text,
                    rendering_style=(
                        self.style_converter.convert(parent_style)
                        if apply_parent_style
                        else None
                    ),
                )
            )

        for child in parent:
            if not isinstance(child.tag, str):
                continue

            wrapper = self._find_wrapper(parent_wrapper, child)
            child_style = resolver.resolve(wrapper, parent_style)

            inline_content.extend(
                self._parse_inline_element(
                    child,
                    wrapper,
                    resolver,
                    child_style,
                )
            )

            if child.tail:
                inline_content.append(
                    Text(
                        child.tail,
                        rendering_style=(
                            self.style_converter.convert(parent_style)
                            if apply_parent_style
                            else None
                        ),
                    )
                )

        # Transparent inline elements preserve their recursively parsed
        # children. Apply the wrapper's style to direct text nodes; nested
        # semantic elements retain their own styles.
        return self._parse_inline_content(
            element,
            wrapper,
            resolver,
            style,
            apply_parent_style=True,
        )

    def _parse_inline_element(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        style: ResolvedCssStyle,
    ) -> list[Inline]:
        """Parse one inline XHTML element."""
        tag_name = _local_name(element.tag)
        classes = _class_names(element)
        rendering_style = self.style_converter.convert(style)

        if tag_name == "br":
            return [LineBreak()]

        content = self._parse_inline_content(
            element,
            wrapper,
            resolver,
            style,
        )

        if tag_name in {"i", "em"}:
            return [Italic(
                content=content,
                rendering_style=rendering_style,
            )]

        if tag_name in {"b", "strong"}:
            return [Bold(
                content=content,
                rendering_style=rendering_style,
            )]

        if _has_class_marker(classes, SMALL_CAPS_CLASS_MARKERS):
            return [SmallCaps(
                content=content,
                rendering_style=rendering_style,
            )]

        if _has_class_marker(classes, HANDWRITING_CLASS_MARKERS):
            return [Handwriting(
                variant=self._determine_handwriting_variant(classes),
                content=content,
                rendering_style=rendering_style,
            )]

        if _has_class_marker(classes, SMS_CLASS_MARKERS):
            return [SMS(
                content=content,
                rendering_style=rendering_style,
            )]

        if _has_class_marker(classes, DROP_CAP_CLASS_MARKERS):
            return [DropCap(
                content=content,
                rendering_style=rendering_style,
            )]

        # Ordinary spans, links, and other inline wrappers are transparent:
        # retain their recursively parsed children rather than flattening
        # their text. Their own computed style is applied to direct text.
        return [content[0]] if len(content) == 1 and _is_text_span(element) else [_TransparentInline(
            content=content,
            rendering_style=rendering_style,
        )]

    def _determine_handwriting_variant(
        self,
        classes: set[str],
    ) -> HandwritingVariant:
        """Determine the handwriting variant from class names or config."""
        normalized_classes = {
            class_name.lower().replace("_", "-")
            for class_name in classes
        }

        if any(
            "handwriting-print" in class_name
            or class_name in {"print", "handwritingprint"}
            for class_name in normalized_classes
        ):
            return HandwritingVariant.PRINT

        if any(
            "handwriting-script" in class_name
            or class_name in {"script", "handwritingscript"}
            for class_name in normalized_classes
        ):
            return HandwritingVariant.SCRIPT

        return self.configuration.fonts.handwriting.default_variant

    def _determine_paragraph_style(
        self,
        style: ResolvedCssStyle,
        section_type: SectionType,
    ) -> ParagraphStyle:
        """Determine the semantic paragraph style."""
        if section_type is SectionType.FRONT_MATTER:
            return ParagraphStyle.FRONT_MATTER

        text_indent = style.get("text-indent")

        if self._is_nonzero_length(text_indent):
            return ParagraphStyle.FIRST_INDENT

        margin_top = style.get("margin-top")
        margin_bottom = style.get("margin-bottom")

        if (
            self._is_nonzero_length(margin_top)
            and self._is_nonzero_length(margin_bottom)
        ):
            return ParagraphStyle.SPACING_BEFORE_AND_AFTER

        if self._is_nonzero_length(margin_bottom):
            return ParagraphStyle.SPACING_AFTER

        return ParagraphStyle.NORMAL

    @staticmethod
    def _is_nonzero_length(value: str | None) -> bool:
        """Return whether a CSS length represents a nonzero numeric value."""
        if value is None:
            return False

        match = _LENGTH_VALUE_PATTERN.fullmatch(value)

        if match is None:
            # For values outside the simple numeric-length syntax, avoid
            # incorrectly treating a potentially nonzero value as zero.
            return value.strip().lower() not in {
                "",
                "0",
                "0px",
                "0pt",
                "0em",
                "0rem",
                "0mm",
                "0cm",
                "0%",
            }

        return Decimal(match.group(1)) != 0

    @staticmethod
    def _is_block_container(element: etree._Element) -> bool:
        """Return whether an element may contain block-level content."""
        return _local_name(element.tag) in {
            "body",
            "div",
            "section",
            "article",
            "main",
            "header",
            "footer",
            "aside",
        }


def _local_name(tag: str) -> str:
    """Return an XML tag's local name without its namespace."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1].lower()

    return tag.lower()


def _class_names(element: etree._Element) -> set[str]:
    """Return the CSS classes assigned to an XHTML element."""
    class_attribute = element.get("class", "")

    return {
        class_name
        for class_name in class_attribute.split()
        if class_name
    }


def _has_class_marker(
    classes: set[str],
    markers: tuple[str, ...],
) -> bool:
    """Determine whether a class name contains a semantic marker."""
    normalized_classes = {
        class_name.lower().replace("_", "-")
        for class_name in classes
    }

    return any(
        marker.lower().replace("_", "-") in normalized_class
        for marker in markers
        for normalized_class in normalized_classes
    )


def _is_text_span(element: etree._Element) -> bool:
    """Return whether an element is an ordinary transparent inline wrapper."""
    return _local_name(element.tag) in {
        "span",
        "a",
        "abbr",
        "cite",
        "code",
        "q",
        "small",
        "sub",
        "sup",
    }