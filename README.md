# book-gen

Simplify the editing and generation of books, from manuscript to publishable formats.

The goal of this project is that, from a book text written in Markdown, this package should perform some basic editing checks on the source document, then generate both an ebook in [EPUB format](https://opensource.com/article/22/8/epub-file) and a typeset, print-ready PDF for a print book (to be printed through a platform like [Amazon Kindle Direct Publishing](https://kdp.amazon.com/)).

As of October 2026, the project is not there yet. Instead, there are two modules (`editingchecks` and `printbook`) which offer support for several parts of the editing and publishing process.

## Getting started

Choose your favorite method to [clone this repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) to your development environment.

A `requirements.txt` file exists, listing the external packages and versions that you can use to create [a Python virtual environment](https://docs.python.org/3/tutorial/venv.html). 

## Module: `editingchecks`

This module operates on a manuscript draft that has already been prepared in a plain text 
format. It performs a number of format and character-usage checks on that text, before
the text is sent downstream for generation of an EPUB or print book.

This module currently contains four files

```
editingchecks
├── editingchecks.py
├── generate.py
├── inventory.py
└── unicodesummary.py
```

### editingchecks.py
"""Run editing checks on a text document"""
  "Usage: editingchecks.py text_file"

This is currently the main entry point for this module. The `main()` function here 
creates an inventory of the characters in the file using functions in `inventory.py`,
and then runs a series of spot-checks using tests that are defined in the `runchecks()`
function of this module.

### generate.py
"""Convert from input text to output for ebook"""
  "Usage: generate.py text_file"

This is a small utility module. The only function that is currently defined
is `addparagraphs()`, which adds HTML paragraph opening and closing tags for each line.

### inventory.py
"""Generate a character inventory"""
  "Usage: inventory.py text_file"

This module includes a very simple function `getinventory()` to create a `Counter()` 
for characters in an iterable, and a `prettyprint()` function to create a
more readable display of this inventory, particularly when displaying characters
that might not be printable otherwise.

### unicodesummary.py
"""Print a summary of the Unicode characters in text"""
  "Usage: python unicodesummary.py "Héllo — café!"
  "Usage: echo 'Héllo — café!' | python unicodesummary.py"
  "Usage: python unicodesummary.py --file my_text.txt"

This is an extension to the code in `inventory.py` which allows more convenient 
stand-alone generation of a Unicode character summary. Text may be analyzed by
passing it directly from the command line, by piping or redirecting it, or by
providing the path to a file to be analyzed.

## Module: `printbook`

This module requires that an EPUB version of a book has already been created; it
will use some components of that EPUB version, along with some print-specific 
configuration information, to generate a typeset PDF for printing. The pipeline is

```
EPUB XHTML + CSS    print-specific configuration file
        │            │
        ▼            ▼
┌──────────────────────┐
│ XHTML/CSS parser     │
│                      │
│ structure + cascade  │
└──────────┬───────────┘
           │
           ▼
      Parsed Book
           │
           ▼
┌──────────────────────┐
│ RenderingStyle       │
│ converter            │
└──────────┬───────────┘
           │
           ▼
        Book
   (semantic model)
           │
           ▼
┌──────────────────────┐
│ LuaLaTeX renderer    │
└──────────┬───────────┘
           │
           ▼
      .tex file
           │
           ▼
        LuaLaTeX
           │
           ▼
         PDF
```

This module currently contains the following files

```
printbook
├── check_css_usage.py
├── configuration.py
├── css_parser.py
├── kdp.py
├── latex_renderer.py
├── model.py
├── rendering_style.py
└── xhtml_parser.py
```

### check_css_usage.py
"""Report CSS classes used by XHTML files in an extracted EPUB directory.

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

### configuration.py
"""Configuration for print-book editions.

This module parses and validates the YAML configuration for a print book.

It contains no XHTML, CSS, semantic-model, or LaTeX rendering logic.
KDP-specific requirements are handled by the kdp module.
"""

### kdp.py
"""KDP-specific print requirements.

This module contains rules specific to Amazon KDP paperback manuscript
requirements. It should not contain book-specific configuration.

The minimum inside (gutter) margin depends on the final page count.
"""

### model.py
"""Semantic model for print books.

This module defines the intermediate representation used by the print-book
pipeline. It intentionally contains no EPUB, XHTML, CSS, YAML, or LaTeX
logic.

The model represents the semantic structure of a book and the meaningful
typographic and rendering distinctions that must survive conversion from EPUB
to print.
"""
