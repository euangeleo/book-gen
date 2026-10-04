# TeX Renderer Contract

## 1. Responsibility

The TeX renderer converts a fully populated semantic `Book` object into a LuaLaTeX source document.

Its inputs are:

```python
Book
PrintBookConfiguration
```

The renderer must **not**:

* parse XHTML;
* parse CSS;
* perform CSS selector matching;
* perform CSS cascading;
* interpret CSS classes;
* access the EPUB;
* calculate semantic paragraph styles;
* modify the semantic model.

Its output is a complete `.tex` source document suitable for compilation with LuaLaTeX.

A later build component may invoke LuaLaTeX to produce the PDF.

```text
Book + PrintBookConfiguration
             │
             ▼
       LatexRenderer
             │
             ▼
       complete .tex
             │
             ▼
          LuaLaTeX
             │
             ▼
            PDF
```

---

## 2. Document class and preamble

The renderer will use:

```latex
\documentclass{memoir}
```

The renderer will construct the document preamble from the requirements of the `Book` and its rendering styles.

At minimum, the renderer will need to support the packages required for:

* custom fonts;
* drop caps;
* block-specific margin adjustment;
* any other features required by the semantic model.

The currently established packages include:

```latex
\usepackage{lettrine}
\usepackage{changepage}
```

The renderer should include a package only when the generated document actually requires it, where practical.

---

## 3. Page geometry

The renderer will use the physical page and margin configuration from `book.yaml`.

The configured:

* page width;
* page height;
* top margin;
* bottom margin;
* inner margin;
* outer margin

will be translated into the `memoir` page geometry.

The **inner margin configured in `book.yaml` is authoritative for the generated document**.

The KDP minimum gutter is a validation concern rather than something that should silently alter the user's configured margin.

Therefore:

```text
book.yaml inner margin
        │
        ▼
   configuration
   validation
        │
        ├── insufficient → error/warning
        │
        └── sufficient
              │
              ▼
        TeX renderer
              │
              ▼
       memoir geometry
```

I agree with your instinct that the KDP check belongs primarily in the configuration/model-validation stage.

There is no reason for the TeX renderer to independently recalculate the KDP requirement. It should receive a valid configuration and render it.

If we want a defensive assertion in the renderer later, it should be just that—a defensive check—not a second source of KDP policy.

---

## 4. KDP gutter calculation

The renderer does **not** calculate the KDP gutter.

`kdp.py` remains responsible for:

* determining the minimum gutter based on page count;
* comparing that requirement against the configured inner margin;
* reporting an invalid configuration.

The renderer simply uses the resulting configured geometry.

One practical consequence is that the eventual pipeline will probably need to determine the final page count **before final geometry validation**, because KDP gutter requirements depend on page count.

That is a pipeline/build concern rather than a TeX-rendering concern.

---

## 5. Sections and `memoir` divisions

The `SectionType` enumeration maps to the `memoir` logical divisions as follows:

| `SectionType`       | LaTeX division |
| ------------------- | -------------- |
| `TITLE_PAGE`        | `\frontmatter` |
| `FRONT_MATTER`      | `\frontmatter` |
| `TABLE_OF_CONTENTS` | `\frontmatter` |
| `CHAPTER`           | `\mainmatter`  |
| `BACK_MATTER`       | `\backmatter`  |

The renderer will emit the appropriate division command when transitioning between divisions.

Conceptually:

```latex
\frontmatter

% title page
...

% front matter
...

% generated table of contents
...

\mainmatter

% chapter 1
...

% chapter 2
...

\backmatter

% back matter
...
```

The renderer must not assume that every section individually begins a new `memoir` division. It should emit the division command when the sequence of sections requires a transition.

---

## 6. Structural assumptions about sections

The following are explicit assumptions of the initial renderer contract:

* There is at most one `TITLE_PAGE`.
* There is at most one `FRONT_MATTER`.
* There is at most one `TABLE_OF_CONTENTS`.
* There may be multiple `CHAPTER` sections.
* There is at most one `BACK_MATTER`.
* There are no `PART`-level divisions.
* Chapters are the highest repeated structural division.
* The source books do not require `\part`, `\section`, or `\subsection` semantics.

The renderer should validate these assumptions rather than silently producing strange LaTeX if the model violates them.

---

## 7. Chapter titles

A `CHAPTER` section will correspond to a LaTeX chapter.

The chapter title will be taken from the first H1-level heading in that section.

The renderer should therefore produce something conceptually like:

```latex
\chapter*{Chapter 1\\Iris}
```

for:

```xhtml
<h1 id="Chap01" class="P_Heading_1">
    <span>
        <a id="start">Chapter 1</a><br />Iris
    </span>
</h1>
```

The renderer should **not** retain the XHTML `<br>` itself. It should receive a semantic representation of the line break.

This brings us to an important correction to the current model.

---

## 8. Line breaks need a semantic representation

The semantic model is specifically intended to be independent of XHTML and LaTeX. A literal `"<br />"` would violate that principle.

Nor would I encode it as a literal newline in `Text.text`, because a newline in source text is not necessarily a semantic line break.

I recommend adding:

```python
@dataclass(frozen=True)
class LineBreak(Inline):
    """A deliberate line break within inline content."""
```

Then the heading becomes conceptually:

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

and the TeX renderer produces:

```latex
Chapter 1\\Iris
```

This is a very small addition to the model, but it gives us the correct architecture.

The XHTML parser maps:

```html
<br />
```

→

```python
LineBreak()
```

and the TeX renderer maps:

```python
LineBreak()
```

→

```latex
\\
```

That is much cleaner than leaking either XHTML or LaTeX into `Text`.

---

## 9. Table of contents

The XHTML table of contents will **not** be reproduced literally as an EPUB-style list of links.

Instead, the renderer will generate the print book's table of contents using LaTeX's normal TOC mechanism.

The `TABLE_OF_CONTENTS` section supplies the authoritative ordered chapter titles.

The configuration/model establishes a correspondence between:

```text
TOC entry 1 ↔ Chapter 1
TOC entry 2 ↔ Chapter 2
...
```

The renderer will therefore use the TOC information to establish the chapter titles associated with the generated LaTeX chapters.

The actual page numbers will be generated by LaTeX based on the final typesetting.

This is an intentional and documented departure from literal EPUB conversion:

```text
EPUB:
    chapter title + hyperlink

Print:
    chapter title + generated page number
```

The renderer should generate the appropriate LaTeX TOC rather than attempting to preserve EPUB hyperlinks.

---

## 10. Chapter command

The current contract calls for:

```latex
\chapter*{...}
```

when rendering the chapter title.

However, there is one important consequence: **starred chapters are not automatically added to the LaTeX table of contents.**

Therefore, if we use:

```latex
\chapter*{Chapter 1\\Iris}
```

the renderer must also generate the corresponding TOC entry, conceptually:

```latex
\addcontentsline{toc}{chapter}{Chapter 1\\Iris}
```

The exact handling of the visual chapter numbering and TOC numbering should be established during implementation, but the contract should explicitly require that the generated TOC contain the chapter titles and final page numbers.

---

## 11. Length conversion

The renderer should preserve CSS-derived relative lengths wherever LaTeX provides an equivalent representation.

### `em`

A model value such as:

```python
Length(Decimal("1.2"), LengthUnit.EM)
```

should become conceptually:

```latex
1.2em
```

rather than being converted prematurely into points.

### Percentages

A value such as:

```python
Length(Decimal("50"), LengthUnit.PERCENT)
```

should be represented relative to an appropriate LaTeX width:

```latex
0.5\textwidth
```

or:

```latex
0.25\columnwidth
```

as appropriate to the rendering context.

The renderer is therefore responsible for selecting the **appropriate containing width**.

The default context will generally be:

```latex
\textwidth
```

but the renderer must allow a block to establish another appropriate context.

This is particularly important for tables and other constrained layouts.

### Absolute lengths

Existing physical units such as:

```text
pt
mm
```

are emitted using their corresponding LaTeX units.

### `px`

The model currently permits `px`, so the renderer contract should preserve it rather than silently discard it. Its eventual conversion to a physical LaTeX unit should be defined explicitly during implementation.

---

## 12. Block margins

CSS-derived block margins represented in `RenderingStyle` should be rendered using `changepage`'s `adjustwidth` environment where appropriate.

For example:

```python
RenderingStyle(
    margin_left=Length(Decimal("2"), LengthUnit.MM),
    margin_right=Length(Decimal("5"), LengthUnit.MM),
)
```

would conceptually become:

```latex
\begin{adjustwidth}{2mm}{5mm}
...
\end{adjustwidth}
```

The renderer should preserve the distinction between:

* margins;
* padding;
* paragraph spacing.

They should not all be reduced to arbitrary vertical or horizontal whitespace.

For a block whose margins require an `adjustwidth` environment, the renderer will wrap the block's content in that environment.

---

## 13. Paragraph spacing

`margin-top` and `margin-bottom` should be interpreted as block spacing rather than automatically being treated as page geometry.

The renderer should choose the appropriate LaTeX mechanism based on whether the margin affects:

* the block's horizontal extent;
* spacing before the block;
* spacing after the block.

The goal is to reproduce the source layout rather than blindly translate CSS property names into LaTeX commands.

---

## 14. `page_break_before`

For an object whose `RenderingStyle` contains:

```python
page_break_before=True
```

the renderer emits:

```latex
\clearpage
```

immediately before that object's rendering.

Thus:

```text
previous content
      ↓
\clearpage
      ↓
object with page_break_before
```

This ensures that content preceding the break is fully processed before the new page begins.

---

## 15. Drop caps

`DropCap` will use the `lettrine` package.

The renderer will generate:

```latex
\lettrine{A}{rest of the text}
```

or the equivalent appropriate construction based on the actual inline content.

The `lettrine` package is therefore a required rendering dependency whenever a `DropCap` occurs.

The renderer should treat the drop cap as a semantic inline object rather than attempting to reproduce the original CSS mechanism such as `float`.

---

## 16. Small caps

`SmallCaps` will render using:

```latex
\textsc{...}
```

The renderer may assume that a SmallCaps span does not cross a block boundary.

This is an explicit source-document assumption.

The renderer does not need to reconstruct or split SmallCaps spans across paragraphs.

---

## 17. Handwriting

The semantic model already provides:

```python
HandwritingVariant.SCRIPT
HandwritingVariant.PRINT
```

The renderer obtains the corresponding font families from the book configuration.

The rules are:

| Semantic value                | Configuration                                                       |
| ----------------------------- | ------------------------------------------------------------------- |
| `Handwriting(variant=SCRIPT)` | `fonts.handwriting.script`                                          |
| `Handwriting(variant=PRINT)`  | `fonts.handwriting.print`                                           |
| default/no variant            | `fonts.handwriting.default_variant` → corresponding configured font |

The renderer should not contain hard-coded knowledge that:

```text
script = Dancing Script
print = Johnny Mac Scrawl BRK
```

Those are configuration decisions.

---

## 18. SMS

The revised configuration contract should have:

```yaml
fonts:
  body: "Linux Libertine"
  sms: "<font-family-name>"
  handwriting:
    default_variant: print
    print: "Johnny Mac Scrawl BRK"
    script: "Dancing Script"
```

with the corresponding family name required to appear in:

```yaml
fonts.paths:
```

This follows the same architectural principle we already established: **configuration identifies the font family; configuration also maps that family to its font file.**

And the renderer should treat SMS as a semantic rendering category rather than merely assuming it is "another handwriting style." That leaves room to add other SMS-specific characteristics later.

---

## 19. Tables

There is a gap here in the current model.

Your proposed behavior is exactly what I would want:

1. If the source specifies column widths, preserve them.
2. If it doesn't, distribute columns equally.
3. Allow manual adjustment of the generated `.tex` if necessary.

But our current:

```python
class Table(Block):
    rows: list[TableRow]
```

does **not** preserve column widths.

Therefore the renderer cannot currently know whether:

```html
<td style="width: 30%">
```

was present in the EPUB.

I would add table-column information to the semantic model before implementing the renderer.

Something along these lines:

```python
@dataclass(frozen=True)
class TableColumn:
    """Rendering information for one table column."""

    width: Length | None = None
```

and:

```python
@dataclass(frozen=True)
class Table(Block):
    """Tabular content consisting of ordered rows."""

    columns: list[TableColumn] = field(default_factory=list)
    rows: list[TableRow] = field(default_factory=list)
    rendering_style: RenderingStyle | None = None
```

Then:

```text
specified source width
        ↓
TableColumn.width
        ↓
LaTeX table column specification
```

and:

```text
no source width
        ↓
TableColumn.width = None
        ↓
renderer distributes columns equally
```

This is a good example of why the semantic model should preserve **meaningful source information even when the renderer doesn't yet know what to do with it**.

---

## 20. Fonts

The renderer will use LuaLaTeX's font facilities to load configured font files.

The semantic model contains:

```python
RenderingStyle.font_family
```

not font paths.

The configuration supplies the mapping:

```text
font family
     ↓
font file
```

The renderer therefore performs the final association between semantic font-family names and configured font resources.

It should never infer a font file from a CSS name or from a hard-coded filename.

---

## 21. Escaping

All text originating in the semantic model must be safely escaped for LaTeX.

This includes characters such as:

```text
&
%
$
#
_
{
}
~
^
\
```

The renderer must distinguish between:

```text
ordinary text
```

and:

```text
renderer-generated LaTeX
```

so that user/source text can never accidentally become LaTeX syntax.

This is especially important for:

* chapter titles;
* table contents;
* SMS text;
* handwriting text;
* headings;
* ordinary paragraphs.

---

## 22. Inline rendering

The renderer should recursively render inline semantic objects.

Conceptually:

```text
Text
Italic
Bold
SmallCaps
Handwriting
SMS
DropCap
LineBreak
```

each has a dedicated rendering method.

For example:

```python
_render_text()
_render_italic()
_render_bold()
_render_small_caps()
_render_handwriting()
_render_sms()
_render_drop_cap()
_render_line_break()
```

This is preferable to one enormous `_render_inline()` method containing a large conditional tree.

---

## 23. Block rendering

Likewise, blocks should have dedicated rendering methods:

```python
_render_heading()
_render_paragraph()
_render_block_quote()
_render_section_break()
_render_list()
_render_list_item()
_render_table()
```

The renderer should recursively render nested block content.

This is particularly important for:

```python
BlockQuote
ListItem
TableCell
```

because each can contain other blocks.

---

## 24. Paragraph styles

The semantic `ParagraphStyle` remains authoritative.

The renderer translates:

```python
ParagraphStyle.NORMAL
ParagraphStyle.FIRST_INDENT
ParagraphStyle.SPACING_AFTER
ParagraphStyle.SPACING_BEFORE_AND_AFTER
ParagraphStyle.FRONT_MATTER
```

into appropriate LaTeX paragraph behavior.

The renderer should **not infer these styles again from CSS**.

By this stage:

```text
CSS
 ↓
parser
 ↓
semantic paragraph style
 ↓
renderer
```

is the intended architecture.

---

## 25. Heading levels

The initial contract assumes that the source uses H1 as the chapter heading and that the other heading levels do not represent `memoir`'s larger structural divisions.

Therefore the renderer will need an explicit mapping for the remaining heading levels.

The initial likely mapping is:

```text
H1 → chapter title
H2 → section
H3 → subsection
H4 → subsubsection
```

but **this conflicts slightly with the stated source-book assumption that the books do not use `\section`, `\subsection`, or `\subsubsection`.**

I would therefore not hard-code this yet. The renderer contract should say:

> H1 is structurally significant for chapters. H2–H4 are supported by the semantic model, but their final LaTeX structural mapping must be explicitly defined before implementation.

That prevents us from accidentally violating the source-book assumptions.

---

## 26. Output responsibility

The renderer returns a complete string:

```python
tex_source: str
```

It may also provide a convenience method such as:

```python
render_to_file(book, output_path)
```

but that should simply write the already-generated TeX source.

It should **not invoke LuaLaTeX**.

That gives us an excellent test boundary:

```python
tex = renderer.render(book)

assert "\\frontmatter" in tex
assert "\\mainmatter" in tex
assert "\\backmatter" in tex
```

without needing to compile anything.

A separate component can eventually handle:

```text
.tex → lualatex → PDF
```

---

## 27. Contract-level changes I recommend before implementation

I think we have enough information to proceed, but I would make these three changes first:

### Add `LineBreak`

```python
@dataclass(frozen=True)
class LineBreak(Inline):
    """A deliberate line break within inline content."""
```

### Add table column widths

Something like:

```python
@dataclass(frozen=True)
class TableColumn:
    width: Length | None = None
```

and add `columns` to `Table`.

### Add an SMS font to configuration

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

Those aren't renderer hacks; they're information that the renderer genuinely needs and that the semantic/configuration layers should own.

With those three adjustments, **I think the TeX renderer contract is sufficiently specified to begin implementation**. The renderer can then be a fairly clean tree-walker over `Book`, with all of the messy EPUB/CSS interpretation already behind it.
