# XHTML/CSS to Semantic Model Parser Contract

## 1. Purpose

The XHTML/CSS parser converts the XHTML source files of a print-book edition into the project's semantic model.

The parser is responsible for:

* reading XHTML source files;
* parsing XHTML structure and text;
* loading and interpreting the associated CSS;
* resolving CSS selectors, inheritance, and the cascade;
* identifying semantic structures such as headings, paragraphs, lists, quotations, tables, and sections;
* identifying semantic inline structures such as italic, bold, small caps, handwriting, SMS, and drop caps;
* resolving source CSS into `RenderingStyle` objects;
* preserving Unicode text and source order;
* producing the semantic representation expected by the print renderer.

The parser MUST NOT contain:

* LaTeX commands;
* `memoir` configuration;
* PDF-generation logic;
* KDP-specific rules;
* page-size or margin calculations;
* font-file loading or font installation logic;
* print-platform-specific pagination rules.

The parser produces a semantic model. Rendering that model into LaTeX is the responsibility of a later component.

---

# 2. Inputs

The parser receives:

1. one or more XHTML source files;
2. the CSS stylesheet or stylesheets referenced by those XHTML files;
3. the `PrintBookConfiguration`;
4. the semantic-model classes defined in `model.py`.

The parser MUST use the section ordering defined by the configuration when constructing the complete `Book`.

For example:

```yaml
sections:
  - type: front_matter
    file: frontmatter.xhtml

  - type: title_page
    file: title_page.xhtml

  - type: chapter
    file: chapter-0001.xhtml
```

The parser MUST process these files in this order.

The parser MUST NOT infer the overall book order from EPUB package metadata.

---

# 3. Parser Boundary

The parser sits between the source EPUB representation and the semantic model:

```text
book.yaml
    │
    ├── section files
    ├── font-family configuration
    └── handwriting configuration
             │
             ▼
       XHTML/CSS Parser
             │
             ▼
       Semantic Model
             │
             ▼
       LaTeX Renderer
             │
             ▼
           PDF
```

The parser is concerned with **what the source content means and what source styling must survive**.

The renderer is concerned with **how that semantic content is represented in the final PDF**.

---

# 4. XHTML Parsing

The parser MUST use an HTML/XML parsing library rather than attempting to parse XHTML with regular expressions.

The parser SHOULD use Beautiful Soup for initial implementation, since it is already an intended project dependency and is well suited to tolerant parsing of EPUB XHTML.

The parser MUST preserve:

* textual content;
* element order;
* nesting relationships;
* Unicode characters;
* meaningful whitespace where required by the source;
* the distinction between block-level and inline-level content.

The parser MAY normalize insignificant XHTML formatting whitespace when that whitespace does not represent textual content.

---

# 5. CSS Parsing

The parser MUST parse CSS as CSS rather than treating the stylesheet as arbitrary text.

The parser MUST support, at minimum:

* element selectors;
* class selectors;
* compound element/class selectors needed by the source books;
* descendant selectors when required by the source;
* selector groups separated by commas.

The parser SHOULD use an existing CSS parser/library rather than implementing CSS tokenization from scratch.

The initial implementation does not need to implement the entire CSS specification.

Only the CSS behavior required by the supported print books needs to be implemented.

---

# 6. CSS Selector Matching

The parser MUST determine which CSS declarations apply to each XHTML element.

For each element, the parser MUST consider:

1. matching element selectors;
2. matching class selectors;
3. matching compound selectors;
4. matching descendant selectors supported by the implementation;
5. inline `style` attributes, if present and required by the source books;
6. inherited properties from the element's ancestors.

The parser MUST apply CSS specificity and source order when multiple declarations apply to the same element.

More specific selectors MUST take precedence over less specific selectors.

When declarations have equal specificity, the declaration occurring later in the stylesheet MUST take precedence.

If inline styles are supported, an inline declaration MUST take precedence over ordinary stylesheet declarations for the same property.

The parser SHOULD isolate selector matching and cascade resolution from semantic interpretation.

For example, the parser should conceptually be able to perform:

```text
XHTML element
    ↓
matching CSS rules
    ↓
cascade resolution
    ↓
resolved CSS properties
    ↓
RenderingStyle
```

rather than having individual semantic-element parsers independently interpret CSS.

---

# 7. CSS Inheritance

The parser MUST support inheritance for CSS properties that are inheritable and relevant to the supported rendering model.

At minimum, inheritance MUST be considered for properties such as:

* `font-family`;
* `font-size`;
* `font-weight`;
* `font-style`;
* `line-height`;
* `letter-spacing`;
* `color`;
* `text-align` where appropriate to the supported source styles.

The parser MUST distinguish between:

* a property that is explicitly specified on an element;
* a property inherited from an ancestor;
* a property that has a defined initial/default value.

The resulting `RenderingStyle` SHOULD represent the effective rendering value rather than merely the declarations directly attached to the XHTML element.

For example:

```html
<div class="message">
    <p>Hello <span>world</span></p>
</div>
```

If `.message` establishes a font family and the `span` has no overriding font family, the effective rendering style of the `span` MUST retain the inherited font family.

---

# 8. Supported CSS Properties

The initial implementation MUST support only the CSS properties needed by the print books.

The supported set is:

### Typography

* `font-family`
* `font-size`
* `font-weight`
* `font-style`
* `line-height`
* `letter-spacing`

### Block layout

* `text-align`
* `text-indent`
* `margin-top`
* `margin-right`
* `margin-bottom`
* `margin-left`

### Text

* `text-transform`
* `text-decoration`
* `color`
* `background-color`

### Box

* `padding`
* `padding-top`
* `padding-right`
* `padding-bottom`
* `padding-left`
* `border`
* `border-top`
* `border-right`
* `border-bottom`
* `border-left`

### Pagination

* `page-break-before`

Additional CSS properties MUST NOT be added to the semantic model merely because they are present in an EPUB stylesheet.

A CSS property should be supported only when the print pipeline has a defined semantic/rendering behavior for it.

---

# 9. CSS Values

The parser MUST convert supported CSS values into the corresponding model values.

For example:

```css
font-size: 12pt;
```

becomes conceptually:

```python
Length(
    value=Decimal("12"),
    unit=LengthUnit.PT,
)
```

The parser MUST preserve the unit rather than prematurely converting it to another unit.

The initial supported units are:

* `em`
* `pt`
* `mm`
* `%`
* `px`

The parser MUST preserve relative units such as `em` and `%`.

Relative values MUST NOT be converted to physical dimensions until a later rendering stage if the conversion requires information unavailable to the parser.

The parser SHOULD reject unsupported units for properties whose values are required by the semantic model.

---

# 10. Font-Family Resolution

The parser MUST preserve meaningful CSS font-family names in `RenderingStyle.font_family`.

For example:

```css
font-family: "Dancing Script", sans-serif;
```

should produce a rendering requirement whose primary font family is:

```text
Dancing Script
```

The parser MUST NOT replace:

```text
Dancing Script
```

with:

```text
fonts/DancingScript-Regular.otf
```

The path to the physical font file belongs to `PrintBookConfiguration`.

The relationship is:

```text
CSS
"Dancing Script"
       │
       ▼
RenderingStyle.font_family
"Dancing Script"
       │
       ▼
book.yaml
fonts.paths["Dancing Script"]
       │
       ▼
fonts/DancingScript-Regular.otf
```

The parser therefore knows the configured font-family names but does not need to load the corresponding font files.

---

# 11. Generic CSS Font Families

CSS generic families such as:

```text
serif
sans-serif
monospace
cursive
fantasy
```

MUST NOT automatically be treated as literal local font-family names.

When a declaration contains a font stack such as:

```css
font-family: "Dancing Script", sans-serif;
```

the parser SHOULD preserve the first applicable concrete font-family name:

```text
Dancing Script
```

when that family is explicitly configured.

If a declaration contains only a generic family, the parser MAY preserve the generic family as a rendering requirement, but the mapping of that generic family to a physical font is a rendering/configuration concern.

The initial implementation SHOULD NOT invent font mappings for generic families.

---

# 12. Font Configuration Validation

When the parser encounters a concrete CSS font-family name that is required by the source content, it SHOULD verify that the family is represented in the print configuration.

For example, if the source CSS contains:

```css
font-family: "Symbola";
```

the configuration should contain:

```yaml
fonts:
  paths:
    "Symbola": fonts/Symbola.ttf
```

If a required concrete font family has no configured path, the parser MUST report a clear validation error before rendering.

The parser SHOULD distinguish this from a configured font whose file is missing.

The configuration parser already reports missing configured files as warnings.

Thus:

```text
configured family + missing file
```

and:

```text
required family + no configuration
```

are distinct validation conditions.

---

# 13. CSS Class Interpretation

CSS classes serve two different purposes and MUST NOT automatically be treated as semantic-model types.

A CSS class may provide:

1. ordinary rendering information; or
2. a semantic cue required to identify a model object.

For example:

```html
<span class="text_Handwriting">Hello</span>
```

may identify semantic handwriting content.

By contrast:

```html
<p class="P_Centre">Hello</p>
```

may primarily provide alignment information through CSS.

The parser MUST resolve CSS rendering information independently of whether a class has a semantic interpretation.

Unknown CSS classes MUST NOT automatically cause an error.

---

# 14. Semantic Block Mapping

The parser MUST convert supported XHTML block structures into the corresponding semantic-model classes.

The initial mapping is:

| XHTML/source structure        | Semantic model               |
| ----------------------------- | ---------------------------- |
| `h1`                          | `Heading(level=1)`           |
| `h2`                          | `Heading(level=2)`           |
| `h3`                          | `Heading(level=3)`           |
| `h4`                          | `Heading(level=4)`           |
| `p`                           | `Paragraph`                  |
| block quotation               | `BlockQuote`                 |
| ordered list                  | `List(list_type=ORDERED)`    |
| unordered list                | `List(list_type=UNORDERED)`  |
| list item                     | `ListItem`                   |
| table                         | `Table`                      |
| table row                     | `TableRow`                   |
| header cell                   | `TableCell(is_header=True)`  |
| body cell                     | `TableCell(is_header=False)` |
| explicit source section break | `SectionBreak`               |

The parser MAY recognize equivalent source constructs when required by the actual EPUB files.

The semantic model MUST remain independent of the particular XHTML syntax used to express the structure.

---

# 15. Heading Levels

Heading elements MUST retain their structural heading level.

For example:

```html
<h3>Chapter Title</h3>
```

becomes conceptually:

```python
Heading(
    level=3,
    ...
)
```

The parser MUST NOT convert all headings into a generic heading type.

The CSS rendering associated with the heading MUST be retained separately in its `RenderingStyle`.

This is important because different heading levels may legitimately have different CSS-defined font families or other rendering properties.

---

# 16. Paragraph Styles

Paragraphs MUST receive a semantic `ParagraphStyle` when the source provides sufficient evidence for one of the supported semantic styles.

The initial supported values are:

```text
normal
first_indent
spacing_after
spacing_before_and_after
front_matter
```

The parser MUST distinguish semantic paragraph behavior from the raw CSS selector or class name.

For example, a source class that results in:

```css
text-indent: 1em;
```

may be interpreted as:

```python
ParagraphStyle.FIRST_INDENT
```

while the corresponding resolved measurement is retained in:

```python
RenderingStyle.text_indent
```

The parser MUST NOT require the semantic model to know the original CSS class name.

If a CSS distinction affects rendering but does not correspond to one of the semantic paragraph styles, it SHOULD remain solely in `RenderingStyle`.

---

# 17. Inline Semantic Mapping

The parser MUST recognize the following semantic inline structures:

* `Italic`
* `Bold`
* `SmallCaps`
* `Handwriting`
* `SMS`
* `DropCap`

Ordinary text becomes:

```python
Text(...)
```

Inline semantic objects MAY contain other inline objects.

For example:

```text
Handwriting
    └── Text
```

or:

```text
Bold
    └── Italic
          └── Text
```

The parser MUST preserve the nesting represented by the source content when that nesting affects rendering.

---

# 18. Italic and Bold

The parser SHOULD recognize both semantic HTML/XHTML markup and CSS where necessary.

Examples include:

```html
<i>text</i>
```

```html
<em>text</em>
```

and:

```css
font-style: italic;
```

for italic.

Similarly:

```html
<b>text</b>
```

```html
<strong>text</strong>
```

and:

```css
font-weight: bold;
```

may identify bold content.

The parser SHOULD avoid producing redundant nested semantic objects when the same semantic property is expressed by both markup and CSS.

For example, an `<em>` element whose CSS also specifies `font-style: italic` should not ordinarily produce two nested `Italic` objects.

---

# 19. Small Caps

The parser MUST recognize the source representation used by the supported EPUBs for small capitals.

If small caps are expressed through CSS, the parser MUST translate the relevant source representation into:

```python
SmallCaps(...)
```

where the source semantics justify that interpretation.

The parser MUST NOT introduce a generic `CSSStyle` semantic object merely because the source uses a CSS class for small caps.

---

# 20. Handwriting

Handwriting is a semantic distinction rather than merely a font-family choice.

The parser MUST produce:

```python
Handwriting(...)
```

when the source identifies handwriting content.

The resulting object MUST retain a:

```python
HandwritingVariant
```

value.

The variant MUST be determined using the following precedence:

1. explicit source-class mapping from `book.yaml`;
2. another explicit source distinction supported by the parser;
3. `fonts.handwriting.default_variant`.

For example:

```yaml
fonts:
  handwriting:
    default_variant: print
```

means that generic handwriting content is interpreted as:

```python
HandwritingVariant.PRINT
```

The parser MUST NOT infer the semantic variant merely from the font filename.

The configured font family is represented separately through `RenderingStyle.font_family`.

---

# 21. SMS/Text-Message Content

The parser MUST recognize the source representation used by the supported EPUBs for SMS/text-message content.

It MUST produce:

```python
SMS(...)
```

rather than a generic styled inline object when the source representation identifies SMS content.

CSS properties such as:

* `font-family`;
* `letter-spacing`;
* `font-size`;
* `background-color`;

MUST be retained through the object's `RenderingStyle` where applicable.

The parser MUST NOT hard-code a particular SMS font filename.

---

# 22. Drop Caps

The parser MUST recognize the source representation used by the supported EPUBs for drop-cap text.

It MUST produce:

```python
DropCap(...)
```

when the source identifies a drop cap.

CSS properties such as:

```css
float: left;
```

MUST NOT be introduced into the semantic model merely because the EPUB uses them to implement the drop cap.

The semantic object is:

```python
DropCap(...)
```

while the rendering implementation determines how that semantic object is represented in LaTeX.

If additional CSS properties affecting the drop cap are among the supported rendering properties, they MAY be retained in `RenderingStyle`.

---

# 23. Block Quotes

A block quotation MUST become:

```python
BlockQuote(
    content=[...],
    rendering_style=...
)
```

The `BlockQuote`'s rendering style applies to the quotation as a whole.

Paragraphs contained within the quotation MUST retain their own paragraph-level formatting.

For example:

```text
BlockQuote
├── Paragraph
└── Paragraph
```

is preferred over flattening the quotation into one paragraph.

---

# 24. Lists

Ordered lists MUST become:

```python
List(
    list_type=ListType.ORDERED,
    ...
)
```

Unordered lists MUST become:

```python
List(
    list_type=ListType.UNORDERED,
    ...
)
```

Each list item MUST become a `ListItem`.

List items MAY contain multiple blocks.

For example:

```text
List
├── ListItem
│   ├── Paragraph
│   └── Paragraph
└── ListItem
    └── Paragraph
```

The parser MUST preserve list nesting when nested lists occur in the source.

---

# 25. Tables

Tables MUST be represented as first-class semantic objects.

The parser MUST preserve:

* row order;
* cell order;
* header/body distinction;
* cell content;
* applicable rendering styles.

A header cell MUST become:

```python
TableCell(
    is_header=True,
    ...
)
```

A body cell MUST become:

```python
TableCell(
    is_header=False,
    ...
)
```

The parser MUST NOT flatten tables into ordinary paragraphs.

---

# 26. Section Breaks

The parser MAY produce `SectionBreak` when the source explicitly represents a meaningful section break that needs to survive conversion.

A section break MAY contain inline content when the source uses text or symbols as the visible representation of the break.

The parser MUST distinguish a meaningful section break from ordinary XHTML formatting whitespace.

The exact visual representation belongs to the renderer.

---

# 27. RenderingStyle Construction

Every model object that has source-specific rendering information SHOULD receive a `RenderingStyle`.

The parser MUST NOT create a `RenderingStyle` merely because an XHTML element exists.

A `RenderingStyle` should contain only resolved properties relevant to the object.

For example:

```python
Heading(
    level=3,
    content=[...],
    rendering_style=RenderingStyle(
        font_family="Dancing Script",
        text_alignment=TextAlignment.CENTER,
    ),
)
```

The parser MUST NOT put CSS selectors, CSS class names, CSS property names, or raw CSS declarations into `RenderingStyle`.

---

# 28. RenderingStyle Merging

When an element receives styling from multiple sources, the parser MUST resolve the cascade before constructing its `RenderingStyle`.

For example:

```css
p {
    font-family: "Linux Libertine";
    font-size: 11pt;
}

.special {
    font-size: 12pt;
}
```

An element with:

```html
<p class="special">
```

should receive an effective style equivalent to:

```python
RenderingStyle(
    font_family="Linux Libertine",
    font_size=Length(
        value=Decimal("12"),
        unit=LengthUnit.PT,
    ),
)
```

The semantic model should not contain two competing font sizes.

---

# 29. CSS Shorthand Properties

The parser MAY support CSS shorthand properties when required by the source EPUB.

At minimum, the implementation SHOULD be able to expand the following when they occur:

* `margin`;
* `padding`;
* `border`.

For example:

```css
margin: 1em 2em;
```

should be resolved into the four corresponding margin values before constructing `RenderingStyle`.

The semantic model contains individual properties rather than CSS shorthand syntax.

Unsupported shorthand syntax SHOULD produce a warning or validation error according to whether the unsupported syntax affects required rendering.

---

# 30. Colors

Supported CSS colors MUST be represented by the model's `Color` value object.

The parser SHOULD normalize equivalent CSS color representations where practical.

For example, CSS color syntax such as:

```css
#ffffff
```

may become:

```python
Color(value="#ffffff")
```

The parser MUST NOT embed CSS-specific property names in the `Color` object.

The exact representation used by the renderer may be determined later, provided the semantic model retains sufficient information.

---

# 31. Pagination Properties

The parser MUST support:

```css
page-break-before
```

when used by the supported source books.

A value that means a page break is required MUST become:

```python
RenderingStyle(page_break_before=True)
```

The parser MUST NOT emit LaTeX commands such as:

```latex
\clearpage
```

or:

```latex
\newpage
```

Those belong to the renderer.

---

# 32. Unsupported CSS

The source EPUB may contain many CSS declarations that are irrelevant to the print edition.

The parser MUST NOT fail merely because an unused CSS property exists in the stylesheet.

For example, an unused property such as:

```css
some-selector {
    display: none;
}
```

does not require support merely because it appears in `styles.css`.

The parser SHOULD distinguish:

### Ignored CSS

A valid CSS property that is outside the initial supported rendering vocabulary and does not affect a required semantic interpretation.

This MAY be ignored with no error.

### Unsupported required CSS

A CSS property that affects content which the parser must preserve, but for which the current pipeline has no defined behavior.

This SHOULD generate a warning or validation error.

### Malformed CSS

CSS that cannot be parsed reliably.

This SHOULD generate a clear parsing error identifying the stylesheet and relevant rule.

---

# 33. Unsupported XHTML

The parser MUST distinguish unknown XHTML elements from malformed XHTML.

Unknown elements that merely provide structural wrappers MAY be ignored while their contents are recursively parsed.

For example:

```html
<div class="wrapper">
    <p>Text</p>
</div>
```

may produce the same semantic paragraph as:

```html
<p>Text</p>
```

if the `div` contributes no semantic information.

An unknown element that contains meaningful source semantics MUST NOT be silently discarded.

Unsupported structures SHOULD generate a clear warning or validation error.

---

# 34. Whitespace and Text Nodes

The parser MUST preserve meaningful textual whitespace.

It SHOULD discard whitespace introduced solely by XHTML indentation and formatting when that whitespace does not correspond to visible text.

For example:

```html
<p>
    Hello
    world
</p>
```

MUST be handled according to the source document's textual semantics rather than blindly preserving every indentation newline.

The parser MUST preserve Unicode characters exactly unless a specific normalization rule is explicitly required.

---

# 35. Source Order

The parser MUST preserve source order for:

* blocks;
* inline content;
* list items;
* table rows;
* table cells;
* nested semantic content.

No sorting based on CSS selectors, class names, or source filenames is permitted.

The only ordering imposed externally is the section ordering specified by `book.yaml`.

---

# 36. Section Construction

Each configured section MUST be converted into a semantic-model `Section`.

For example:

```yaml
- type: chapter
  file: chapter-0001.xhtml
```

becomes conceptually:

```python
Section(
    section_type=SectionType.CHAPTER,
    content=[...],
)
```

The parser MUST NOT place the XHTML filename into the semantic model.

The semantic model represents the content, not its source location.

---

# 37. Complete Book Construction

After all configured sections have been parsed, the parser MUST construct:

```python
Book(
    sections=[...],
    title=...,
    author=...,
)
```

The book title and author SHOULD be obtained from `PrintBookConfiguration.book`.

The section list MUST follow the order specified by the configuration.

The resulting `Book` MUST contain no:

* XHTML paths;
* CSS selectors;
* CSS class names as primary vocabulary;
* font-file paths;
* YAML configuration objects;
* LaTeX commands;
* KDP configuration.

---

# 38. CSS Class Names and Semantic Vocabulary

CSS class names MUST remain an implementation detail of the source parser unless a class is explicitly needed to identify semantic meaning.

The parser SHOULD NOT create semantic-model classes corresponding one-to-one with every CSS class.

For example, the following source classes do not automatically require semantic-model types:

```text
.P_Centre
.P_Right
.P_Dedication
.P_Footers
.P_ListItem
.P_Preformatted
.P_Only_Epub
.P_Only_HTML
```

If a class merely establishes alignment, spacing, indentation, or other supported rendering information, that information belongs in `RenderingStyle`.

If a class has no effect on the print representation, it may be ignored.

---

# 39. Handwriting Class Configuration

Handwriting class mappings are a special case because the source class may carry semantic information.

The parser MUST consult:

```yaml
fonts:
  handwriting:
    default_variant: ...
    classes:
      ...
```

when determining the `HandwritingVariant`.

For example:

```yaml
classes:
  text_Handwriting_script: script
  text_Handwriting_print: print
```

means:

```text
text_Handwriting_script → HandwritingVariant.SCRIPT
text_Handwriting_print  → HandwritingVariant.PRINT
```

The class name itself MUST NOT be stored in the semantic model.

---

# 40. Relationship to book.yaml

The parser MAY read configuration values required to interpret the source content.

In particular, it MAY use:

* section ordering;
* handwriting class mappings;
* handwriting default variant;
* configured font-family names;
* available font-family names for validation.

The parser MUST NOT use configuration to override source CSS distinctions that the semantic model is designed to preserve.

For example, if the source CSS distinguishes:

```css
h1 {
    font-family: "Linux Libertine";
}

h3 {
    font-family: "Dancing Script";
}
```

the parser MUST preserve those different font-family requirements.

The configuration provides the physical font files needed to render those families; it does not collapse them into a generic role such as "heading font."

---

# 41. Validation Timing

Validation SHOULD occur in stages.

### Configuration validation

Performed when `book.yaml` is loaded.

This includes:

* required configuration fields;
* section files;
* configured font paths;
* valid handwriting variants;
* configuration consistency.

### Source parsing validation

Performed while parsing XHTML/CSS.

This includes:

* malformed XHTML;
* malformed CSS;
* unsupported source structures;
* missing required font-family configuration;
* unsupported rendering requirements.

### Rendering validation

Performed by the rendering pipeline.

This includes:

* whether the configured fonts can actually be used by LuaLaTeX;
* whether the final document can be typeset;
* final page count;
* KDP-specific margin validation;
* other print-platform requirements.

The parser MUST NOT perform rendering validation.

---

# 42. Error Reporting

Parser errors SHOULD identify enough source information to make the problem diagnosable.

Where possible, an error SHOULD identify:

* XHTML filename;
* CSS stylesheet;
* CSS selector;
* XHTML element;
* CSS property;
* CSS class;
* semantic structure being constructed.

For example:

```text
chapter-0003.xhtml:
element <h3 class="ChapterTitle">:
font family "Example Font" is required by the source CSS,
but no path is configured in fonts.paths.
```

Errors SHOULD describe the source-level problem rather than exposing internal implementation details.

---

# 43. Warnings

Warnings SHOULD be used for conditions that do not necessarily prevent construction of a valid semantic model.

Examples include:

* unused CSS declarations;
* unsupported but irrelevant CSS properties;
* unknown CSS classes with no semantic effect;
* configured font files that are missing;
* source constructs that can be safely ignored.

Errors SHOULD be used when the parser cannot construct a trustworthy semantic representation.

Examples include:

* malformed XHTML preventing structural parsing;
* malformed CSS preventing reliable cascade resolution;
* a required font-family with no configured path;
* invalid semantic structure;
* unsupported content whose meaning would otherwise be lost.

---

# 44. Parser Output Contract

The parser's principal output is:

```python
Book
```

The resulting object MUST conform to the semantic model defined in `model.py`.

A successful parse MUST therefore produce a structure of the general form:

```text
Book
└── Section*
    └── Block*
        ├── Heading
        │   └── Inline*
        ├── Paragraph
        │   └── Inline*
        ├── BlockQuote
        │   └── Block*
        ├── List
        │   └── ListItem*
        ├── Table
        │   └── TableRow*
        └── SectionBreak
```

with inline structures such as:

```text
Text
Italic
Bold
SmallCaps
Handwriting
SMS
DropCap
```

nested where required by the source.

---

# 45. Separation from the LaTeX Renderer

The parser MUST NOT make decisions that belong to LaTeX rendering.

For example, the parser may produce:

```python
RenderingStyle(
    font_family="Dancing Script",
    font_size=Length(
        value=Decimal("12"),
        unit=LengthUnit.PT,
    ),
)
```

but MUST NOT decide that this means:

```latex
\fontsize{12pt}{...}\selectfont
```

Similarly, a parser result of:

```python
RenderingStyle(page_break_before=True)
```

must not become a LaTeX page-break command until the renderer processes it.

This separation permits the semantic model to be rendered by another output system in the future.

---

# 46. Initial Implementation Scope

The first working implementation SHOULD support only the constructs known to occur in the target EPUB books.

The initial implementation should prioritize:

1. XHTML section parsing;
2. headings;
3. paragraphs;
4. block quotations;
5. ordered and unordered lists;
6. tables;
7. ordinary text;
8. italic;
9. bold;
10. small caps;
11. handwriting;
12. SMS/text-message content;
13. drop caps;
14. CSS class matching;
15. CSS element matching;
16. CSS inheritance;
17. CSS cascade and specificity;
18. the supported `RenderingStyle` properties;
19. font-family resolution;
20. validation against `book.yaml`.

The implementation SHOULD NOT attempt to become a general-purpose EPUB rendering engine.

---

# 47. Design Principle

The parser should answer the following question:

> **What semantic content is present in this XHTML, and what source-defined rendering distinctions must survive into the print representation?**

It should NOT answer:

> **How should LuaLaTeX typeset this content?**

The desired transformation is therefore:

```text
EPUB XHTML + CSS
        │
        ▼
   parse structure
        │
        ▼
 resolve CSS cascade
        │
        ▼
 identify semantics
        │
        ▼
 construct RenderingStyle
        │
        ▼
   Semantic Model
```

rather than:

```text
EPUB XHTML + CSS
        │
        ▼
      LaTeX
```

This distinction is the central architectural boundary between the parser and the renderer.
