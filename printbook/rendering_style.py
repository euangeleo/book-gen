"""Convert resolved CSS styles into semantic rendering styles.

This module forms the boundary between CSS parsing and the semantic model.

The CSS parser is responsible for:
    * parsing CSS;
    * matching selectors;
    * resolving the cascade;
    * resolving inheritance;
    * producing ResolvedCssStyle objects.

This module is responsible for:
    * interpreting supported CSS property values;
    * converting CSS measurements into Length objects;
    * converting CSS colors into Color objects;
    * converting CSS border and padding values;
    * producing RenderingStyle objects.

No XHTML parsing, CSS selector matching, or LaTeX rendering belongs here.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Mapping

from model import (
    Border,
    BorderSide,
    BorderStyle,
    Color,
    FontStyle,
    FontWeight,
    Length,
    LengthUnit,
    Padding,
    RenderingStyle,
    TextAlignment,
    TextDecoration,
    TextTransform,
)


class RenderingStyleConversionError(ValueError):
    """Raised when a CSS value cannot be converted to the semantic model."""

_LENGTH_PATTERN = re.compile(
    r"^\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
    r"(?P<unit>em|pt|mm|%|px)"
    r"\s*$"
)


_COLOR_PATTERN = re.compile(
    r"^#[0-9a-fA-F]{3,8}$"
)


class ResolvedCssStyle:
    """CSS properties after selector matching, cascade, and inheritance.

    The CSS parser should construct this object.

    Property names are CSS property names such as ``font-family`` and
    ``text-align``. Values remain CSS strings at this stage.

    Keeping CSS values as strings until this boundary is intentional:
    ``Length`` and the other semantic-model types should not be exposed to
    CSS parsing or selector-matching code.
    """

    def __init__(
        self,
        properties: Mapping[str, str] | None = None,
    ) -> None:
        self.properties = dict(properties or {})

    def get(self, property_name: str) -> str | None:
        """Return a resolved CSS property value."""
        return self.properties.get(property_name)


class RenderingStyleConverter:
    """Convert resolved CSS styles into RenderingStyle objects."""

    def convert(
        self,
        css_style: ResolvedCssStyle | None,
    ) -> RenderingStyle | None:
        """Convert one resolved CSS style.

        ``None`` is returned when there is no supported rendering information
        in the supplied style.
        """
        if css_style is None:
            return None

        style = RenderingStyle(
            font_family=self._font_family(css_style),
            font_size=self._length(css_style, "font-size"),
            font_weight=self._font_weight(css_style),
            font_style=self._font_style(css_style),
            line_height=self._line_height(css_style),
            letter_spacing=self._length(css_style, "letter-spacing"),
            text_alignment=self._text_alignment(css_style),
            text_indent=self._length(css_style, "text-indent"),
            margin_top=self._length(css_style, "margin-top"),
            margin_right=self._length(css_style, "margin-right"),
            margin_bottom=self._length(css_style, "margin-bottom"),
            margin_left=self._length(css_style, "margin-left"),
            text_transform=self._text_transform(css_style),
            text_decoration=self._text_decoration(css_style),
            foreground_color=self._color(
                css_style,
                "color",
            ),
            background_color=self._color(
                css_style,
                "background-color",
            ),
            padding=self._padding(css_style),
            border=self._border(css_style),
            page_break_before=self._page_break_before(css_style),
        )

        if style == RenderingStyle():
            return None

        return style

    @staticmethod
    def _font_family(
        css_style: ResolvedCssStyle,
    ) -> str | None:
        """Return the CSS font-family value unchanged.

        Font-family resolution against configured font files belongs to the
        font/rendering configuration layer, not to this conversion step.
        """
        value = css_style.get("font-family")

        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        return _first_font_family(value)

    @staticmethod
    def _font_weight(
        css_style: ResolvedCssStyle,
    ) -> FontWeight | None:
        """Convert a CSS font-weight value."""
        value = css_style.get("font-weight")

        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized in {"normal", "400"}:
            return FontWeight.NORMAL

        if normalized in {"bold", "700"}:
            return FontWeight.BOLD

        raise RenderingStyleConversionError(
            f"Unsupported font-weight value: {value!r}"
        )

    @staticmethod
    def _font_style(
        css_style: ResolvedCssStyle,
    ) -> FontStyle | None:
        """Convert a CSS font-style value."""
        value = css_style.get("font-style")

        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized == "normal":
            return FontStyle.NORMAL

        if normalized in {"italic", "oblique"}:
            return FontStyle.ITALIC

        raise RenderingStyleConversionError(
            f"Unsupported font-style value: {value!r}"
        )

    @staticmethod
    def _line_height(
        css_style: ResolvedCssStyle,
    ) -> Length | None:
        """Convert a CSS line-height value.

        The semantic model currently represents line-height as a Length.
        Unitless CSS line-height therefore cannot be represented without
        knowing the eventual font size, so it is rejected here.
        """
        value = css_style.get("line-height")

        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized in {"normal", "inherit", "initial", "unset"}:
            return None

        return _parse_length(
            value,
            property_name="line-height",
        )

    @staticmethod
    def _text_alignment(
        css_style: ResolvedCssStyle,
    ) -> TextAlignment | None:
        """Convert CSS text-align."""
        value = css_style.get("text-align")

        if value is None:
            return None

        normalized = value.strip().lower()

        try:
            return TextAlignment(normalized)
        except ValueError as error:
            raise RenderingStyleConversionError(
                f"Unsupported text-align value: {value!r}"
            ) from error

    @staticmethod
    def _text_transform(
        css_style: ResolvedCssStyle,
    ) -> TextTransform | None:
        """Convert CSS text-transform."""
        value = css_style.get("text-transform")

        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized == "none":
            return TextTransform.NONE

        if normalized == "uppercase":
            return TextTransform.UPPERCASE

        raise RenderingStyleConversionError(
            f"Unsupported text-transform value: {value!r}"
        )

    @staticmethod
    def _text_decoration(
        css_style: ResolvedCssStyle,
    ) -> TextDecoration | None:
        """Convert CSS text-decoration."""
        value = css_style.get("text-decoration")

        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized in {"none", "initial", "inherit", "unset"}:
            return TextDecoration.NONE

        # CSS text-decoration can contain multiple tokens, so check for
        # underline rather than requiring the entire value to be "underline".
        if "underline" in normalized.split():
            return TextDecoration.UNDERLINE

        raise RenderingStyleConversionError(
            f"Unsupported text-decoration value: {value!r}"
        )

    @staticmethod
    def _page_break_before(
        css_style: ResolvedCssStyle,
    ) -> bool:
        """Convert CSS page-break-before to the model's boolean value."""
        value = css_style.get("page-break-before")

        if value is None:
            return False

        normalized = value.strip().lower()

        if normalized in {"auto", "inherit", "initial", "unset"}:
            return False

        if normalized == "always":
            return True

        raise RenderingStyleConversionError(
            f"Unsupported page-break-before value: {value!r}"
        )

    @staticmethod
    def _length(
        css_style: ResolvedCssStyle,
        property_name: str,
    ) -> Length | None:
        """Convert one CSS length property."""
        value = css_style.get(property_name)

        if value is None:
            return None

        normalized = value.strip().lower()

        if normalized in {"auto", "inherit", "initial", "unset"}:
            return None

        return _parse_length(
            value,
            property_name=property_name,
        )

    def _color(
        self,
        css_style: ResolvedCssStyle,
        property_name: str,
    ) -> Color | None:
        """Convert one CSS color property."""
        value = css_style.get(property_name)

        if value is None:
            return None

        normalized = value.strip()

        if normalized.lower() in {
            "transparent",
            "inherit",
            "initial",
            "unset",
        }:
            return None

        return Color(
            value=_normalize_color(normalized),
        )

    def _padding(
        self,
        css_style: ResolvedCssStyle,
    ) -> Padding | None:
        """Convert CSS padding properties."""
        values = {
            "top": self._length(css_style, "padding-top"),
            "right": self._length(css_style, "padding-right"),
            "bottom": self._length(css_style, "padding-bottom"),
            "left": self._length(css_style, "padding-left"),
        }

        if all(value is None for value in values.values()):
            return None

        return Padding(**values)

    def _border(
        self,
        css_style: ResolvedCssStyle,
    ) -> Border | None:
        """Convert CSS border properties."""
        sides = {
            "top": self._border_side(css_style, "top"),
            "right": self._border_side(css_style, "right"),
            "bottom": self._border_side(css_style, "bottom"),
            "left": self._border_side(css_style, "left"),
        }

        if all(side is None for side in sides.values()):
            return None

        return Border(**sides)

    def _border_side(
        self,
        css_style: ResolvedCssStyle,
        side: str,
    ) -> BorderSide | None:
        """Convert one CSS border side."""
        width = self._length(
            css_style,
            f"border-{side}-width",
        )

        color = self._color(
            css_style,
            f"border-{side}-color",
        )

        style_value = css_style.get(
            f"border-{side}-style"
        )

        if (
            width is None
            and color is None
            and style_value is None
        ):
            return None

        border_style = _parse_border_style(style_value)

        return BorderSide(
            width=width,
            color=color,
            style=border_style,
        )


def _parse_length(
    value: str,
    *,
    property_name: str,
) -> Length:
    """Parse a supported CSS length value."""
    match = _LENGTH_PATTERN.fullmatch(value)

    if match is None:
        raise RenderingStyleConversionError(
            f"Unsupported {property_name} value: {value!r}. "
            "Supported units are em, pt, mm, %, and px."
        )

    try:
        numeric_value = Decimal(match.group("value"))
    except InvalidOperation as error:
        raise RenderingStyleConversionError(
            f"Invalid numeric value in {property_name}: {value!r}"
        ) from error

    unit = _LENGTH_UNITS[match.group("unit")]

    return Length(
        value=numeric_value,
        unit=LengthUnit(match.group("unit")),
    )


def _first_font_family(value: str) -> str:
    """Return the first font-family from a CSS font-family list.

    The complete fallback list remains a CSS concern. The semantic model
    currently represents one selected family, so the first family is retained.
    """
    first_family = value.split(",", maxsplit=1)[0].strip()

    if (
        len(first_family) >= 2
        and first_family[0] == first_family[-1]
        and first_family[0] in {"'", '"'}
    ):
        first_family = first_family[1:-1]

    return first_family.strip()


def _normalize_color(value: str) -> str:
    """Normalize a supported CSS color representation.

    Named colors and functional colors are preserved as CSS-independent
    strings for now. Hexadecimal colors are normalized to lowercase.
    """
    if _COLOR_PATTERN.fullmatch(value):
        return value.lower()

    return value


def _parse_border_style(
    value: str | None,
) -> BorderStyle:
    """Convert a CSS border-style value."""
    if value is None:
        return BorderStyle.NONE

    normalized = value.strip().lower()

    if normalized == "none":
        return BorderStyle.NONE

    if normalized == "solid":
        return BorderStyle.SOLID

    raise RenderingStyleConversionError(
        f"Unsupported border-style value: {value!r}"
    )
