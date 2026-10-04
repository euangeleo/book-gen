"""CSS parsing, selector matching, and cascade resolution.

This module knows about CSS syntax and CSS cascading, but does not know
anything about the semantic book model or LaTeX.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cssselect2
import tinycss2
from lxml import etree


SUPPORTED_CSS_PROPERTIES = frozenset(
    {
        "font-family",
        "font-size",
        "font-weight",
        "font-style",
        "line-height",
        "letter-spacing",
        "text-align",
        "text-indent",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "text-transform",
        "text-decoration",
        "color",
        "background-color",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "border",
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
        "page-break-before",
    }
)


INHERITED_PROPERTIES = frozenset(
    {
        "font-family",
        "font-size",
        "font-weight",
        "font-style",
        "line-height",
        "letter-spacing",
        "color",
        "text-align",
    }
)


@dataclass(frozen=True)
class CssDeclaration:
    """One CSS declaration."""

    property_name: str
    value: str
    important: bool = False


@dataclass(frozen=True)
class CssRule:
    """A CSS rule together with its selector metadata."""

    selector: object
    declarations: tuple[CssDeclaration, ...]
    source_order: int


@dataclass(frozen=True)
class ResolvedCssStyle:
    """The effective CSS properties for one XHTML element.

    Values remain CSS-level strings at this stage. Conversion into the
    semantic model's RenderingStyle is intentionally deferred.
    """

    properties: dict[str, str]

    def get(self, property_name: str) -> str | None:
        """Return one resolved CSS property."""
        return self.properties.get(property_name)

    def __contains__(self, property_name: str) -> bool:
        """Return whether a property is present."""
        return property_name in self.properties


class CssStylesheet:
    """Parsed CSS stylesheet with selector-matching support."""

    def __init__(self, css_text: str, source_name: str = "<stylesheet>") -> None:
        self.source_name = source_name
        self._matcher = cssselect2.Matcher()
        self._parse(css_text)

    def _parse(self, css_text: str) -> None:
        """Parse stylesheet rules and add them to the selector matcher."""
        rules = tinycss2.parse_stylesheet(
            css_text,
            skip_whitespace=True,
            skip_comments=True,
        )

        source_order = 0

        for rule in rules:
            if rule.type != "qualified-rule":
                continue

            selector_text = tinycss2.serialize(rule.prelude).strip()

            if not selector_text:
                continue

            declarations = self._parse_declarations(rule.content)

            if not declarations:
                continue

            try:
                selectors = cssselect2.compile_selector_list(selector_text)
            except cssselect2.SelectorError as error:
                raise ValueError(
                    f"Invalid CSS selector in {self.source_name}: "
                    f"{selector_text!r}"
                ) from error

            for selector in selectors:
                self._matcher.add_selector(
                    selector,
                    CssRule(
                        selector=selector,
                        declarations=tuple(declarations),
                        source_order=source_order,
                    ),
                )

                source_order += 1

    @staticmethod
    def _parse_declarations(
        tokens: list[object],
    ) -> list[CssDeclaration]:
        """Parse declarations from a CSS rule body."""
        declarations = tinycss2.parse_declaration_list(
            tokens,
            skip_whitespace=True,
            skip_comments=True,
        )

        parsed_declarations: list[CssDeclaration] = []

        for declaration in declarations:
            if declaration.type != "declaration":
                continue

            property_name = declaration.lower_name

            if property_name not in SUPPORTED_CSS_PROPERTIES:
                continue

            value = tinycss2.serialize(declaration.value).strip()

            if not value:
                continue

            parsed_declarations.append(
                CssDeclaration(
                    property_name=property_name,
                    value=value,
                    important=declaration.important,
                )
            )

        return parsed_declarations

    def matched_rules(
        self,
        element: cssselect2.ElementWrapper,
    ) -> Iterator[CssRule]:
        """Yield CSS rules matching an XHTML element."""
        for _, _, _, rule in self._matcher.match(element):
            yield rule


class CssCascadeResolver:
    """Resolve effective CSS properties for XHTML elements."""

    def __init__(self, stylesheet: CssStylesheet) -> None:
        self.stylesheet = stylesheet

    def resolve(
        self,
        element: cssselect2.ElementWrapper,
        inherited_style: ResolvedCssStyle | None = None,
    ) -> ResolvedCssStyle:
        """Resolve the effective style for one XHTML element."""
        properties: dict[str, str] = {}

        if inherited_style is not None:
            for property_name in INHERITED_PROPERTIES:
                inherited_value = inherited_style.get(property_name)

                if inherited_value is not None:
                    properties[property_name] = inherited_value

        for rule in self.stylesheet.matched_rules(element):
            for declaration in rule.declarations:
                properties[declaration.property_name] = declaration.value

        inline_style = element.etree_element.get("style")

        if inline_style:
            self._apply_inline_style(properties, inline_style)

        properties = self._expand_shorthand_properties(properties)

        return ResolvedCssStyle(properties=properties)

    @staticmethod
    def _apply_inline_style(
        properties: dict[str, str],
        inline_style: str,
    ) -> None:
        """Apply supported declarations from an inline style attribute."""
        declarations = tinycss2.parse_declaration_list(
            inline_style,
            skip_whitespace=True,
            skip_comments=True,
        )

        for declaration in declarations:
            if declaration.type != "declaration":
                continue

            property_name = declaration.lower_name

            if property_name not in SUPPORTED_CSS_PROPERTIES:
                continue

            value = tinycss2.serialize(declaration.value).strip()

            if value:
                properties[property_name] = value

    @staticmethod
    def _expand_shorthand_properties(
        properties: dict[str, str],
    ) -> dict[str, str]:
        """Expand supported CSS shorthand properties."""
        expanded = dict(properties)

        _expand_four_sided_property(
            expanded,
            "margin",
        )

        _expand_four_sided_property(
            expanded,
            "padding",
        )

        return expanded


def _expand_four_sided_property(
    properties: dict[str, str],
    property_name: str,
) -> None:
    """Expand a CSS four-sided shorthand into individual properties."""
    shorthand = properties.get(property_name)

    if shorthand is None:
        return

    values = shorthand.split()

    if len(values) == 1:
        top, right, bottom, left = values * 4
    elif len(values) == 2:
        top, right = values
        bottom, left = top, right
    elif len(values) == 3:
        top, right, bottom = values
        left = right
    elif len(values) == 4:
        top, right, bottom, left = values
    else:
        return

    properties[f"{property_name}-top"] = top
    properties[f"{property_name}-right"] = right
    properties[f"{property_name}-bottom"] = bottom
    properties[f"{property_name}-left"] = left

    del properties[property_name]


def create_css_root(
    root: etree._Element,
) -> cssselect2.ElementWrapper:
    """Create a cssselect2 wrapper for an XHTML document root."""
    return cssselect2.ElementWrapper.from_xml_root(root)
