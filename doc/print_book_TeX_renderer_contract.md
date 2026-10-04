# Model-to-TeX Renderer Contract

## 1. Responsibility and boundary

The renderer accepts:

* a fully parsed and semantically interpreted `Book`;
* the print-book configuration from `book.yaml`;
* KDP-related configuration/calculation support where needed.

It produces:

* a complete LuaLaTeX source document as a `.tex` file.

It does **not**:

* parse XHTML;
* parse CSS;
* perform CSS selector matching or cascading;
* interpret CSS classes;
* resolve EPUB hyperlinks;
* parse YAML;
* determine semantic structure;
* invoke LuaLaTeX itself.

The renderer should know about:

* the semantic model in `model.py`;
* `RenderingStyle`;
* print-book configuration;
* LaTeX/memoir rendering policy.

The renderer should **not** know about EPUB-specific constructs such as `.P_Heading_1` or `.P_TOC_Entry_1`.

---

## 2. `SectionType` → `memoir`

The renderer will use the following fixed mapping.

| Semantic section    | LaTeX division |
| ------------------- | -------------- |
| `TITLE_PAGE`        | `\frontmatter` |
| `FRONT_MATTER`      | `\frontmatter` |
| `TABLE_OF_CONTENTS` | `\frontmatter` |
| `CHAPTER`           | `\mainmatter`  |
| `BACK_MATTER`       | `\backmatter`  |

The renderer should emit each division command only when the corresponding division begins.

The expected ordering is:

```text
TITLE_PAGE
FRONT_MATTER
TABLE_OF_CONTENTS
CHAPTER*
BACK_MATTER
```

where `CHAPTER*` means one or more chapters.

The renderer should reject a `Book` that violates the established structural assumptions rather than silently attempting to produce something sensible.

### Source-format assumptions

The pipeline assumes:

* zero or one `TITLE_PAGE`;
* zero or one `FRONT_MATTER`;
* exactly one `TABLE_OF_CONTENTS`;
* one or more `CHAPTER` sections;
* zero or one `BACK_MATTER`;
* no `PART` equivalent;
* no `SECTION` or `SUBSECTION` equivalent in the semantic hierarchy.

Within a chapter:

* the first H1 is the chapter title;
* H2–H6 do not represent `memoir` structural divisions.

---

## 3. Chapter titles

The first H1 in each `CHAPTER` section is the chapter title.

For example:

```python
Heading(
    level=1,
    content=[
        Text("Chapter 1"),
        LineBreak(),
        Text("Iris"),
    ],
)
```

produces:

```latex
\chapter[TOC TITLE][Chapter 1]{Chapter 1\\Iris}
```

The three values have distinct sources:

### `⟨toc-title⟩`

Taken from the corresponding `TableOfContentsEntry`.

### `⟨head-title⟩`

Everything in the chapter H1 **before the first `LineBreak`**.

### `⟨title⟩`

The complete H1 content, with:

```text
LineBreak()
```

rendered as:

```latex
\\
```

Thus:

```text
Heading
├── Text("Chapter 1")
├── LineBreak()
└── Text("Iris")
```

becomes:

```latex
\chapter[
    <TOC title>
][
    Chapter 1
]{
    Chapter 1\\Iris
}
```

The source-format assumption is that the H1 contains at most the title information needed for this purpose and that the first `LineBreak()` separates the running-header title from the complete printed chapter title.

---

## 4. Table of contents

The EPUB's TOC is **source data**, not the literal printed TOC.

The semantic model should contain:

```python
@dataclass(frozen=True)
class TableOfContentsEntry:
    """One chapter entry in the print book's table of contents."""

    title: InlineContent = field(default_factory=list)
```

and:

```python
@dataclass(frozen=True)
class TableOfContents(Block):
    """The semantic table of contents for the print book."""

    heading: InlineContent = field(default_factory=list)
    entries: list[TableOfContentsEntry] = field(
        default_factory=list
    )
```

The renderer will use the TOC heading as the heading associated with the generated LaTeX TOC, but it will **not render the EPUB TOC entries as ordinary paragraphs**.

Instead, it emits:

```latex
\tableofcontents
```

and allows LaTeX to calculate the actual page numbers.

The Nth TOC entry corresponds to the Nth `CHAPTER` section.

Therefore:

```text
TOC entries = number of chapters
```

must be a validation invariant.

The TOC contains **only chapter entries**. It does not contain entries for:

* title page;
* front matter;
* back matter.

This means the EPUB TOC is being used as the authoritative source for the **display title of each chapter**, while LaTeX is responsible for generating the page numbers.

---

## 5. `LineBreak`

The semantic model should add:

```python
@dataclass(frozen=True)
class LineBreak(Inline):
    """A deliberate line break within inline content."""
```

The renderer maps:

```python
LineBreak()
```

to:

```latex
\\
```

This applies generally to inline content, although the source-format assumptions may restrict where it occurs.

---

## 6. Tables and column widths

I agree completely with the proposed model change.

Add:

```python
@dataclass(frozen=True)
class TableColumn:
    """Rendering information for one table column."""

    width: Length | None = None
```

and modify `Table` to:

```python
@dataclass(frozen=True)
class Table(Block):
    """Tabular content consisting of ordered rows."""

    columns: list[TableColumn] = field(default_factory=list)
    rows: list[TableRow] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None
```

The parser therefore preserves source information without deciding how LaTeX will use it.

### Renderer policy

If the source specifies widths:

```text
HTML/CSS width
       ↓
TableColumn.width
       ↓
LaTeX column width
```

The renderer attempts to preserve the original value and unit as closely as possible.

If no widths were specified:

```text
TableColumn.width == None
```

the renderer distributes the available table width equally among the columns.

Manual modification of the generated `.tex` remains an explicitly supported workflow.

This is particularly important: **the renderer should not try to "improve" an unspecified table layout beyond equal distribution.**

---

## 7. Length conversion

The renderer should preserve source units whenever reasonably possible.

### `pt`

Directly usable:

```latex
12pt
```

### `mm`

Directly usable:

```latex
12mm
```

### `em`

Preserve as `em`:

```latex
1.2em
```

rather than converting to points.

### `%`

Convert to an appropriate LaTeX width expression.

For example:

```text
50% of \textwidth
```

becomes:

```latex
0.5\textwidth
```

and:

```text
25% of \columnwidth
```

becomes:

```latex
0.25\columnwidth
```

The renderer must know the **appropriate reference dimension for the context** in which the percentage occurs.

The contract therefore does **not** say that every percentage is relative to `\textwidth`.

---

## 8. Page breaks

If:

```python
rendering_style.page_break_before is True
```

the renderer emits:

```latex
\clearpage
```

immediately before rendering that object.

The semantic meaning is:

> All material preceding this object must be completed before the page break occurs.

This is deliberately `\clearpage`, rather than `\newpage`.

---

## 9. Drop caps

`DropCap` is rendered using the `lettrine` package.

The generated preamble must include:

```latex
\usepackage{lettrine}
```

where the semantic model contains content requiring drop caps.

The renderer will generate the corresponding `\lettrine` command.

The renderer should not attempt to emulate the typographic effect manually.

---

## 10. Small capitals

`SmallCaps` is rendered using:

```latex
\textsc{...}
```

The source-format assumption is:

> A `SmallCaps` sequence will remain within a single block object.

This means the renderer does not need to support a small-cap span that crosses paragraph/block boundaries.

An explicitly configured font may still apply to the enclosing or containing content; the renderer should preserve the semantic distinction rather than treating `SmallCaps` as an entirely separate font family.

---

## 11. Handwriting

`Handwriting` is resolved through the print-book configuration.

The semantic object contains:

```python
HandwritingVariant.SCRIPT
```

or:

```python
HandwritingVariant.PRINT
```

or, by the existing default:

```python
HandwritingVariant.SCRIPT
```

However, the effective default is determined by `book.yaml`:

```yaml
fonts:
  handwriting:
    default_variant: print
    print: "Johnny Mac Scrawl BRK"
    script: "Dancing Script"
```

The renderer therefore follows:

```text
Handwriting with no explicit variant
        ↓
book.yaml default_variant
        ↓
configured family
```

and:

```text
Handwriting(SCRIPT)
        ↓
fonts.handwriting.script
```

```text
Handwriting(PRINT)
        ↓
fonts.handwriting.print
```

The font family is then mapped to its configured font file through:

```yaml
fonts:
  paths:
    "Dancing Script": fonts/DancingScript-Regular.otf
```

The renderer ultimately needs the font file when generating the LuaLaTeX font configuration.

A requested handwriting variant that has no configured font should be treated as a configuration/rendering error rather than silently falling back to another font.

---

## 12. SMS

The configuration will be extended to include an SMS font family:

```yaml
fonts:
  body: "Linux Libertine"
  sms: "..."
  handwriting:
    default_variant: print
    print: "..."
    script: "..."
  paths:
    ...
```

`SMS` is therefore rendered primarily by switching to the configured SMS font.

For now, no additional typographic characteristics are required.

However, the renderer should encapsulate SMS rendering in its own method rather than scattering special-case font commands throughout inline rendering. This leaves us room to add other SMS characteristics later without changing the semantic model.

---

## 13. CSS margins

CSS margins represented in `RenderingStyle` should be translated into local block margins using the `changepage` package where appropriate.

The generated preamble should therefore include:

```latex
\usepackage{changepage}
```

when required.

The renderer may produce environments conceptually equivalent to:

```latex
\begin{adjustwidth}{<left>}{<right>}
...
\end{adjustwidth}
```

This is intended to preserve the source layout as closely as practical.

The important distinction is that **margin rendering belongs to the LaTeX renderer**, not to the semantic model. The model says:

```python
margin_left=...
margin_right=...
```

and the renderer decides how LaTeX achieves that.

---

## 14. KDP gutter

The `inner` margin in `book.yaml` is the user's configured desired inner margin.

The renderer initially uses that value in the `memoir` page geometry.

The KDP minimum gutter is determined separately by `kdp.py`, according to the final typeset page count.

This creates an unavoidable two-stage process:

```text
book.yaml
    │
    ▼
generate .tex
    │
    ▼
LuaLaTeX
    │
    ▼
PDF + page count
    │
    ▼
KDP calculation
```

The renderer should therefore **not attempt to know the final KDP-required gutter before typesetting**.

After the page count is known:

1. calculate the KDP minimum gutter;
2. compare it with the configured `inner` margin;
3. if the configured margin is insufficient, issue a warning;
4. report the recommended minimum;
5. allow the generated LaTeX/PDF to exist, but clearly identify that the configuration does not currently satisfy the KDP requirement.

The user then changes `book.yaml` and reruns the pipeline.

This means the KDP validation should remain separate from ordinary LaTeX geometry generation.

---

## 15. `memoir` geometry

The renderer will generate the `memoir` document geometry from:

* configured page width;
* configured page height;
* top margin;
* bottom margin;
* inner margin;
* outer margin.

The initial geometry should use the configured values directly.

The renderer should not silently replace the configured inner margin with the KDP minimum.

Instead:

```text
book.yaml inner margin
        ↓
memoir geometry
        ↓
typeset document
        ↓
KDP validation
        ↓
warning if inadequate
```

That preserves the user's explicit configuration and makes the KDP requirement transparent.

---

## 16. Font configuration

The renderer uses the new configuration model in which:

```yaml
fonts:
  body: "Linux Libertine"
  sms: "..."
  handwriting:
    default_variant: print
    print: "..."
    script: "..."
  paths:
    "Linux Libertine": fonts/LinLibertine_R.otf
    "Dancing Script": fonts/DancingScript-Regular.otf
```

The semantic model contains **font-family names**, not font paths.

The renderer is the point where configured font families become actual LuaLaTeX font declarations.

This is an important architectural boundary:

```text
RenderingStyle
    font_family="Dancing Script"
             │
             ▼
PrintBookConfiguration
    paths["Dancing Script"]
             │
             ▼
LuaLaTeX font configuration
```

---

## 17. Output should be deterministic

For a given:

```text
Book
+
PrintBookConfiguration
```

the renderer should produce deterministic LaTeX.

In particular, it should not:

* reorder blocks;
* reorder table rows or columns;
* infer missing content;
* introduce arbitrary formatting;
* depend on Python object identity;
* depend on filesystem traversal order.

This will make generated `.tex` files suitable for version control and manual inspection.

---

## 18. Renderer interface

The public interface should be:

```python
class LatexRenderer:
    """Render a semantic print book as LuaLaTeX source."""

    def __init__(
        self,
        configuration: PrintBookConfiguration,
    ) -> None:
        ...

    def render(
        self,
        book: Book,
    ) -> str:
        """Return complete LuaLaTeX source for the book."""
        ...
```

This allows file output to remain a small concern outside the renderer:

```python
latex_source = renderer.render(book)

output_path.write_text(
    latex_source,
    encoding="utf-8",
)
```

This distinction makes the renderer substantially easier to unit test.

