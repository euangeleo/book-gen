# Print Book Conversion Pipeline
## Component Interface Specification

**Status:** Draft  
**Language:** Python 3.12+  
**Output:** Print-ready PDF  
**Typesetting engine:** LuaLaTeX  
**Document class:** `memoir`

---

## 1. Purpose and scope

This document defines the public interfaces and responsibilities of the Python components 
used to convert manually extracted EPUB XHTML and CSS content into a print-ready PDF.

The project uses a design-first architecture in which each component has a clearly defined
responsibility and communicates with other components through explicit interfaces.

The primary processing stages are:

1. Load and validate the book configuration.
2. Parse the configured XHTML and associated CSS.
3. Convert the source documents into the semantic book model.
4. Render the semantic model as LaTeX.
5. Compile the LaTeX source into a PDF using LuaLaTeX.
6. Validate the resulting PDF against applicable KDP requirements.

Python coordinates these operations. LuaLaTeX performs the final typesetting.

### 1.1 Design principles

The implementation should follow these principles:

- Each module has one primary responsibility.
- Public interfaces should be small and stable.
- Components communicate through explicitly defined data structures.
- The semantic model is independent of XHTML, CSS, YAML, and LaTeX.
- Configuration data is not embedded in the semantic model.
- Rendering decisions are made in the renderer, not in the XHTML parser.
- KDP-specific rules are isolated from general document processing.
- Intermediate files, especially the generated `.tex` source, remain available for inspection and manual adjustment.

### 1.2 Project scope and assumptions

The initial implementation assumes:

- EPUB files are manually extracted outside the Python application.
- Only the XHTML files, CSS files, and custom fonts needed for the print edition are copied into the print-version directory.
- Python does not unzip or otherwise modify the original EPUB.
- The initial output consists of black text on white or unprinted paper.
- Images, indexing, and cross-references are outside the initial scope.
- The semantic model supports the textual structures required by the source books.
- The final PDF is produced using LuaLaTeX and the `memoir` document class.

---

## 2. Overall architecture

### 2.1 Processing flow

```text
                   book.yaml
                       |
                       v
              configuration.py
              load_configuration()
                       |
                       v
             PrintBookConfiguration
                       |
                       v
                xhtml_parser.py
                  XhtmlParser
                       |
             +---------+---------+
             |                   |
             v                   v
         css_parser.py     rendering_style.py
         CssStylesheet     RenderingStyleConverter
         CssCascadeResolver
             |                   |
             +---------+---------+
                       |
                       v
                    model.py
                      Book
                       |
                       v
               latex_renderer.py
                 LatexRenderer
                       |
                       v
                  LaTeX source
                       |
                       v
                    LuaLaTeX
                       |
                       v
                      PDF
                       |
                       v
                    kdp.py
            get_minimum_gutter_inches()
                       |
                       v
               KDP validation
```

The `pipeline.py` module coordinates this process. The `main.py` module provides the command-line entry point.

### 2.2 Public module interfaces

| Module | Public interface |
|---|---|
| `main.py` | `main()` |
| `pipeline.py` | `build_print_book()` |
| `configuration.py` | `load_configuration()` |
| `css_parser.py` | `CssStylesheet`, `CssCascadeResolver` |
| `rendering_style.py` | `ResolvedCssStyle`, `RenderingStyleConverter` |
| `xhtml_parser.py` | `XhtmlParser` |
| `latex_renderer.py` | `LatexRenderer` |
| `kdp.py` | `get_minimum_gutter_inches()` |

The public interfaces listed above constitute the initial module API. Additional functions 
and classes may be introduced as private implementation details without expanding that API.

---

## 3. Shared data contracts

The components exchange several important data structures.

### 3.1 Configuration model

The configuration module returns a `PrintBookConfiguration` instance.

The configuration model contains:

- Book metadata.
- Page dimensions.
- Page margins.
- Font configuration.
- Ordered section configuration.
- Paths to source XHTML files and configured font files.

The configuration model is defined in `configuration.py` and is consumed by the XHTML parser, 
rendering-style converter, LaTeX renderer, and pipeline.

It is not part of the semantic book model.

### 3.2 Semantic book model

The semantic model is defined independently of the processing modules.

Its principal public type is:

```python
Book
```

A `Book` contains ordered `Section` objects. Sections contain semantic block-level content, 
which in turn may contain inline content.

The model includes, among other types:

- `Section`
- `Heading`
- `Paragraph`
- `BlockQuote`
- `SectionBreak`
- `List`
- `ListItem`
- `Table`
- `TableRow`
- `TableCell`
- `TableOfContents`
- `Text`
- `Italic`
- `Bold`
- `SmallCaps`
- `Handwriting`
- `SMS`
- `DropCap`
- `LineBreak`

Rendering information is represented by `RenderingStyle`, which is independent of CSS syntax and LaTeX commands.

The semantic model is the contract between the XHTML parser and the LaTeX renderer.

### 3.3 CSS data model

The CSS parser produces a resolved representation of the CSS declarations applicable to an XHTML element.

The rendering-style converter translates that representation into the semantic model's `RenderingStyle` type.

This distinction is intentional:

```text
CSS declarations
       |
       v
ResolvedCssStyle
       |
       v
RenderingStyle
       |
       v
Semantic content
```

`ResolvedCssStyle` retains CSS-oriented information. `RenderingStyle` represents the 
rendering requirements that must survive conversion into the semantic model.

---

# 4. Module specifications

## 4.1 `main.py`

### Responsibility

Provide the command-line interface for the application.

`main.py` is the application's entry point. It should not contain document-processing 
logic or directly interact with the lower-level components.

### Public interface

```python
def main() -> int:
    """Run the print-book command-line application."""
```

### Inputs

Command-line arguments, including:

- Input book directory.
- Output directory.

The precise argument names and defaults will be established when the CLI is implemented.

### Return value

An integer process exit status:

- `0`: successful completion.
- Nonzero: an error occurred.

### Dependencies

- `pipeline.py`
- Standard-library command-line and output facilities.

### Responsibilities

1. Parse command-line arguments.
2. Call `pipeline.build_print_book()`.
3. Report the resulting PDF path on success.
4. Report a useful error message on failure.
5. Return the appropriate exit status.

### Error handling

`main()` should catch the application's public pipeline exception, report 
the error to standard error, and return a nonzero status.

It should not attempt to recover from individual CSS, XHTML, or LaTeX errors itself.

---

## 4.2 `pipeline.py`

### Responsibility

Coordinate the complete conversion process.

The pipeline is the application's orchestration layer. It knows the order in which 
components must run, but should not implement their underlying functionality.

### Public interface

```python
def build_print_book(
    book_directory: Path,
    output_directory: Path,
) -> Path:
    """Build a print-ready PDF from a print-book source directory."""
```

### Inputs

| Argument | Type | Description |
|---|---|---|
| `book_directory` | `Path` | Directory containing `book.yaml`, XHTML, CSS, and required source assets. |
| `output_directory` | `Path` | Destination for generated LaTeX and PDF files. |

### Return value

A `Path` identifying the successfully generated PDF.

### Processing responsibilities

The function coordinates the following operations:

1. Load the configuration using `configuration.load_configuration()`.
2. Parse the configured XHTML files using `XhtmlParser`.
3. Obtain the semantic `Book` model.
4. Render the semantic model using `LatexRenderer`.
5. Write the generated LaTeX source to the output directory.
6. Compile the LaTeX source using LuaLaTeX.
7. Determine the resulting PDF's page count.
8. Obtain the required minimum gutter from `kdp.get_minimum_gutter_inches()`.
9. Compare the required gutter with the configured inner margin.
10. Return the PDF path if validation succeeds.

### PDF validation and KDP compliance

After compiling the LaTeX source into a PDF, the pipeline must determine the final page 
count and validate the resulting document against the applicable KDP print requirements.

The pipeline must:

1. Determine the final PDF page count.
2. Obtain the applicable minimum inner margin using `kdp.get_minimum_gutter_inches()`.
3. Compare the required minimum with the configured inner margin.
4. Check the resulting PDF dimensions and other applicable page-margin requirements.
5. Report any detected compliance violations to the user.

If validation fails, the application must provide sufficient diagnostic information 
for the user to update the print configuration. This information should include, as 
applicable:

- The generated PDF's page count.
- The applicable KDP minimum inner margin.
- The configured inner margin.
- The difference between the configured and required margins.
- Any other detected page-dimension or margin violations, including the actual and required values.

The application must not silently modify the configuration or automatically adjust 
page geometry to correct compliance violations.

The user can update the print configuration and run the build process again. The pipeline 
must use the revised configuration to generate a new PDF and repeat the validation process.

A PDF that fails required validation must not be reported as a successfully completed, 
KDP-compliant build. The generated PDF and LaTeX source may nevertheless be retained for 
inspection and correction.

### Side effects

The pipeline is responsible for creating the output directory when necessary and writing generated files.

The generated `.tex` file should be retained alongside the PDF so that it can be inspected or manually adjusted.

### Dependencies

- `configuration.py`
- `xhtml_parser.py`
- `latex_renderer.py`
- `kdp.py`
- LuaLaTeX executable
- A mechanism for obtaining the PDF page count

### Error handling

The pipeline should propagate or wrap component errors in an application-level exception.

A proposed exception contract is:

```python
class PrintBookError(Exception):
    """Base exception for print-book build failures."""
```

Specific errors may retain their original exceptions as causes.

The pipeline should not return a PDF path if compilation or required validation fails.

### Design constraints

- The pipeline must not parse XHTML or CSS itself.
- The pipeline must not construct semantic model objects.
- The pipeline must not generate LaTeX fragments.
- The pipeline must not implement KDP gutter rules.
- PDF compilation and page-count retrieval are build operations, not KDP-specific operations.

Private helper functions may be introduced to keep the implementation manageable. They
are not part of the public API.

---

## 4.3 `configuration.py`

### Responsibility

Load, parse, and validate the book-specific YAML configuration.

### Public interface

```python
def load_configuration(
    book_directory: Path,
) -> PrintBookConfiguration:
    """Load and validate a print-book configuration."""
```

### Input

`book_directory` identifies the print-version directory containing `book.yaml`.

### Return value

A fully populated `PrintBookConfiguration` instance.

### Configuration contents

The configuration model includes:

- `BookMetadata`
- `PageConfiguration`
- `MarginConfiguration`
- `FontConfiguration`
- `HandwritingConfiguration`
- Ordered `SectionConfiguration` objects

### Responsibilities

1. Locate and read `book.yaml`.
2. Parse the YAML document.
3. Validate required configuration fields.
4. Convert YAML values into typed configuration objects.
5. Resolve relative file paths against `book_directory`.
6. Validate supported measurement units.
7. Validate the required high-level section structure.
8. Validate that configured font families have corresponding font paths.
9. Warn about missing font files where appropriate.

### Section-order invariant

The configured sections must follow this sequence:

```text
title_page? 
front_matter?
table_of_contents
chapter+
back_matter?
```

The following constraints apply:

- At most one title page.
- At most one front-matter section.
- Exactly one table-of-contents section.
- At least one chapter.
- At most one back-matter section.
- Sections must occur in the prescribed order.

### Font configuration

The configuration must provide:

- A body font family.
- An SMS font family.
- A default handwriting variant.
- A font family for each handwriting variant.
- A path for each configured font family.

The paths are resolved relative to the book directory.

A configured font file that does not exist should produce a warning during 
configuration loading. If a required font is subsequently needed for rendering 
and remains unavailable, rendering must fail rather than silently substituting 
an unrelated font.

### Exceptions

The implementation should distinguish at least:

- Missing configuration file.
- Invalid YAML.
- Missing required configuration values.
- Invalid measurement values or units.
- Invalid section structure.
- Invalid font configuration.

These may initially be represented by `ValueError` and `FileNotFoundError`; a 
dedicated configuration exception can be introduced if it improves error reporting.

### Design constraints

This module must not parse XHTML, load CSS, construct the semantic `Book`, or generate LaTeX.

---

## 4.4 `css_parser.py`

### Responsibility

Load CSS stylesheets and resolve the CSS declarations applicable to individual XHTML elements.

This module handles CSS syntax and cascading. It does not interpret CSS classes as semantic book structures.

### Public types

```python
class CssStylesheet:
    """A parsed CSS stylesheet."""
```

```python
class CssCascadeResolver:
    """Resolve CSS styles for XHTML elements."""
```

### `CssStylesheet`

Proposed public construction interfaces:

```python
@classmethod
def from_file(
    cls,
    path: Path,
) -> CssStylesheet:
    """Load and parse a CSS stylesheet from a file."""
```

```python
@classmethod
def from_text(
    cls,
    text: str,
) -> CssStylesheet:
    """Parse a CSS stylesheet from a string."""
```

`from_text()` is particularly useful for unit tests, where small CSS examples 
can be supplied without creating temporary files.

A stylesheet represents parsed CSS rules. It does not represent the resolved 
style of any particular XHTML element.

### `CssCascadeResolver`

Proposed public interface:

```python
class CssCascadeResolver:
    def __init__(
        self,
        stylesheets: Sequence[CssStylesheet],
    ) -> None:
        """Initialize the resolver with ordered stylesheets."""

    def resolve(
        self,
        element: Element,
    ) -> ResolvedCssStyle:
        """Resolve CSS declarations applicable to an XHTML element."""
```

`Element` represents an element from the XHTML parser's chosen XML library. The 
exact type will be fixed when that library is selected.

### Responsibilities

- Parse CSS rules and declarations.
- Recognize supported selectors.
- Match selectors against XHTML elements.
- Apply selector specificity.
- Respect stylesheet order.
- Resolve applicable declarations.
- Account for supported inheritance.
- Return a `ResolvedCssStyle`.

### CSS source handling

The XHTML parser is responsible for discovering and loading the stylesheets referenced 
by the configured XHTML documents.

The CSS parser is responsible for parsing those stylesheets and resolving their declarations.

The initial implementation should support the CSS features required by the supplied books 
rather than attempting to implement the entire CSS specification.

Unsupported or malformed CSS should be handled consistently and reported where it affects 
document rendering.

### Exceptions

A CSS parsing or resolution error should be distinguishable from an XHTML parsing error.

A dedicated `CssParseError` or `CssResolutionError` may be introduced.

### Design constraints

This module must not:

- Create semantic model objects.
- Interpret classes as `Handwriting`, `SMS`, `DropCap`, or `BlockQuote`.
- Generate LaTeX.
- Resolve configured font paths.

---

## 4.5 `rendering_style.py`

### Responsibility

Convert resolved CSS declarations into the rendering information represented by the semantic model.

This module is the translation boundary between CSS-specific information and the semantic rendering model.

### Public types

```python
@dataclass(frozen=True)
class ResolvedCssStyle:
    """CSS declarations resolved for an XHTML element."""
```

```python
class RenderingStyleConverter:
    """Convert resolved CSS styles into semantic rendering styles."""
```

### `ResolvedCssStyle`

This type represents CSS declarations after selector matching and cascading.

It should retain the CSS-oriented information needed by the converter, including supported properties such as:

- Font family.
- Font size.
- Font weight.
- Font style.
- Line height.
- Letter spacing.
- Text alignment.
- Text indentation.
- Margins.
- Padding.
- Text transformation.
- Text decoration.
- Foreground and background colors.
- Borders.
- Page-break behavior.

The representation should be independent of LaTeX.

The precise internal representation of CSS property values is an implementation decision, 
provided that it preserves the information required by the converter.

### `RenderingStyleConverter`

Proposed public interface:

```python
class RenderingStyleConverter:
    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        """Initialize the converter with book-specific font settings."""

    def convert(
        self,
        style: ResolvedCssStyle,
    ) -> RenderingStyle:
        """Convert resolved CSS into a semantic RenderingStyle."""
```

### Responsibilities

1. Convert supported CSS measurements into semantic `Length` values.
2. Convert CSS font properties into semantic font properties.
3. Convert alignment, indentation, spacing, and decoration properties.
4. Convert supported border and padding information.
5. Preserve page-break behavior.
6. Resolve configured font-family semantics where required.
7. Return a `RenderingStyle` independent of CSS syntax.

### Font handling

Font configuration is available through `PrintBookConfiguration`.

The converter must support the established font semantics:

- **Body text** uses the configured body font.
- **SMS text** uses the configured SMS font.
- **Handwriting text** uses the configured handwriting family.
  - An explicit handwriting variant, script or print, selects the corresponding configured family.
  - If no variant is specified, the configured default variant applies.

The converter should not resolve font-file paths or generate LaTeX font declarations. Those 
are renderer responsibilities.

### Semantic interpretation boundary

The converter translates rendering properties. It does not decide that an element is a paragraph, 
block quote, section break, or drop cap. Those structural decisions belong to `XhtmlParser`.

### Exceptions

Unsupported or invalid CSS values should produce a clear conversion error when they cannot be 
represented safely.

---

## 4.6 `xhtml_parser.py`

### Responsibility

Parse configured XHTML documents and construct the semantic `Book` model. This module converts 
source document structure into meaningful book structure.

### Public interface

```python
class XhtmlParser:
    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        """Initialize the parser with book configuration."""

    def parse(self) -> Book:
        """Parse all configured XHTML sections into a Book."""
```

### Input

A `PrintBookConfiguration` containing the ordered source XHTML files and associated book configuration.

### Return value

A complete semantic `Book`.

### Responsibilities

1. Read the configured XHTML files in their specified order.
2. Parse XHTML while preserving document structure.
3. Discover and load associated stylesheets.
4. Use `CssStylesheet` and `CssCascadeResolver` to resolve CSS.
5. Use `RenderingStyleConverter` to obtain semantic rendering styles.
6. Interpret XHTML structure and supported class markers.
7. Construct semantic block and inline objects.
8. Assemble the resulting content into ordered `Section` objects.
9. Construct the complete `Book` model.

### Required semantic mappings

The parser must support the established mappings, including:

| XHTML/CSS feature | Semantic representation |
|---|---|
| Paragraph | `Paragraph` |
| Heading | `Heading` |
| `<br>` | `LineBreak` |
| Block-quote marker | `BlockQuote` |
| Section-break marker | `SectionBreak` |
| Handwriting marker | `Handwriting` |
| SMS/editing marker | `SMS` |
| Drop-cap markup | `DropCap` |
| Italic text | `Italic` |
| Bold text | `Bold` |
| Small-cap text | `SmallCaps` |
| Ordered list | `List` with `ListType.ORDERED` |
| Unordered list | `List` with `ListType.UNORDERED` |
| Table | `Table` |

The parser must preserve the inline content and meaningful rendering distinctions 
represented by the semantic model.

### Chapter and TOC invariants

The initial book structure has exactly one semantic table of contents and one or more chapters.

The TOC contains chapter entries only.

The parser must preserve the association between chapter sections and TOC entries. The number 
of TOC entries must equal the number of chapter sections.

For each chapter:

- The first and only H1 represents the chapter title.
- H1 content is preserved as inline semantic content.
- A `LineBreak` within the H1 remains a `LineBreak`.
- H2 and lower headings do not automatically become memoir structural divisions.

The renderer will use the semantic chapter title and corresponding TOC entry to construct the 
memoir chapter command.

### CSS and XHTML responsibilities

The parser interprets document structure and semantic class markers.

The CSS resolver determines which declarations apply.

The rendering-style converter translates those declarations into semantic rendering information.

These responsibilities must remain separate even though the parser coordinates them.

### Exceptions

Malformed or unreadable XHTML should produce an XHTML parsing error.

Missing required source files should produce a clear error identifying the affected file.

CSS errors should retain their CSS-specific identity where practical.

### Design constraints

The parser must not:

- Generate LaTeX.
- Write the final PDF.
- Compile LaTeX.
- Calculate KDP gutter requirements.
- Resolve final page geometry.

---

## 4.7 `latex_renderer.py`

### Responsibility

Convert the semantic `Book` model into a complete LaTeX document.

The renderer is the only component that should know how semantic model objects map to LaTeX 
commands and environments.

### Public interface

```python
class LatexRenderer:
    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        """Initialize the renderer with book configuration."""

    def render(
        self,
        book: Book,
    ) -> str:
        """Render a semantic Book as LaTeX source."""
```

### Inputs

- `PrintBookConfiguration`
- Semantic `Book`

### Return value

A string containing a complete LaTeX source document. The returned source must be suitable 
for compilation using LuaLaTeX.

### Responsibilities

1. Generate the document preamble.
2. Configure the `memoir` document class.
3. Configure page dimensions and margins.
4. Configure the required packages.
5. Register and configure fonts using the configured font paths.
6. Render book metadata.
7. Render front matter, chapters, and back matter.
8. Render the table of contents.
9. Render block-level semantic content.
10. Render inline semantic content.
11. Escape LaTeX special characters in source text.
12. Generate a complete, compilable LaTeX document.

### Established rendering rules

The renderer must implement the following mappings:

| Semantic concept | LaTeX behavior |
|---|---|
| Title page | `\frontmatter` and title-page layout |
| Front matter | `\frontmatter` |
| Table of contents | `\frontmatter` |
| Chapter | `\mainmatter` and `\chapter` |
| Back matter | `\backmatter` |
| Small caps | `\textsc{...}` |
| Drop cap | `\lettrine{...}{...}` |
| Line break in chapter title | `\\` |
| Page break before content | `\clearpage` |
| Block quote | Appropriate quote environment or equivalent layout |
| Section break | Renderer-defined section-break treatment |
| Handwriting | Configured handwriting font |
| SMS | Configured SMS font |

### Chapter title handling

The first H1 in a chapter supplies its full chapter title.

The corresponding TOC entry supplies the chapter's short TOC title.

The renderer uses the memoir chapter interface:

```latex
\chapter[<toc-title>][<head-title>]{<title>}
```

The full title is rendered from the H1 inline content.

The running-head title is the H1 content before its first `LineBreak`.

A line break in the full title is rendered as `\\`.

### Font handling

The renderer is responsible for:

- Resolving configured font-family names to font paths.
- Loading fonts through LuaLaTeX-compatible font facilities.
- Generating the necessary font declarations.
- Applying body, SMS, and handwriting fonts.
- Raising an error if a required font file is unavailable.

The renderer must not silently substitute an unrelated font when a required 
configured font is missing.

### Page geometry and margins

The renderer uses the page dimensions and margins specified in the book configuration.

The configured inner margin is used as supplied. It must not be silently increased, 
reduced, or replaced with a KDP-derived value.

The renderer is responsible for translating the configured page dimensions and margins 
into the appropriate LaTeX page-geometry settings. It does not determine KDP compliance 
or modify the configured dimensions to satisfy KDP requirements.

### Tables

The renderer should preserve source-specified column widths as closely as possible.

When no source widths are available, columns should receive equal widths.

Relative units should be translated into appropriate LaTeX dimensions in context.

Generated `.tex` files may be manually adjusted before recompilation.

### Output constraints

The renderer returns LaTeX source as a string.

It does not write the `.tex` file, invoke LuaLaTeX, inspect the PDF, or perform KDP validation.

### Exceptions

Invalid or unsupported semantic structures and unavailable required fonts should produce a rendering error.

---

## 4.8 `kdp.py`

### Responsibility

Provide KDP-specific print requirements that can be evaluated after the PDF has been typeset.

### Public interface

```python
def get_minimum_gutter_inches(
    page_count: int,
) -> Decimal:
    """Return the minimum required gutter in inches."""
```

### Input

`page_count` is the final page count of the compiled PDF.

### Return value

A `Decimal` representing the minimum required gutter in inches.

### Gutter requirements

The initial implementation uses the following page-count ranges:

| Page count | Minimum gutter |
|---:|---:|
| 24–150 | 0.375 inches |
| 151–300 | 0.500 inches |
| 301–500 | 0.625 inches |
| 501–700 | 0.750 inches |
| 701–828 | 0.875 inches |

### Validation behavior

The function must reject page counts outside the supported range.

A `ValueError` is appropriate for an unsupported page count.

### Responsibility boundary

This module provides the minimum required gutter for a given page count.

It does not:

- Read `book.yaml`.
- Load `PrintBookConfiguration`.
- Inspect PDF files.
- Determine the PDF page count.
- Modify page margins.
- Compile LaTeX.

The pipeline compares the returned minimum with the configured inner margin 
and reports a validation failure if the configured margin is insufficient.

---

# 5. Cross-component contracts and invariants

The following contracts apply across module boundaries.

## 5.1 Configuration and semantic model are separate

`PrintBookConfiguration` describes how a book is to be built.

`Book` describes the content and semantic structure of the book.

The configuration must not be embedded in the semantic model.

## 5.2 CSS does not enter the semantic model

CSS selectors, class names, and raw CSS declarations must not appear in the semantic model.

The parser and converter must translate source-specific information into semantic 
objects and rendering properties.

## 5.3 The semantic model is renderer-independent

The semantic model must not contain LaTeX commands, package names, or renderer-specific constructs.

The renderer determines how semantic content is typeset.

## 5.4 The parser and renderer communicate through `Book`

The parser's public output is:

```python
Book
```

The renderer's principal input is:

```python
Book
```

Neither component should require internal data structures from the other.

## 5.5 Chapter and TOC counts must agree

The semantic book must contain one TOC section.

The number of TOC entries must equal the number of chapter sections.

Each TOC entry corresponds to its chapter in document order.

## 5.6 Page geometry is configured, not inferred

The renderer uses the page size and margins from the configuration.

The pipeline checks the final configured inner margin against the KDP minimum after typesetting.

The application must not silently modify the configured margin to make the book pass validation.

## 5.7 Generated LaTeX remains an intermediate artifact

The `.tex` file is a first-class build artifact.

The pipeline must retain it so that users can inspect and manually adjust the generated source.

A subsequent build may overwrite generated files in the output directory according to the build 
policy established during implementation.

---

# 6. Error-handling contract

The application should report errors at the level where they occur, while allowing the pipeline 
to present a coherent overall build failure.

The following exception categories are proposed:

| Category | Origin | Examples |
|---|---|---|
| Configuration error | `configuration.py` | Missing YAML, invalid settings, invalid section order |
| CSS error | `css_parser.py` | Malformed stylesheet, unsupported selector |
| Style conversion error | `rendering_style.py` | Unsupported or invalid CSS value |
| XHTML error | `xhtml_parser.py` | Invalid XML, missing source document |
| Rendering error | `latex_renderer.py` | Unsupported semantic structure, missing required font |
| Compilation error | `pipeline.py` | LuaLaTeX failure |
| Validation error | `pipeline.py` / `kdp.py` | Insufficient gutter |

A common application exception is proposed:

```python
class PrintBookError(Exception):
    """Base exception for print-book build failures."""
```

Component-specific exceptions may inherit from this base class.

The pipeline should preserve the original exception as the cause when wrapping errors:

```python
raise PrintBookError("Unable to build print book.") from error
```

The command-line application catches `PrintBookError` and reports it to the user.

The implementation should avoid catching broad exceptions merely to suppress them or 
continue with an invalid document.

---

# 7. Dependencies and module boundaries

The intended dependency direction is:

```text
main
  |
  v
pipeline
  |
  +----------------------------+
  |                  |         |
  v                  v         v
configuration  xhtml_parser  latex_renderer
                  |
                  +------------------+
                  |                  |
                  v                  v
              css_parser      rendering_style
                                     |
                                     v
                               semantic model

pipeline
  |
  v
kdp
```

More precisely:

| Module | May depend on |
|---|---|
| `main.py` | `pipeline.py` |
| `pipeline.py` | `configuration.py`, `xhtml_parser.py`, `latex_renderer.py`, `kdp.py` |
| `configuration.py` | Semantic/configuration types, YAML library, standard library |
| `css_parser.py` | CSS parsing library, XHTML element type, `ResolvedCssStyle` |
| `rendering_style.py` | Semantic model, configuration types |
| `xhtml_parser.py` | Configuration, CSS parser, rendering-style converter, semantic model |
| `latex_renderer.py` | Configuration, semantic model |
| `kdp.py` | Standard library |

The CSS parser and rendering-style converter are dependencies used by the XHTML parser. They 
are not independent stages in the top-level pipeline.

The semantic model should remain independent of all these modules.

---

# 8. Testing expectations

Each public interface should have tests at its own boundary.

| Module | Principal tests |
|---|---|
| `main.py` | Argument parsing, exit status, error reporting |
| `pipeline.py` | Correct component ordering, generated artifacts, compilation failure, validation failure |
| `configuration.py` | Valid configuration, missing fields, invalid measurements, section ordering, font paths |
| `css_parser.py` | Stylesheet parsing, selector matching, specificity, inheritance, cascade order |
| `rendering_style.py` | CSS-to-semantic-style conversion, units, fonts, margins, borders |
| `xhtml_parser.py` | XHTML-to-semantic-model conversion, headings, lists, tables, inline content, TOC |
| `latex_renderer.py` | Semantic-model-to-LaTeX conversion, escaping, chapter commands, fonts, tables |
| `kdp.py` | Every page-count boundary, supported and unsupported page counts |

Tests for individual modules should not require running the entire pipeline.

The pipeline should have integration tests that exercise the components together using a 
small, controlled book fixture.

The fixture should include at least:

- A title page.
- A front-matter section.
- A table of contents.
- Multiple chapters.
- A back-matter section.
- A chapter title containing a line break.
- A drop cap.
- Handwriting and SMS content.
- A block quote.
- A section break.
- A table and a list.

The test fixture's TOC entries must correspond to its chapter sections.

---

# 9. Decisions intentionally deferred

The following decisions do not need to be settled to define the public interfaces, but 
must be resolved before or during implementation.

| Decision | Reason for deferral |
|---|---|
| XHTML/XML parsing library | Determines the concrete `Element` type used by the CSS resolver |
| CSS parsing library | Determines how stylesheet rules and selectors are represented internally |
| Exact `ResolvedCssStyle` field representation | Can be selected to suit the CSS library and converter |
| CSS selector support | Should be driven by the actual source stylesheets |
| CSS inheritance and unsupported-property policy | Requires implementation-level testing against source documents |
| PDF page-count mechanism | A build concern; should be selected independently of KDP rules |
| LuaLaTeX invocation details | Includes executable discovery, working directory, logging, and compilation passes |
| Output naming and overwrite policy | Affects build behavior but not the component interfaces |
| Exact exception subclasses | Can be introduced as the implementation's error-handling needs become clear |
| CLI argument names and defaults | Can be finalized when `main.py` is implemented |

These deferred decisions should not be used as a reason to expand the public API prematurely.

---

# 10. Proposed implementation order

The modules should be implemented and tested in an order that respects their dependencies.

1. **Semantic model** — finalize the model and its invariants.
2. **Configuration** — implement and test YAML loading and validation.
3. **CSS parser** — implement stylesheet loading and cascade resolution.
4. **Rendering-style converter** — implement CSS-to-semantic-style conversion.
5. **XHTML parser** — construct the semantic `Book`.
6. **LaTeX renderer** — convert the semantic model into a complete LaTeX document.
7. **KDP rules** — implement gutter lookup and boundary tests.
8. **Pipeline** — connect the components and implement PDF compilation and validation.
9. **CLI** — expose the completed pipeline through `main()`.

The order is intended to support incremental testing. The pipeline and CLI should be implemented 
after the underlying components have stable contracts.

---

## 11. Definition of completion

The initial implementation will be considered functionally complete when:

- A valid `book.yaml` can be loaded into a typed configuration.
- All configured XHTML files can be parsed.
- The supported CSS features can be resolved.
- The parser can construct a complete semantic `Book`.
- The renderer can generate a complete LuaLaTeX-compatible document.
- LuaLaTeX can compile the generated document into a PDF.
- The final PDF page count can be determined.
- The configured inner margin can be checked against the appropriate KDP minimum.
- Errors are reported clearly without silently discarding source content.
- The generated `.tex` and PDF files are retained in the output directory.

**The principal architectural contract is:**

```text
PrintBookConfiguration
          +
       XHTML/CSS
          |
          v
          Book
          |
          v
     LaTeX source
          |
          v
          PDF
          |
          v
    KDP validation
```

The pipeline coordinates the process; each component owns its own transformation; and the 
semantic `Book` remains the stable boundary between source-document interpretation and final typesetting.