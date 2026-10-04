"""Convert XHTML sections into the semantic print-book model.

This module handles XHTML structure and semantic interpretation. CSS
resolution is delegated to css_parser.py.

Conversion of resolved CSS into RenderingStyle objects is intentionally
deferred to a later rendering-style converter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from configuration import PrintBookConfiguration
from css_parser import (
    CssCascadeResolver,
    CssStylesheet,
    ResolvedCssStyle,
    create_css_root,
)
from model import (
    Block,
    BlockQuote,
    Bold,
    DropCap,
    Handwriting,
    HandwritingVariant,
    Heading,
    Inline,
    Italic,
    List,
    ListItem,
    ListType,
    Paragraph,
    ParagraphStyle,
    Section,
    SectionBreak,
    SectionType,
    SmallCaps,
    SMS,
    Table,
    TableCell,
    TableRow,
    Text,
)


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


@dataclass(frozen=True)
class ParsedElement:
    """An XHTML element together with its resolved CSS style."""

    element: etree._Element
    style: ResolvedCssStyle


class XhtmlBookParser:
    """Parse configured XHTML sections into a semantic Book."""

    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        self.configuration = configuration

    def parse(self) -> "Book":
        """Parse the complete configured print book."""
        from model import Book

        sections = tuple(
            self._parse_section(section_configuration)
            for section_configuration in self.configuration.sections
        )

        return Book(
            sections=list(sections),
            title=self.configuration.book.title,
            author=self.configuration.book.author,
        )

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

        body_wrapper = self._find_wrapper(
            css_root,
            body,
        )

        blocks = self._parse_blocks(
            body,
            body_wrapper,
            resolver,
            section_configuration.section_type,
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
        blocks: list[Block] = []

        for child in parent:
            if not isinstance(child.tag, str):
                continue

            wrapper = self._find_wrapper(
                parent_wrapper,
                child,
            )

            parsed_block = self._parse_block(
                child,
                wrapper,
                resolver,
                section_type,
                parent_style=resolver.resolve(
                    parent_wrapper,
                    None,
                ),
            )

            if parsed_block is not None:
                blocks.append(parsed_block)

        return blocks

    def _parse_block(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        parent_style: ResolvedCssStyle,
    ) -> Block | None:
        """Parse one XHTML element as a semantic block."""
        tag_name = _local_name(element.tag)
        style = resolver.resolve(wrapper, parent_style)

        if tag_name in {"h1", "h2", "h3", "h4"}:
            return Heading(
                level=int(tag_name[1]),
                content=self._parse_inline_content(
                    element,
                    wrapper,
                    resolver,
                    style,
                ),
            )

        if tag_name == "p":
            return Paragraph(
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
            )

        if tag_name == "blockquote":
            return BlockQuote(
                content=self._parse_nested_blocks(
                    element,
                    wrapper,
                    resolver,
                    section_type,
                    style,
                ),
            )

        if tag_name in {"ol", "ul"}:
            return self._parse_list(
                element,
                wrapper,
                resolver,
                section_type,
                style,
            )

        if tag_name == "table":
            return self._parse_table(
                element,
                wrapper,
                resolver,
                section_type,
                style,
            )

        if self._is_section_break(element, style):
            return SectionBreak(
                content=self._parse_inline_content(
                    element,
                    wrapper,
                    resolver,
                    style,
                ),
            )

        if self._is_block_container(element):
            nested_blocks = self._parse_nested_blocks(
                element,
                wrapper,
                resolver,
                section_type,
                style,
            )

            if nested_blocks:
                return _combine_blocks(nested_blocks)

        return None

    def _parse_nested_blocks(
        self,
        parent: etree._Element,
        parent_wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        parent_style: ResolvedCssStyle,
    ) -> list[Block]:
        """Parse nested block content."""
        blocks: list[Block] = []

        for child in parent:
            if not isinstance(child.tag, str):
                continue

            wrapper = self._find_wrapper(
                parent_wrapper,
                child,
            )

            block = self._parse_block(
                child,
                wrapper,
                resolver,
                section_type,
                parent_style,
            )

            if block is not None:
                blocks.append(block)

        return blocks

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
            if _local_name(child.tag) != "li":
                continue

            child_wrapper = self._find_wrapper(
                wrapper,
                child,
            )

            item_style = resolver.resolve(
                child_wrapper,
                style,
            )

            item_blocks = self._parse_nested_blocks(
                child,
                child_wrapper,
                resolver,
                section_type,
                item_style,
            )

            if not item_blocks:
                inline_content = self._parse_inline_content(
                    child,
                    child_wrapper,
                    resolver,
                    item_style,
                )

                if inline_content:
                    item_blocks = [
                        Paragraph(content=inline_content)
                    ]

            items.append(
                ListItem(
                    content=item_blocks,
                )
            )

        return List(
            list_type=list_type,
            items=items,
        )

    def _parse_table(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        section_type: SectionType,
        style: ResolvedCssStyle,
    ) -> Table:
        """Parse an XHTML table."""
        rows: list[TableRow] = []

        for row in element.iter():
            if _local_name(row.tag) != "tr":
                continue

            row_wrapper = self._find_wrapper(wrapper, row)
            row_style = resolver.resolve(row_wrapper, style)

            cells: list[TableCell] = []

            for cell in row:
                cell_tag = _local_name(cell.tag)

                if cell_tag not in {"th", "td"}:
                    continue

                cell_wrapper = self._find_wrapper(
                    row_wrapper,
                    cell,
                )

                cell_style = resolver.resolve(
                    cell_wrapper,
                    row_style,
                )

                cell_blocks = self._parse_nested_blocks(
                    cell,
                    cell_wrapper,
                    resolver,
                    section_type,
                    cell_style,
                )

                if not cell_blocks:
                    inline_content = self._parse_inline_content(
                        cell,
                        cell_wrapper,
                        resolver,
                        cell_style,
                    )

                    if inline_content:
                        cell_blocks = [
                            Paragraph(content=inline_content)
                        ]

                cells.append(
                    TableCell(
                        content=cell_blocks,
                        is_header=cell_tag == "th",
                    )
                )

            rows.append(
                TableRow(
                    cells=cells,
                )
            )

        return Table(rows=rows)

    def _parse_inline_content(
        self,
        parent: etree._Element,
        parent_wrapper,
        resolver: CssCascadeResolver,
        parent_style: ResolvedCssStyle,
    ) -> list[Inline]:
        """Parse inline content while preserving source order."""
        inline_content: list[Inline] = []

        if parent.text:
            inline_content.append(
                Text(parent.text)
            )

        for child in parent:
            if not isinstance(child.tag, str):
                continue

            wrapper = self._find_wrapper(
                parent_wrapper,
                child,
            )

            child_style = resolver.resolve(
                wrapper,
                parent_style,
            )

            inline_content.append(
                self._parse_inline_element(
                    child,
                    wrapper,
                    resolver,
                    child_style,
                )
            )

            if child.tail:
                inline_content.append(
                    Text(child.tail)
                )

        return inline_content

    def _parse_inline_element(
        self,
        element: etree._Element,
        wrapper,
        resolver: CssCascadeResolver,
        style: ResolvedCssStyle,
    ) -> Inline:
        """Parse one inline XHTML element."""
        tag_name = _local_name(element.tag)

        content = self._parse_inline_content(
            element,
            wrapper,
            resolver,
            style,
        )

        classes = _class_names(element)

        if tag_name in {"i", "em"}:
            return Italic(content=content)

        if tag_name in {"b", "strong"}:
            return Bold(content=content)

        if _has_class_marker(classes, SMALL_CAPS_CLASS_MARKERS):
            return SmallCaps(content=content)

        if _has_class_marker(classes, HANDWRITING_CLASS_MARKERS):
            variant = self._determine_handwriting_variant(classes)

            return Handwriting(
                variant=variant,
                content=content,
            )

        if _has_class_marker(classes, SMS_CLASS_MARKERS):
            return SMS(content=content)

        if _has_class_marker(classes, DROP_CAP_CLASS_MARKERS):
            return DropCap(content=content)

        if _is_text_span(element):
            return Text(
                "".join(_inline_text(element))
            )

        return Text(
            "".join(_inline_text(element))
        )

    def _determine_handwriting_variant(
        self,
        classes: set[str],
    ) -> HandwritingVariant:
        """Determine handwriting variant from configured class mappings."""
        for class_name in classes:
            try:
                return self.configuration.handwriting.get_variant(
                    class_name
                )
            except KeyError:
                continue

        return self.configuration.handwriting.default_variant

    @staticmethod
    def _determine_paragraph_style(
        style: ResolvedCssStyle,
        section_type: SectionType,
    ) -> ParagraphStyle:
        """Determine the semantic paragraph style."""
        if section_type is SectionType.FRONT_MATTER:
            return ParagraphStyle.FRONT_MATTER

        text_indent = style.get("text-indent")

        if text_indent is not None and text_indent not in {"0", "0em", "0pt"}:
            return ParagraphStyle.FIRST_INDENT

        margin_top = style.get("margin-top")
        margin_bottom = style.get("margin-bottom")

        if (
            margin_top is not None
            and margin_bottom is not None
            and margin_top not in {"0", "0em", "0pt"}
            and margin_bottom not in {"0", "0em", "0pt"}
        ):
            return ParagraphStyle.SPACING_BEFORE_AND_AFTER

        if margin_bottom is not None and margin_bottom not in {
            "0",
            "0em",
            "0pt",
        }:
            return ParagraphStyle.SPACING_AFTER

        return ParagraphStyle.NORMAL

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

    @staticmethod
    def _is_section_break(
        element: etree._Element,
        style: ResolvedCssStyle,
    ) -> bool:
        """Determine whether an element represents a section break."""
        return (
            style.get("page-break-before") in {
                "always",
                "page",
            }
        )


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
    """Return whether an element is an ordinary inline span."""
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


def _inline_text(element: etree._Element) -> list[str]:
    """Collect all text contained by an inline element."""
    return list(element.itertext())


def _combine_blocks(blocks: list[Block]) -> Block | None:
    """Return a block when a wrapper contains exactly one semantic block."""
    if len(blocks) == 1:
        return blocks[0]

    return None
