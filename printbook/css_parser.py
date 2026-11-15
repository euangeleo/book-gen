"""CSS parsing, selector matching, and cascade resolution.

This module knows about CSS syntax and CSS cascading, but does not know
anything about the semantic book model or LaTeX.
"""

from __future__ import annotations

from dataclasses import dataclass
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
        "border-width",
        "border-style",
        "border-color",
        "border-top-width",
        "border-top-style",
        "border-top-color",
        "border-right-width",
        "border-right-style",
        "border-right-color",
        "border-bottom-width",
        "border-bottom-style",
        "border-bottom-color",
        "border-left-width",
        "border-left-style",
        "border-left-color",
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


FOUR_SIDED_PROPERTIES = frozenset(
    {
        "margin",
        "padding",
        "border",
        "border-width",
        "border-style",
        "border-color",
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
    """A CSS rule together with its declarations and source order."""

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

            css_rule = CssRule(
                declarations=tuple(declarations),
                source_order=source_order,
            )

            for selector in selectors:
                self._matcher.add_selector(selector, css_rule)

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
    ) -> Iterator[tuple[tuple[int, int, int], CssRule]]:
        """Yield matching rules with their selector specificity.

        If multiple selectors from the same selector list match an element,
        the rule is yielded once, using the highest matching specificity.
        """
        matched: dict[int, tuple[tuple[int, int, int], CssRule]] = {}

        for specificity, _, _, rule in self._matcher.match(element):
            previous = matched.get(rule.source_order)

            if previous is None or specificity > previous[0]:
                matched[rule.source_order] = (specificity, rule)

        yield from sorted(
            matched.values(),
            key=lambda match: match[1].source_order,
        )


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

        # Each candidate is stored with its cascade priority.
        # Higher-priority candidates replace lower-priority candidates.
        winners: dict[
            str,
            tuple[tuple[object, ...], str],
        ] = {}

        for specificity, rule in self.stylesheet.matched_rules(element):
            for declaration_index, declaration in enumerate(rule.declarations):
                self._consider_declaration(
                    winners,
                    declaration,
                    important=declaration.important,
                    inline=False,
                    specificity=specificity,
                    source_order=rule.source_order,
                    declaration_order=declaration_index,
                )

        inline_style = element.etree_element.get("style")

        if inline_style:
            declarations = tinycss2.parse_declaration_list(
                inline_style,
                skip_whitespace=True,
                skip_comments=True,
            )

            for declaration_index, declaration in enumerate(declarations):
                if declaration.type != "declaration":
                    continue

                property_name = declaration.lower_name

                if property_name not in SUPPORTED_CSS_PROPERTIES:
                    continue

                value = tinycss2.serialize(declaration.value).strip()

                if not value:
                    continue

                self._consider_declaration(
                    winners,
                    CssDeclaration(
                        property_name=property_name,
                        value=value,
                        important=declaration.important,
                    ),
                    important=declaration.important,
                    inline=True,
                    specificity=(0, 0, 0),
                    source_order=0,
                    declaration_order=declaration_index,
                )

        properties.update(
            {
                property_name: candidate[1]
                for property_name, candidate in winners.items()
            }
        )

        return ResolvedCssStyle(properties=properties)

    @staticmethod
    def _consider_declaration(
        winners: dict[str, tuple[tuple[object, ...], str]],
        declaration: CssDeclaration,
        *,
        important: bool,
        inline: bool,
        specificity: tuple[int, int, int],
        source_order: int,
        declaration_order: int,
    ) -> None:
        """Consider a declaration and retain it if it has higher priority."""
        priority = (
            important,
            inline,
            specificity,
            source_order,
            declaration_order,
        )

        for expanded in _expand_declaration(declaration):
            previous = winners.get(expanded.property_name)

            if previous is None or priority > previous[0]:
                winners[expanded.property_name] = (
                    priority,
                    expanded.value,
                )


def _expand_declaration(
    declaration: CssDeclaration,
) -> tuple[CssDeclaration, ...]:
    """Expand supported shorthand declarations into longhand declarations."""

    property_name = declaration.property_name
    value = declaration.value

    # A border shorthand consists of width, style, and color components.
    # It is not a whitespace-separated list of four side values.
    if property_name == "border" or property_name in {
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
    }:
        components = _parse_border_components(value)

        if components is None:
            return ()

        width, style, color = components

        if property_name == "border":
            sides = ("top", "right", "bottom", "left")
        else:
            sides = (property_name.removeprefix("border-"),)

        expanded = []

        for side in sides:
            prefix = f"border-{side}"

            expanded.extend(
                (
                    CssDeclaration(
                        property_name=f"{prefix}-width",
                        value=width,
                        important=declaration.important,
                    ),
                    CssDeclaration(
                        property_name=f"{prefix}-style",
                        value=style,
                        important=declaration.important,
                    ),
                    CssDeclaration(
                        property_name=f"{prefix}-color",
                        value=color,
                        important=declaration.important,
                    ),
                )
            )

        return tuple(expanded)

    # The remaining shorthand properties distribute one to four values
    # across the four sides.
    if property_name not in FOUR_SIDED_PROPERTIES:
        return (declaration,)

    values = _split_css_values(value)

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
        # An invalid shorthand must not affect the longhand properties.
        return ()

    if property_name in {
        "border-width",
        "border-style",
        "border-color",
    }:
        component = property_name.removeprefix("border-")

        return tuple(
            CssDeclaration(
                property_name=f"border-{side}-{component}",
                value=side_value,
                important=declaration.important,
            )
            for side, side_value in (
                ("top", top),
                ("right", right),
                ("bottom", bottom),
                ("left", left),
            )
        )

    return tuple(
        CssDeclaration(
            property_name=f"{property_name}-{side}",
            value=side_value,
            important=declaration.important,
        )
        for side, side_value in (
            ("top", top),
            ("right", right),
            ("bottom", bottom),
            ("left", left),
        )
    )


def _parse_border_components(
    value: str,
) -> tuple[str, str, str] | None:
    """Parse the width, style, and color components of a border shorthand.

    Only the border styles supported by the rendering layer (none and solid)
    are accepted. A missing component receives its CSS initial value.
    """

    width: str | None = None
    style: str | None = None
    color: str | None = None

    supported_styles = {"none", "solid"}

    # Recognize other CSS border styles so they aren't mistaken for colors.
    unsupported_styles = {
        "hidden",
        "dotted",
        "dashed",
        "double",
        "groove",
        "ridge",
        "inset",
        "outset",
    }

    for token in tinycss2.parse_component_value_list(value):
        if token.type in {"whitespace", "comment"}:
            continue

        token_value = tinycss2.serialize([token]).strip()

        if token.type == "dimension":
            if width is not None:
                return None
            width = token_value

        elif token.type == "number":
            # CSS permits a unitless zero border width, but not other
            # unitless numeric widths.
            if width is not None or token.value != 0:
                return None
            width = token_value

        elif token.type == "ident" and token_value.lower() in {
            "thin",
            "medium",
            "thick",
        }:
            if width is not None:
                return None
            width = token_value.lower()

        elif token.type == "ident":
            identifier = token_value.lower()

            if identifier in supported_styles:
                if style is not None:
                    return None
                style = identifier

            elif identifier in unsupported_styles:
                return None

            else:
                # A named color, such as red, black, or currentColor.
                if color is not None:
                    return None
                color = token_value

        elif token.type in {"hash", "function"}:
            # Hexadecimal colors and functional colors such as rgb().
            if color is not None:
                return None
            color = token_value

        else:
            # This component is outside the supported border syntax.
            return None

    # CSS initial values for omitted border components.
    return (
        width if width is not None else "medium",
        style if style is not None else "none",
        color if color is not None else "currentColor",
    )


def _split_css_values(value: str) -> list[str]:
    """Split a shorthand into whitespace-separated CSS component values."""
    tokens = tinycss2.parse_component_value_list(value)

    return [
        tinycss2.serialize([token]).strip()
        for token in tokens
        if token.type not in {"whitespace", "comment"}
    ]


def create_css_root(
    root: etree._Element,
) -> cssselect2.ElementWrapper:
    """Create a cssselect2 wrapper for an XHTML document root."""
    return cssselect2.ElementWrapper.from_xml_root(root)