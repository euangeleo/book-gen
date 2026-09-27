#!/usr/bin/env python3

"""
Report CSS classes used by XHTML files in an extracted EPUB directory.

Usage:
    python check_css_usage.py /path/to/unzipped/epub

The program reports:
    * CSS classes used in the XHTML files
    * Number of occurrences in each XHTML file
    * CSS classes defined in styles.css but never used
    * Classes used in XHTML but not defined in styles.css

Requires:
    beautifulsoup4
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from bs4 import BeautifulSoup


STYLESHEET_FILENAME = "styles.css"
XHTML_SUFFIXES = {".xhtml", ".html"}


def find_xhtml_files(book_directory: Path) -> list[Path]:
    """Return all XHTML files beneath the book directory."""
    return sorted(
        path
        for path in book_directory.rglob("*")
        if path.is_file() and path.suffix.lower() in XHTML_SUFFIXES
    )


def collect_class_usage(
        xhtml_files: list[Path],
) -> dict[str, Counter[str]]:
    """Return class usage counts organized by XHTML filename."""
    usage_by_file: dict[str, Counter[str]] = {}

    for xhtml_file in xhtml_files:
        usage_by_file[xhtml_file.name] = extract_used_classes(xhtml_file)

    return usage_by_file


def extract_used_classes(xhtml_file: Path) -> Counter[str]:
    """Return the number of occurrences of each CSS class in an XHTML file."""
    with xhtml_file.open("r", encoding="utf-8") as file:
        document = BeautifulSoup(file, "html.parser")

    class_counts: Counter[str] = Counter(
        class_name
        for element in document.find_all(class_=True)
        for class_name in element.get("class", [])
    )

    return class_counts


def extract_defined_classes(stylesheet: Path) -> set[str]:
    """Return CSS class names defined by the stylesheet."""
    with stylesheet.open("r", encoding="utf-8") as file:
        css = file.read()

    return set(re.findall(r"\.([A-Za-z_][\w-]*)", css))


def print_used_classes(usage_by_file: dict[str, Counter[str]]) -> None:
    """Print every CSS class found in the XHTML files."""
    all_classes = sorted(
        {
            class_name
            for class_counts in usage_by_file.values()
            for class_name in class_counts
        }
    )

    print("CSS CLASSES USED")
    print("================")

    for class_name in all_classes:
        print(f"\n.{class_name}")

        for filename, class_counts in usage_by_file.items():
            count = class_counts.get(class_name, 0)

            if count:
                print(f"    {filename}: {count}")


def print_unused_classes(
    defined_classes: set[str],
    used_classes: set[str],
) -> None:
    """Print CSS classes defined but never used."""
    unused_classes = sorted(defined_classes - used_classes)

    print("\nCSS CLASSES DEFINED BUT NOT USED")
    print("================================")

    if not unused_classes:
        print("    None")

    for class_name in unused_classes:
        print(f"    .{class_name}")


def print_undefined_classes(
    defined_classes: set[str],
    used_classes: set[str],
) -> None:
    """Print CSS classes used but not defined."""
    undefined_classes = sorted(used_classes - defined_classes)

    print("\nCSS CLASSES USED BUT NOT DEFINED")
    print("================================")

    if not undefined_classes:
        print("    None")

    for class_name in undefined_classes:
        print(f"    .{class_name}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze CSS class usage in an extracted EPUB."
    )

    parser.add_argument(
        "book_directory",
        type=Path,
        help="Directory containing the extracted EPUB files.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the CSS usage analysis."""
    try:
        arguments = parse_arguments()
        book_directory = arguments.book_directory
    except:
        print("Usage: python check_css_usage.py /path/to/unzipped/epub\n")
        raise SystemExit(f"Invalid arguments: {arguments}")

    if not book_directory.is_dir():
        raise SystemExit(f"Not a directory: {book_directory}")

    stylesheet = book_directory / STYLESHEET_FILENAME

    if not stylesheet.is_file():
        raise SystemExit(f"Stylesheet not found: {stylesheet}")

    xhtml_files = find_xhtml_files(book_directory)

    if not xhtml_files:
        raise SystemExit(f"No XHTML files found in: {book_directory}")

    usage_by_file = collect_class_usage(xhtml_files)
    defined_classes = extract_defined_classes(stylesheet)

    used_classes = {
        class_name
        for class_counts in usage_by_file.values()
        for class_name in class_counts
    }

    print_used_classes(usage_by_file)
    print_unused_classes(defined_classes, used_classes)
    print_undefined_classes(defined_classes, used_classes)


if __name__ == "__main__":
    main()