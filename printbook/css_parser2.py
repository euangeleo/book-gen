"""CSS cascade resolution for XHTML documents."""

from __future__ import annotations

from dataclasses import dataclass

import cssselect2
import tinycss2


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
    """One supported CSS declaration."""

    property_name: str
    value: str
    important: bool = False


@dataclass(frozen=True)
class CssRule:
    """One CSS rule."""

    declarations: tuple[CssDeclaration, ...]


@dataclass(frozen=True)
class ResolvedCssStyle:
    """Effective CSS properties for one XHTML element."""

    properties: dict[str, str]

    def get(self, property_name: str) -> str | None:
        """Return one resolved CSS property."""
        return self.properties.get(property_name)


class CssStylesheet:
    """Parsed stylesheet used for selector matching."""

    def __init__(
        self,
        css_text: str,
        source_name: str,
    ) -> None:
        self.source_name = source_name
        self._matcher = cssselect2.Matcher()
        self._parse(css_text)

    def _parse(self, css_text: str) -> None:
        """Parse CSS rules and populate the selector matcher."""
        rules = tinycss2.parse_stylesheet(
            css_text,
            skip_whitespace=True,
            skip_comments=True,
        )

        for rule in rules:
            if rule.type != "qualified-rule":
                continue

            selector_text = tinycss2.serialize(
                rule.prelude
            ).strip()

            declarations = _parse_declarations(rule.content)

            if not selector_text or not declarations:
                continue

            selectors = cssselect2.compile_selector_list(
                selector_text
            )

            for selector in selectors:
                self._matcher.add_selector(
                    selector,
                    CssRule(tuple(declarations)),
                )

    def matching_declarations(
        self,
        element: cssselect2.ElementWrapper,
    ) -> list[CssDeclaration]:
        """Return declarations matching an XHTML element."""
        declarations: list[CssDeclaration] = []

        for _, _, _, rule in self._matcher.match(element):
            declarations.extend(rule.declarations)

        return declarations


class CssCascadeResolver:
    """Resolve CSS styles for an XHTML document."""

    def __init__(
        self,
        stylesheet: CssStylesheet,
    ) -> None:
        self.stylesheet = stylesheet

    def resolve_document(
        self,
        root: cssselect2.ElementWrapper,
    ) -> dict[object, ResolvedCssStyle]:
        """Resolve effective styles for every element in a document."""
        resolved_styles: dict[object, ResolvedCssStyle] = {}

        for element in root.iter_subtree():
            parent_style = self._parent_style(
                element,
                resolved_styles,
            )

            resolved_styles[element.etree_element] = (
                self._resolve_element(
                    element,
                    parent_style,
                )
            )

        return resolved_styles

    def _resolve_element(
        self,
        element: cssselect2.ElementWrapper,
        parent_style: ResolvedCssStyle | None,
    ) -> ResolvedCssStyle:
        """Resolve one element against its parent style."""
        properties: dict[str, str] = {}

        if parent_style is not None:
            for property_name in INHERITED_PROPERTIES:
                inherited_value = parent_style.get(property_name)

                if inherited_value is not None:
                    properties[property_name] = inherited_value

        for declaration in self.stylesheet.matching_declarations(
            element
        ):
            properties[declaration.property_name] = declaration.value

        inline_style = element.etree_element.get("style")

        if inline_style:
            for declaration in _parse_declarations(inline_style):
                properties[declaration.property_name] = (
                    declaration.value
                )

        _expand_four_sided_property(properties, "margin")
        _expand_four_sided_property(properties, "padding")

        return ResolvedCssStyle(properties)

    @staticmethod
    def _parent_style(
        element: cssselect2.ElementWrapper,
        styles: dict[object, ResolvedCssStyle],
    ) -> ResolvedCssStyle | None:
        """Return the already-resolved style of an element's parent."""
        parent = element.parent

        if parent is None:
            return None

        return styles.get(parent.etree_element)


def _parse_declarations(
    tokens: list[object] | str,
) -> list[CssDeclaration]:
    """Parse supported declarations."""
    declarations = tinycss2.parse_declaration_list(
        tokens,
        skip_whitespace=True,
        skip_comments=True,
    )

    parsed: list[CssDeclaration] = []

    for declaration in declarations:
        if declaration.type != "declaration":
            continue

        value = tinycss2.serialize(
            declaration.value
        ).strip()

        if not value:
            continue

        parsed.append(
            CssDeclaration(
                property_name=declaration.lower_name,
                value=value,
                important=declaration.important,
            )
        )

    return parsed


def _expand_four_sided_property(
    properties: dict[str, str],
    property_name: str,
) -> None:
    """Expand margin or padding shorthand."""
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
