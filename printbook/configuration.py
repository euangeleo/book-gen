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
    """Font families and their associated local font files."""

    body: str
    handwriting_script: str | None
    handwriting_print: str | None
    paths: dict[str, Path]


@dataclass(frozen=True)
class HandwritingConfiguration:
    """Mapping between EPUB handwriting classes and semantic variants."""

    default_variant: HandwritingVariant
    class_mappings: dict[str, HandwritingVariant]

    def get_variant(self, class_name: str) -> HandwritingVariant:
        """Return the semantic variant associated with an EPUB CSS class."""
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
    fonts = _parse_font_configuration(raw_configuration, directory)
    handwriting = _parse_handwriting_configuration(raw_configuration)

    _validate_handwriting_fonts(fonts, handwriting)

    return PrintBookConfiguration(
        directory=directory,
        book=_parse_book_metadata(raw_configuration),
        page=_parse_page_configuration(raw_configuration),
        margins=_parse_margin_configuration(raw_configuration),
        fonts=fonts,
        handwriting=handwriting,
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
    """Parse font-family names and their local font-file paths."""
    fonts = _require_mapping(configuration, "fonts")

    body = _require_string(fonts, "body")

    handwriting = _require_mapping(fonts, "handwriting")

    handwriting_script = _parse_optional_font_family(
        handwriting,
        "script",
    )

    handwriting_print = _parse_optional_font_family(
        handwriting,
        "print",
    )

    paths = _parse_font_paths(fonts, directory)

    return FontConfiguration(
        body=body,
        handwriting_script=handwriting_script,
        handwriting_print=handwriting_print,
        paths=paths,
    )


def _parse_optional_font_family(
    configuration: dict,
    name: str,
) -> str | None:
    """Parse an optional font-family name."""
    value = configuration.get(name)

    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Font family '{name}' must be a non-empty string."
        )

    return value


def _parse_font_paths(
    fonts: dict,
    directory: Path,
) -> dict[str, Path]:
    """Parse the mapping from font-family names to local font files."""
    raw_paths = _require_mapping(fonts, "paths")

    paths: dict[str, Path] = {}

    for font_family, raw_path in raw_paths.items():
        if not isinstance(font_family, str) or not font_family.strip():
            raise ValueError(
                "Every font path entry must have a non-empty "
                "font-family name."
            )

        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(
                f"Font path for '{font_family}' must be a "
                "non-empty string."
            )

        font_path = directory / raw_path

        if not font_path.is_file():
            warnings.warn(
                f"Configured font does not exist: {font_path}",
                UserWarning,
                stacklevel=2,
            )

        paths[font_family] = font_path

    return paths


def _parse_handwriting_configuration(
    configuration: dict,
) -> HandwritingConfiguration:
    """Parse handwriting variant configuration."""
    fonts = _require_mapping(configuration, "fonts")
    handwriting = _require_mapping(fonts, "handwriting")

    default_variant = _parse_handwriting_variant(
        _require_string(handwriting, "default_variant")
    )

    raw_mappings = handwriting.get("classes", {})

    if not isinstance(raw_mappings, dict):
        raise ValueError("'fonts.handwriting.classes' must be a mapping.")

    class_mappings = {
        _require_class_name(class_name):
        _parse_handwriting_variant(variant)
        for class_name, variant in raw_mappings.items()
    }

    return HandwritingConfiguration(
        default_variant=default_variant,
        class_mappings=class_mappings,
    )


def _require_class_name(value: object) -> str:
    """Validate and return an XHTML/CSS class name."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "Every handwriting class mapping must have a "
            "non-empty class name."
        )

    return value


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


def _validate_handwriting_fonts(
    fonts: FontConfiguration,
    handwriting: HandwritingConfiguration,
) -> None:
    """Validate font configuration required by handwriting variants."""
    variants_in_use = {
        handwriting.default_variant,
        *handwriting.class_mappings.values(),
    }

    for variant in variants_in_use:
        font_family = _get_handwriting_font_family(
            fonts,
            variant,
        )

        if font_family is None:
            raise ValueError(
                f"Handwriting variant '{variant.value}' is used, "
                "but no corresponding font family is configured."
            )

        if font_family not in fonts.paths:
            raise ValueError(
                f"Handwriting variant '{variant.value}' uses font "
                f"family '{font_family}', but that font family has "
                "no entry in 'fonts.paths'."
            )


def _get_handwriting_font_family(
    fonts: FontConfiguration,
    variant: HandwritingVariant,
) -> str | None:
    """Return the configured font family for a handwriting variant."""
    if variant is HandwritingVariant.SCRIPT:
        return fonts.handwriting_script

    if variant is HandwritingVariant.PRINT:
        return fonts.handwriting_print

    raise ValueError(
        f"Unsupported handwriting variant: {variant.value!r}."
    )


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
