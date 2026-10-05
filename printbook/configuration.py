"""Configuration for print-book editions.

This module parses and validates the YAML configuration for a print book.

It contains no XHTML, CSS, semantic-model, or LaTeX rendering logic.
KDP-specific requirements are handled by the kdp module.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from model import HandwritingVariant, SectionType


CONFIGURATION_FILENAME = "book.yaml"

SUPPORTED_UNITS = frozenset({"in", "mm", "cm", "pt"})

MEASUREMENT_PATTERN = re.compile(
    r"^\s*(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>in|mm|cm|pt)\s*$"
)


@dataclass(frozen=True)
class Measurement:
    """A physical measurement with an explicit unit."""

    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        """Validate the measurement."""
        if self.value <= 0:
            raise ValueError("Measurement must be greater than zero.")

        if self.unit not in SUPPORTED_UNITS:
            raise ValueError(f"Unsupported measurement unit: {self.unit}")

    @classmethod
    def from_string(cls, value: str) -> Measurement:
        """Create a measurement from a string such as '6in' or '25.4mm'."""
        if not isinstance(value, str):
            raise ValueError(
                f"Measurement must be a string, not {type(value).__name__}."
            )

        match = MEASUREMENT_PATTERN.fullmatch(value)

        if match is None:
            raise ValueError(
                f"Invalid measurement: {value!r}. "
                "Expected a positive number followed by in, mm, cm, or pt."
            )

        return cls(
            value=Decimal(match.group("value")),
            unit=match.group("unit"),
        )


@dataclass(frozen=True)
class BookMetadata:
    """Metadata identifying the print book."""

    title: str
    author: str


@dataclass(frozen=True)
class PageConfiguration:
    """Physical dimensions of the printed page."""

    width: Measurement
    height: Measurement


@dataclass(frozen=True)
class MarginConfiguration:
    """Physical margins of the printed page."""

    top: Measurement
    bottom: Measurement
    inner: Measurement
    outer: Measurement


@dataclass(frozen=True)
class HandwritingConfiguration:
    """Configuration for handwriting-style text."""

    default_variant: HandwritingVariant
    print: str
    script: str


@dataclass(frozen=True)
class FontConfiguration:
    """Fonts available to the print edition.

    Font family names are kept separate from their filesystem paths.
    The renderer works with family names, while the paths allow fontspec
    to locate the actual font files.
    """

    body: str
    sms: str
    handwriting: HandwritingConfiguration
    paths: dict[str, Path]


@dataclass(frozen=True)
class SectionConfiguration:
    """Configuration describing one sequential book section."""

    section_type: SectionType
    file: Path
    number: int | None = None


@dataclass(frozen=True)
class PrintBookConfiguration:
    """Complete configuration for one print-book edition."""

    directory: Path
    book: BookMetadata
    page: PageConfiguration
    margins: MarginConfiguration
    fonts: FontConfiguration
    sections: tuple[SectionConfiguration, ...]


def load_configuration(
    configuration_path: Path,
) -> PrintBookConfiguration:
    """Load and validate a print-book YAML configuration."""
    configuration_path = configuration_path.resolve()

    if not configuration_path.is_file():
        raise FileNotFoundError(
            f"Configuration file does not exist: {configuration_path}"
        )

    with configuration_path.open("r", encoding="utf-8") as configuration_file:
        raw_configuration = yaml.safe_load(configuration_file)

    if not isinstance(raw_configuration, dict):
        raise ValueError("The YAML configuration must contain a mapping.")

    return _create_configuration(
        raw_configuration,
        configuration_path.parent,
    )


def _create_configuration(
    raw_configuration: dict,
    directory: Path,
) -> PrintBookConfiguration:
    """Create a typed configuration from parsed YAML data."""
    return PrintBookConfiguration(
        directory=directory,
        book=_parse_book_metadata(raw_configuration),
        page=_parse_page_configuration(raw_configuration),
        margins=_parse_margin_configuration(raw_configuration),
        fonts=_parse_font_configuration(
            raw_configuration,
            directory,
        ),
        sections=_parse_section_configurations(
            raw_configuration,
            directory,
        ),
    )


def _parse_book_metadata(configuration: dict) -> BookMetadata:
    """Parse required book metadata."""
    book = _require_mapping(configuration, "book")

    return BookMetadata(
        title=_require_string(book, "title"),
        author=_require_string(book, "author"),
    )


def _parse_page_configuration(
    configuration: dict,
) -> PageConfiguration:
    """Parse page dimensions."""
    page = _require_mapping(configuration, "page")

    return PageConfiguration(
        width=_parse_measurement(page, "width"),
        height=_parse_measurement(page, "height"),
    )


def _parse_margin_configuration(
    configuration: dict,
) -> MarginConfiguration:
    """Parse physical page margins."""
    margins = _require_mapping(configuration, "margins")

    return MarginConfiguration(
        top=_parse_measurement(margins, "top"),
        bottom=_parse_measurement(margins, "bottom"),
        inner=_parse_measurement(margins, "inner"),
        outer=_parse_measurement(margins, "outer"),
    )


def _parse_font_configuration(
    configuration: dict,
    directory: Path,
) -> FontConfiguration:
    """Parse and validate the configured fonts."""
    fonts = _require_mapping(configuration, "fonts")

    body = _require_string(fonts, "body")
    sms = _require_string(fonts, "sms")

    handwriting = _parse_handwriting_configuration(fonts)

    paths = _parse_font_paths(fonts, directory)

    required_families = {
        body,
        sms,
        handwriting.print,
        handwriting.script,
    }

    _validate_font_paths(
        required_families,
        paths,
    )

    return FontConfiguration(
        body=body,
        sms=sms,
        handwriting=handwriting,
        paths=paths,
    )


def _parse_handwriting_configuration(
    fonts: dict,
) -> HandwritingConfiguration:
    """Parse handwriting configuration."""
    handwriting = _require_mapping(
        fonts,
        "handwriting",
    )

    default_variant = _parse_handwriting_variant(
        handwriting.get("default_variant")
    )

    print_family = _require_string(
        handwriting,
        "print",
    )

    script_family = _require_string(
        handwriting,
        "script",
    )

    return HandwritingConfiguration(
        default_variant=default_variant,
        print=print_family,
        script=script_family,
    )


def _parse_font_paths(
    fonts: dict,
    directory: Path,
) -> dict[str, Path]:
    """Parse the mapping from font family names to font files."""
    raw_paths = _require_mapping(fonts, "paths")

    paths: dict[str, Path] = {}

    for family, value in raw_paths.items():
        if not isinstance(family, str) or not family.strip():
            raise ValueError(
                "Font family names in 'fonts.paths' "
                "must be non-empty strings."
            )

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Font path for {family!r} must be "
                "a non-empty string."
            )

        font_path = directory / value
        paths[family] = font_path

    return paths


def _validate_font_paths(
    required_families: set[str],
    paths: dict[str, Path],
) -> None:
    """Validate that required font families have configured paths."""
    for family in sorted(required_families):
        if family not in paths:
            raise ValueError(
                f"No font path is configured for font family "
                f"{family!r}."
            )

        font_path = paths[family]

        if not font_path.is_file():
            warnings.warn(
                f"Configured font does not exist: {font_path}",
                UserWarning,
                stacklevel=2,
            )


def _parse_handwriting_variant(
    value: object,
) -> HandwritingVariant:
    """Convert a YAML value to a semantic-model handwriting variant."""
    if not isinstance(value, str):
        raise ValueError(
            "Handwriting default_variant must be a string."
        )

    try:
        return HandwritingVariant(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid handwriting variant: {value!r}. "
            "Expected one of: "
            + ", ".join(
                variant.value
                for variant in HandwritingVariant
            )
            + "."
        ) from error


def _parse_section_configurations(
    configuration: dict,
    directory: Path,
) -> tuple[SectionConfiguration, ...]:
    """Parse and validate the sequential book sections."""
    raw_sections = configuration.get("sections")

    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError(
            "'sections' must be a non-empty list."
        )

    sections = tuple(
        _parse_section_configuration(
            section,
            directory,
        )
        for section in raw_sections
    )

    _validate_section_structure(sections)

    return sections


def _parse_section_configuration(
    section: object,
    directory: Path,
) -> SectionConfiguration:
    """Parse one section configuration."""
    if not isinstance(section, dict):
        raise ValueError(
            "Each section must be a mapping."
        )

    section_type = _parse_section_type(
        section.get("type")
    )

    source_file = _parse_source_file(
        section,
        directory,
    )

    number = section.get("number")

    if number is not None:
        if not isinstance(number, int) or number < 1:
            raise ValueError(
                "Section number must be a positive integer."
            )

    return SectionConfiguration(
        section_type=section_type,
        file=source_file,
        number=number,
    )


def _validate_section_structure(
    sections: tuple[SectionConfiguration, ...],
) -> None:
    """Validate the required high-level book structure."""
    counts = {
        section_type: sum(
            section.section_type == section_type
            for section in sections
        )
        for section_type in SectionType
    }

    if counts[SectionType.TITLE_PAGE] > 1:
        raise ValueError(
            "A book may contain at most one title page."
        )

    if counts[SectionType.FRONT_MATTER] > 1:
        raise ValueError(
            "A book may contain at most one front-matter section."
        )

    if counts[SectionType.TABLE_OF_CONTENTS] != 1:
        raise ValueError(
            "A book must contain exactly one table-of-contents section."
        )

    if counts[SectionType.CHAPTER] < 1:
        raise ValueError(
            "A book must contain at least one chapter."
        )

    if counts[SectionType.BACK_MATTER] > 1:
        raise ValueError(
            "A book may contain at most one back-matter section."
        )


def _parse_section_type(
    value: object,
) -> SectionType:
    """Convert a YAML section type to the semantic-model enum."""
    if not isinstance(value, str):
        raise ValueError("Section type must be a string.")

    try:
        return SectionType(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid section type: {value!r}. "
            "Expected one of: "
            + ", ".join(
                section_type.value
                for section_type in SectionType
            )
            + "."
        ) from error


def _parse_source_file(
    section: dict,
    directory: Path,
) -> Path:
    """Parse and validate a section's XHTML source file."""
    value = _require_string(section, "file")
    source_file = directory / value

    if not source_file.is_file():
        raise FileNotFoundError(
            f"Configured XHTML file does not exist: {source_file}"
        )

    return source_file


def _parse_measurement(
    configuration: dict,
    name: str,
) -> Measurement:
    """Parse a required physical measurement."""
    value = _require_string(configuration, name)
    return Measurement.from_string(value)


def _require_mapping(
    configuration: dict,
    name: str,
) -> dict:
    """Return a required YAML mapping."""
    value = configuration.get(name)

    if not isinstance(value, dict):
        raise ValueError(f"'{name}' must be a mapping.")

    return value


def _require_string(
    configuration: dict,
    name: str,
) -> str:
    """Return a required non-empty YAML string."""
    value = configuration.get(name)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")

    return value.strip()
