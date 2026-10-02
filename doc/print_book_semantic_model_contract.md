# Print Book Semantic Model

## 1. Purpose

The semantic model is the intermediate representation between the XHTML source files and the LaTeX representation used to produce the print-ready PDF.

The model represents the **meaningful structure, content, and rendering requirements of the print book** rather than reproducing the EPUB's XHTML, CSS, or EPUB package structure.

The model MUST NOT depend on LaTeX-specific implementation details.

The model SHOULD preserve information from the source that may affect the printed appearance, while ignoring EPUB-specific features that are not relevant to the print edition.

The model is an ordered representation: the order of sections, blocks, table content, and inline content MUST be preserved.

---

## 2. General Structure

A `Book` consists of an ordered sequence of `Section` objects.

Conceptually:

```text
Book
└── Section*
    └── Block*
        ├── Inline*
        ├── Block*
        ├── List
        │   └── ListItem*
        └── Table
            └── TableRow*
                └── TableCell*
                    └── Block*
```

A `Section` represents a major sequential portion of the printed book, such as a chapter or the collection of back matter.

Initial section types are:

* `front_matter`
* `title_page`
* `table_of_contents`
* `chapter`
* `back_matter`

Additional section types may be added if encountered in future books.

The semantic model does not require every book to contain every section type.

---

## 3. Book

A `Book` represents the complete content of one printed book.

A `Book` MUST contain:

* an ordered collection of sections.

A `Book` MAY contain:

* title
* author
* other bibliographic metadata

Bibliographic metadata should be kept separate from the textual content of the book.

The `Book` object does not contain print-layout parameters such as page size, margins, or gutter size. Those belong to the print configuration.

---

## 4. Section

A `Section` represents a major sequential part of the book.

Each section MUST have:

* a section type;
* an ordered collection of blocks.

The section type identifies the structural role of the section, not its visual appearance.

Initial section types:

### `front_matter`

Material preceding the main body of the book.

### `title_page`

The printed title page.

### `table_of_contents`

The printed table of contents.

### `chapter`

A main-text chapter.

### `back_matter`

Material following the main body of the book.

The YAML configuration determines which source material constitutes each section and its position in the book.

---

## 5. Rendering Style

`RenderingStyle` represents **resolved rendering information that must survive conversion from XHTML/CSS to the print representation**.

It is independent of CSS syntax and MUST NOT contain CSS property names or CSS selectors.

The CSS interpreter is responsible for determining the applicable CSS rules and resolving them into a `RenderingStyle`.

The LaTeX renderer is responsible for translating the `RenderingStyle` into the appropriate LaTeX representation.

A `RenderingStyle` MAY contain:

### Typography

* `font_family`
* `font_size`
* `font_weight`
* `font_style`
* `line_height`
* `letter_spacing`

### Paragraph and block layout

* `text_alignment`
* `text_indent`
* `margin_top`
* `margin_right`
* `margin_bottom`
* `margin_left`

### Text treatment

* `text_transform`
* `text_decoration`
* `foreground_color`
* `background_color`

### Box treatment

* `padding`
* `border`

### Pagination

* `page_break_before`

Only properties actually required by supported source material need to be represented.

The model SHOULD use appropriate value objects or controlled vocabularies for properties where arbitrary strings or numeric values would be ambiguous.

For example:

```text
Length
Padding
Border
Color
FontWeight
FontStyle
TextAlignment
TextTransform
TextDecoration
BorderStyle
```

CSS measurements such as `1.20em`, `10pt`, and `1.00mm` MUST NOT be reduced to bare floating-point numbers during parsing.

Their units and relevant relative values MUST be retained until they can be correctly interpreted by the rendering pipeline.

---

## 6. Relationship Between Semantics and Rendering

The semantic model MUST distinguish between:

1. **what a piece of content is**, and
2. **how that content is rendered**.

For example:

```text
Handwriting(variant="script")
```

is a semantic distinction.

A resolved rendering style might contain:

```text
font_family = "Dancing Script"
font_size = ...
```

Similarly:

```text
Paragraph(style="first_indent")
```

identifies a semantic paragraph style, while the associated `RenderingStyle` can specify the actual indentation.

The model therefore does not need to reproduce the source CSS class:

```text
P_Body_Text_First_Indent
```

nor does it need to reproduce its CSS declaration.

Instead, the parser resolves the source information into:

```text
Paragraph
    style = first_indent
    rendering_style = ...
```

---

## 7. Block-Level Content

A block is a piece of content that occupies a structural position in the document.

Initial block types are:

* `Heading`
* `Paragraph`
* `BlockQuote`
* `SectionBreak`
* `List`
* `ListItem`
* `Table`

Additional block types may be added as needed.

Where appropriate, a block MAY contain a `RenderingStyle`.

The rendering style represents the resolved source formatting that must survive conversion.

---

### 7.1 Heading

A `Heading` represents a heading at a particular structural level.

The initial model supports heading levels 1–4.

A heading MUST contain:

* a heading level;
* inline content.

A heading MAY contain:

* a `RenderingStyle`.

The heading level represents structural information.

The rendering style represents its actual typographic and layout properties.

This distinction is important because the sample EPUB CSS permits different XHTML heading levels to have different fonts, sizes, alignment, spacing, and other properties.

For example:

```css
h1 {
    font-family: sans-serif;
}

h3 {
    font-family: "Dancing Script", sans-serif;
}
```

must remain distinguishable after parsing.

The source CSS classes `P_Heading_1`, `P_Heading_2`, etc. are normalized into semantic heading levels and associated rendering styles.

The model MUST NOT assume that a heading's visual appearance can be inferred solely from its structural level.

---

### 7.2 Paragraph

A `Paragraph` represents ordinary paragraph-level text.

A paragraph MUST contain:

* ordered inline content;
* a paragraph style.

A paragraph MAY contain:

* a `RenderingStyle`.

Initial paragraph styles are:

* `normal`
* `first_indent`
* `spacing_after`
* `spacing_before_and_after`
* `front_matter`

These styles correspond to distinctions actually observed in the source EPUBs.

The model MAY gain additional paragraph styles when a future book requires them.

Source-specific class names such as:

```text
P_Body_Text
P_Body_Text_First_Indent
P_Body_Text__And__Spacing_After
P_Body_Text__And__Spacing_After__And__Spacing_Before
```

MUST NOT be exposed as the primary semantic vocabulary of the model.

---

### 7.3 BlockQuote

A `BlockQuote` represents text that is structurally presented as a quotation.

A block quote contains an ordered collection of blocks.

A block quote MAY contain a `RenderingStyle`.

The rendering style applies to the block quote as a whole.

Paragraphs contained within the block quote retain their own paragraph-level formatting.

Source variations such as:

```text
P_Body_Text_blockquote
P_Body_Text_Blockquote
```

MUST normalize to the same semantic `BlockQuote` type.

---

### 7.4 SectionBreak

A `SectionBreak` represents a deliberate break between textual sections within a larger section.

It may correspond to an EPUB element such as:

```text
P_Section_break
```

A `SectionBreak` MAY contain inline content.

The semantic model records the existence of the break. Its printed representation is determined by the LaTeX renderer and the associated rendering information.

A CSS page break is a separate concept from a semantic `SectionBreak`.

For example:

```text
SectionBreak
```

represents a meaningful break in the source content, whereas:

```text
page_break_before = true
```

represents a pagination requirement.

The two MUST NOT be conflated.

---

### 7.5 List

A `List` represents an ordered or unordered list.

A list MUST contain:

* a list type;
* an ordered collection of `ListItem` objects.

Initial list types:

* `ordered`
* `unordered`

A list MAY contain a `RenderingStyle` where the source contains list-level formatting that must be preserved.

---

### 7.6 ListItem

A `ListItem` represents one item within a list.

A list item contains an ordered collection of blocks.

A list item MAY contain a `RenderingStyle`.

The model does not preserve arbitrary EPUB CSS declarations. It preserves only rendering properties that are relevant to the print representation.

---

## 8. Tables

A `Table` represents tabular content that must be preserved in the printed book.

A table MUST contain an ordered collection of `TableRow` objects.

A `TableRow` MUST contain an ordered collection of `TableCell` objects.

A `TableCell` MUST contain an ordered collection of blocks.

A table cell MAY contain a `RenderingStyle`.

This permits distinctions such as:

```text
table header
    font_family = "Symbola"
    font_size = ...

table contents
    font_family = "Johnny Mac Scrawl BRK"
```

to survive conversion.

The semantic model should distinguish the semantic role of a header cell from an ordinary data cell rather than relying on source XHTML elements such as `th` and `td` alone.

The initial model therefore SHOULD provide a controlled cell role such as:

```text
header
body
```

Additional table semantics may be added if future books require them.

Table-specific structural information belongs in the table model rather than in generic CSS classes.

---

## 9. Inline Content

Inline content occurs within a block and preserves the order of textual material.

Initial inline types are:

* `Text`
* `Italic`
* `Bold`
* `SmallCaps`
* `Handwriting`
* `SMS`
* `DropCap`

Additional semantic inline types may be added as needed.

Character styles MAY be nested when the source content requires it.

For example, text MAY conceptually be both bold and italic.

Inline objects that represent semantic or typographic distinctions MAY contain a `RenderingStyle`.

The model should not assume that character styles are mutually exclusive.

---

### 9.1 Text

`Text` represents ordinary textual content.

A `Text` object contains the actual Unicode text.

The model MUST preserve Unicode characters rather than converting them into LaTeX-specific representations at this stage.

A `Text` object MAY have a `RenderingStyle` when the source applies a rendering distinction that does not justify a separate semantic inline type.

---

### 9.2 Italic

`Italic` represents text that should be rendered using an italic text treatment.

The semantic model records the typographic intent.

A `RenderingStyle` MAY provide additional rendering information associated with the italic text.

The model does not specify how italic text is implemented in LaTeX.

---

### 9.3 Bold

`Bold` represents text that should be rendered using a bold text treatment.

The semantic model records the typographic intent.

A `RenderingStyle` MAY provide additional rendering information associated with the bold text.

---

### 9.4 SmallCaps

`SmallCaps` represents text that should be rendered using small capitals.

The semantic model records the typographic intent rather than a particular font or point size.

A `RenderingStyle` MAY provide additional rendering information associated with the small-cap text.

---

### 9.5 Handwriting

`Handwriting` represents text that is intended to appear in a handwriting-like typeface.

The semantic model MUST support at least two handwriting variants:

* `script`
* `print`

A `Handwriting` object MUST identify its variant.

For example:

```text
Handwriting(variant="script")
Handwriting(variant="print")
```

A `Handwriting` object MAY contain a `RenderingStyle`.

The actual font family is determined from the source CSS.

The print configuration does **not** assign fonts to handwriting variants directly.

Instead, the source CSS may contain:

```css
.text_Handwriting {
    font-family: "Dancing Script";
}
```

The CSS interpreter resolves this to:

```text
font_family = "Dancing Script"
```

The print configuration then provides the local font file associated with that family.

#### Source CSS Mapping

A book in which all handwriting uses a single variant MAY specify how the generic source class:

```text
.text_Handwriting
```

is interpreted.

For example, the source may be configured so that:

```text
.text_Handwriting
    → Handwriting(variant="script")
```

or:

```text
.text_Handwriting
    → Handwriting(variant="print")
```

If a book contains multiple handwriting variants, the source MAY distinguish them using separate CSS classes such as:

```text
.text_Handwriting_script
.text_Handwriting_print
```

These are normalized to:

```text
.text_Handwriting_script
    → Handwriting(variant="script")

.text_Handwriting_print
    → Handwriting(variant="print")
```

The semantic model MUST NOT depend on the particular CSS class names used to identify the variants.

The font family itself is **not** part of the handwriting-variant configuration. It is resolved from CSS into the `RenderingStyle`.

---

### 9.6 SMS

`SMS` represents text that is intentionally formatted as SMS or text-message content.

The semantic model records the fact that the text is SMS-style content.

An `SMS` object MAY contain a `RenderingStyle`.

The model does not assume that SMS formatting is implemented solely through a particular font. The rendering style may include font family, letter spacing, or other typographic properties.

For example, source CSS such as:

```css
.text_SMS {
    font-family: sans-serif;
    letter-spacing: 0.125em;
}
```

may produce an `SMS` object with an associated rendering style containing those resolved properties.

---

### 9.7 DropCap

`DropCap` represents an initial character or characters that receive a distinct typographic treatment at the beginning of a block.

It is included because the source CSS demonstrates a distinct drop-cap treatment:

```text
font-size
line-height
height
margin-right
float
```

A `DropCap` MUST preserve the textual content of the drop cap.

A `DropCap` MAY contain a `RenderingStyle`.

The semantic model records the fact that the content is a drop cap; the rendering style records the relevant typographic properties.

The model MUST NOT expose CSS-specific implementation details such as `float: left` directly.

---

## 10. Rendering Style and Source CSS

The XHTML/CSS parser is responsible for translating source-specific XHTML and CSS into semantic objects and resolved rendering styles.

For example:

```text
h3
    +
CSS:
    font-family: "Dancing Script"
    font-weight: bold
    font-size: 1.8em
    text-align: center
```

may become conceptually:

```text
Heading
    level = 3
    rendering_style =
        font_family = "Dancing Script"
        font_weight = bold
        font_size = 1.8em
        text_alignment = center
```

The semantic model does not retain the original CSS selector or declaration.

Likewise:

```text
p.P_Body_Text_First_Indent
```

may become:

```text
Paragraph
    style = first_indent
    rendering_style =
        text_indent = 1.20em
        ...
```

This permits source CSS to remain authoritative while preventing CSS implementation details from propagating through the application.

---

## 11. Source CSS Normalization

The XHTML parser is responsible for translating source-specific XHTML and CSS vocabulary into the semantic model.

Examples:

```text
P_Body_Text
    → Paragraph(style="normal")

P_Body_Text_First_Indent
    → Paragraph(style="first_indent")

P_Body_Text__And__Spacing_After
    → Paragraph(style="spacing_after")

P_Body_Text__And__Spacing_After__And__Spacing_Before
    → Paragraph(style="spacing_before_and_after")

P_Body_Text_blockquote
P_Body_Text_Blockquote
    → BlockQuote

P_Heading_1
    → Heading(level=1)

P_Heading_2
    → Heading(level=2)

P_Section_break
    → SectionBreak

text_Handwriting
    → Handwriting(variant=<configured interpretation>)

text_SMS
    → SMS

C_Drop_Caps
    → DropCap

B_Simple_Box
    → RenderingStyle containing box properties
```

The exact source class names MUST NOT propagate into the rest of the application unless necessary for diagnostics.

The parser SHOULD preserve source information separately when useful for error reporting or debugging.

---

## 12. Font Families

Font family names are rendering information, not font resources.

The semantic model MAY contain:

```text
font_family = "Dancing Script"
```

but MUST NOT contain:

```text
fonts/DancingScript-Regular.otf
```

The local font file is a configuration/resource concern.

`book.yaml` provides the mapping between a font-family name used by the source CSS and the corresponding local font file.

For example:

```yaml
fonts:
  "Dancing Script": fonts/DancingScript-Regular.otf
```

The CSS therefore determines **which font family is required**, while the configuration determines **where that font can be found**.

The parser MUST NOT replace a specific source font choice with a generic role such as:

```text
title_page_font
chapter_title_font
toc_font
```

unless a future requirement explicitly introduces such a print-design override.

If the source CSS specifies different fonts for `h1` and `h3`, those distinctions MUST survive into their respective `RenderingStyle` objects.

---

## 13. Unsupported Source Content

The initial print pipeline does not support:

* images;
* indexes;
* cross-references;
* EPUB navigation structures;
* EPUB-specific metadata;
* unsupported EPUB-only styling;
* other content not represented by the semantic model.

The parser MUST NOT silently discard unsupported content.

It SHOULD instead:

1. report the source location;
2. identify the unsupported element or feature;
3. allow the conversion process to fail or continue according to a future-defined validation policy.

Unused CSS declarations are not themselves unsupported content. The CSS checker may identify them as unused, and the parser need not process them for a particular book.

---

## 14. Relationship to Print Configuration

The semantic model describes the **content and source-derived rendering requirements** of the book.

The YAML print configuration describes **print-edition configuration and external resources**.

For example, the semantic model may contain:

```text
Handwriting
    variant = script
    rendering_style:
        font_family = "Dancing Script"
```

while `book.yaml` may contain:

```yaml
fonts:
  "Dancing Script": fonts/DancingScript-Regular.otf
```

The CSS determines that the handwriting uses `Dancing Script`.

The YAML configuration tells the pipeline where the `Dancing Script` font file is located.

Similarly, the semantic model may contain:

```text
Paragraph
    style = first_indent
    rendering_style:
        text_indent = 1.20em
```

The model therefore retains the source-derived rendering requirement rather than requiring the renderer to rediscover it from CSS.

Print configuration such as page size, margins, gutter calculation, and other edition-specific parameters remains outside the semantic model.

---

## 15. Design Requirements

The semantic model MUST:

* preserve the order of content;
* preserve meaningful structural distinctions;
* preserve meaningful character-level formatting;
* support nested inline formatting;
* support multiple handwriting variants;
* support tables;
* support rendering styles;
* preserve source-derived rendering properties that affect the printed result;
* remain independent of LaTeX;
* remain independent of EPUB package structure;
* avoid reproducing irrelevant CSS implementation details;
* preserve Unicode text.

The semantic model SHOULD:

* be straightforward to inspect and test;
* provide useful type information to Python code;
* allow unsupported source features to be detected;
* permit different print configurations to render the same semantic book;
* use controlled vocabularies for values with a finite meaningful set of choices;
* use value objects for compound rendering concepts such as lengths, padding, and borders.

The semantic model SHOULD NOT:

* contain page sizes;
* contain margins that belong to the overall print edition;
* contain gutter calculations;
* contain LaTeX commands;
* contain font file paths;
* contain EPUB file paths;
* contain CSS selectors;
* contain source CSS class names as its primary vocabulary;
* reproduce the complete source CSS;
* implement the CSS cascade itself.
