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
class FontConfiguration:
    """Fonts available to the print edition."""

    body: Path | None = None
    handwriting_script: Path | None = None
    handwriting_print: Path | None = None


@dataclass(frozen=True)
class HandwritingConfiguration:
    """Mapping between EPUB handwriting classes and semantic variants."""

    default_variant: HandwritingVariant = HandwritingVariant.SCRIPT

    class_mappings: dict[str, HandwritingVariant] | None = None

    def get_variant(self, class_name: str) -> HandwritingVariant:
        """Return the semantic variant associated with an EPUB CSS class."""
        if self.class_mappings is not None:
            if class_name in self.class_mappings:
                return self.class_mappings[class_name]

        return self.default_variant


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
    handwriting: HandwritingConfiguration
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

    directory = configuration_path.parent

    return _create_configuration(raw_configuration, directory)


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
        fonts=_parse_font_configuration(raw_configuration, directory),
        handwriting=_parse_handwriting_configuration(raw_configuration),
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
    """Parse and validate configured font files."""
    fonts = configuration.get("fonts", {})

    if not isinstance(fonts, dict):
        raise ValueError("'fonts' must be a mapping.")

    body = _parse_optional_font(fonts, "body", directory)

    handwriting = fonts.get("handwriting", {})

    if not isinstance(handwriting, dict):
        raise ValueError("'fonts.handwriting' must be a mapping.")

    handwriting_script = _parse_optional_font(
        handwriting,
        "script",
        directory,
    )

    handwriting_print = _parse_optional_font(
        handwriting,
        "print",
        directory,
    )

    return FontConfiguration(
        body=body,
        handwriting_script=handwriting_script,
        handwriting_print=handwriting_print,
    )


def _parse_optional_font(
    configuration: dict,
    name: str,
    directory: Path,
) -> Path | None:
    """Parse an optional font path and warn if it does not exist."""
    value = configuration.get(name)

    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"Font '{name}' must be a string.")

    font_path = directory / value

    if not font_path.is_file():
        warnings.warn(
            f"Configured font does not exist: {font_path}",
            UserWarning,
            stacklevel=2,
        )

    return font_path


def _parse_handwriting_configuration(
    configuration: dict,
) -> HandwritingConfiguration:
    """Parse handwriting variant configuration."""
    handwriting = configuration.get("handwriting", {})

    if not isinstance(handwriting, dict):
        raise ValueError("'handwriting' must be a mapping.")

    default_variant = _parse_handwriting_variant(
        handwriting.get("default_variant", "script")
    )

    raw_mappings = handwriting.get("classes", {})

    if not isinstance(raw_mappings, dict):
        raise ValueError("'handwriting.classes' must be a mapping.")

    class_mappings = {
        class_name: _parse_handwriting_variant(variant)
        for class_name, variant in raw_mappings.items()
    }

    return HandwritingConfiguration(
        default_variant=default_variant,
        class_mappings=class_mappings,
    )


def _parse_handwriting_variant(value: object) -> HandwritingVariant:
    """Convert a YAML handwriting variant to the semantic-model enum."""
    if not isinstance(value, str):
        raise ValueError("Handwriting variant must be a string.")

    try:
        return HandwritingVariant(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid handwriting variant: {value!r}."
        ) from error


def _parse_section_configurations(
    configuration: dict,
    directory: Path,
) -> tuple[SectionConfiguration, ...]:
    """Parse and validate the sequential book sections."""
    raw_sections = configuration.get("sections")

    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("'sections' must be a non-empty list.")

    sections = [
        _parse_section_configuration(section, directory)
        for section in raw_sections
    ]

    return tuple(sections)


def _parse_section_configuration(
    section: object,
    directory: Path,
) -> SectionConfiguration:
    """Parse one section configuration."""
    if not isinstance(section, dict):
        raise ValueError("Each section must be a mapping.")

    section_type = _parse_section_type(section.get("type"))
    file = _parse_source_file(section, directory)

    number = section.get("number")

    if number is not None:
        if not isinstance(number, int) or number < 1:
            raise ValueError(
                "Section number must be a positive integer."
            )

    return SectionConfiguration(
        section_type=section_type,
        file=file,
        number=number,
    )


def _parse_section_type(value: object) -> SectionType:
    """Convert a YAML section type to the semantic-model enum."""
    if not isinstance(value, str):
        raise ValueError("Section type must be a string.")

    try:
        return SectionType(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid section type: {value!r}."
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

    return value