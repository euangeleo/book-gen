"""Orchestrate the print-book conversion pipeline."""

from pathlib import Path

from configuration import load_configuration
from latex_renderer import LatexRenderer
from xhtml_parser import XhtmlParser


def build_book(book_directory: Path):
    """Build the semantic book model from a print-book directory."""
    configuration = load_configuration(book_directory)

    parser = XhtmlParser(configuration)
    book = parser.parse()

    return configuration, book


def render_book(
    book_directory: Path,
    output_path: Path,
) -> Path:
    """Convert a print-book directory into a LaTeX source file."""
    configuration, book = build_book(book_directory)

    renderer = LatexRenderer(configuration)
    renderer.render(book, output_path)

    return output_path

def build_print_book(book_directory: Path, output_directory: Path) -> Path:
    """Build a print-ready PDF from a print-book directory."""

    configuration = load_configuration(book_directory)

    book = parse_book(
        configuration=configuration,
    )

    latex_source = render_latex(
        book=book,
        configuration=configuration,
    )

    tex_path = output_directory / "book.tex"
    tex_path.write_text(
        latex_source,
        encoding="utf-8",
    )

    pdf_path = compile_latex(
        tex_path=tex_path,
    )

    validate_kdp_requirements(
        pdf_path=pdf_path,
        configuration=configuration,
    )

    return pdf_path