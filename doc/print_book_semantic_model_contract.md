# Print Book Semantic Model

## 1. Purpose

The semantic model is the intermediate representation between the XHTML source files and the LaTeX representation used to produce the print-ready PDF.

The model represents the **meaningful structure and formatting of the print book** rather than reproducing the EPUB's XHTML, CSS, or EPUB package structure.

The model MUST NOT depend on LaTeX-specific implementation details.

The model SHOULD preserve information from the source that may affect the printed appearance, while ignoring EPUB-specific features that are not relevant to the print edition.

The model is an ordered representation: the order of sections, blocks, and inline content MUST be preserved.

---

## 2. General Structure

A `Book` consists of an ordered sequence of `Section` objects.

```text
Book
└── Section*
    └── Block*
        └── Inline*
```

A `Section` represents a major sequential portion of the printed book, like a chapter, or the collection of back matter.

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

The `Book` object does not contain print-layout parameters such as page size or margins. Those belong to the print configuration.

---

## 4. Section

A `Section` represents a major sequential part of the book.

Each section MUST have:

* a section type
* an ordered collection of blocks (think *paragraphs*)

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

The YAML configuration determines which source file constitutes each section and its position in the book.

---

# 5. Block-Level Content

A block is a piece of content that occupies a structural position in the document.

Initial block types are:

* `Heading`
* `Paragraph`
* `BlockQuote`
* `SectionBreak`
* `List`
* `ListItem`

Additional block types may be added as needed.

---

## 5.1 Heading

A `Heading` represents a heading at a particular structural level.

The initial model supports heading levels 1–4.

A heading MUST contain:

* a heading level
* inline content

The visual appearance of a heading is determined by the print-style configuration, not by the XHTML heading element (`h1`, `h2`, etc.) alone.

The source CSS classes `P_Heading_1`, `P_Heading_2`, etc. are therefore normalized into heading levels.

---

## 5.2 Paragraph

A `Paragraph` represents ordinary paragraph-level text.

A paragraph MUST contain:

* ordered inline content
* a paragraph style

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

## 5.3 BlockQuote

A `BlockQuote` represents text that is structurally presented as a quotation.

A block quote contains an ordered collection of blocks.

Source variations such as:

```text
P_Body_Text_blockquote
P_Body_Text_Blockquote
```

MUST normalize to the same semantic `BlockQuote` type.

The exact visual treatment of a block quote belongs to the print-style configuration.

---

## 5.4 SectionBreak

A `SectionBreak` represents a deliberate break between textual sections within a larger section.

It may correspond to an EPUB element such as:

```text
P_Section_break
```

The semantic model records the existence of the break. The block associated with the break may contain text, but its printed representation is determined by the LaTeX renderer and print configuration.

---

## 5.5 List

A `List` represents an ordered or unordered list.

A list MUST contain:

* a list type
* an ordered collection of `ListItem` objects.

Initial list types:

* `ordered`
* `unordered`

---

## 5.6 ListItem

A `ListItem` represents one item within a list.

A list item contains an ordered collection of blocks.

The model does not preserve EPUB-specific indentation or CSS measurements. Those are rendering decisions.

---

# 6. Inline Content

Inline content occurs within a block and preserves the order of textual material.

Initial inline types are:

* `Text`
* `Italic`
* `Bold`
* `SmallCaps`
* `Handwriting`
* `SMS`

Additional character styles may be added as needed.

Character styles MAY be nested when the source content requires it.

For example, text MAY conceptually be both bold and italic.

The model should therefore not assume that character styles are mutually exclusive.

---

## 6.1 Text

`Text` represents ordinary unstyled textual content.

A `Text` object contains the actual Unicode text.

The model MUST preserve Unicode characters rather than converting them into LaTeX-specific representations at this stage.

---

## 6.2 Italic

`Italic` represents text that should be rendered using the book's italic text treatment.

The semantic model records the fact that text is italic.

The model does not specify how italic text is implemented in LaTeX.

---

## 6.3 Bold

`Bold` represents text that should be rendered using the book's bold text treatment.

Although bold has not necessarily appeared in every analyzed book, it is included in the initial model because it is a common and meaningful character-level distinction that may occur in future books.

---

## 6.4 SmallCaps

`SmallCaps` represents text that should be rendered using small capitals.

The semantic model records the typographic intent rather than a particular font or point size.

---

## 6.5 Handwriting

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

The actual font assigned to each variant is a print-book configuration decision.

### Source CSS Mapping

The print-book YAML configuration MUST specify how the source EPUB identifies handwriting variants.

A book in which all handwriting uses a single variant MAY specify that all occurrences of the generic EPUB class:

```text
.text_Handwriting
```

represent that variant.

For example:

```yaml
handwriting:
  default_variant: script
```

In this case:

```text
.text_Handwriting
```

is normalized to:

```text
Handwriting(variant="script")
```

A book may instead specify:

```yaml
handwriting:
  default_variant: print
```

in which case the same generic EPUB class is normalized to:

```text
Handwriting(variant="print")
```

If a book contains multiple handwriting variants, the EPUB MAY distinguish them using separate CSS classes:

```text
.text_Handwriting_script
.text_Handwriting_print
```

These are normalized directly to:

```text
.text_Handwriting_script
    → Handwriting(variant="script")

.text_Handwriting_print
    → Handwriting(variant="print")
```

The semantic model MUST NOT depend on the particular CSS class names used to identify the variants.

The actual font assigned to each handwriting variant MUST be specified by the print-book configuration.

For example:

```yaml
handwriting:
  fonts:
    script: "fonts/DancingScript-Regular.otf"
    print: "fonts/jmacscrl.ttf"
```

A book MAY define only the handwriting variants that it actually uses.

The configuration and parser SHOULD detect a reference to a handwriting variant for which no corresponding font configuration exists.

---

## 6.6 SMS

`SMS` represents text that is intentionally formatted as SMS or text-message dialogue.

The semantic model records the fact that the text is SMS-style content.

The model does not assume that SMS formatting is implemented solely through a particular font. The print renderer may use font choice, letter spacing, or other typographic properties.

---

# 7. Formatting Versus Semantics

The semantic model MUST distinguish between:

1. **what a piece of content is**, and
2. **how that content is rendered**.

For example:

```text
Handwriting
```

is semantic content.

```text
Dancing Script, 11 pt
```

is rendering configuration.

Similarly:

```text
first_indent
```

is a semantic paragraph style.

```text
0.25 inch first-line indentation
```

is a rendering parameter.

This distinction permits the same semantic book representation to be rendered with different print designs.

---

# 8. Source CSS Normalization

The XHTML parser is responsible for translating source-specific XHTML and CSS vocabulary into the semantic model.

Examples:

```text
P_Body_Text
    → Paragraph(style="normal")

P_Body_Text_First_Indent
    → Paragraph(style="first_indent")

P_Body_Text_blockquote
P_Body_Text_Blockquote
    → BlockQuote

P_Heading_1
    → Heading(level=1)

P_Section_break
    → SectionBreak

text_Handwriting
    → Handwriting(variant=<configured variant>)

text_SMS
    → SMS
```

The exact source class names MUST NOT propagate into the rest of the application unless necessary for diagnostics.

The parser SHOULD preserve source information separately when useful for error reporting or debugging.

---

# 9. Unsupported Source Content

The initial print pipeline does not support:

* images
* indexes
* cross-references
* EPUB navigation structures
* EPUB-specific metadata
* EPUB-only styling
* other content not represented by the semantic model

The parser MUST NOT silently discard unsupported content.

It SHOULD instead:

1. report the source location,
2. identify the unsupported element or feature,
3. allow the conversion process to fail or continue according to a future-defined validation policy.

---

# 10. Relationship to Print Configuration

The semantic model describes **content**.

The YAML print configuration describes **how that content is to be turned into a particular print edition**.

For example, the semantic model may contain:

```text
Handwriting(variant="script")
```

while the YAML configuration may specify:

```yaml
fonts:
  handwriting:
    script: "fonts/DancingScript-Regular.otf"
```

Likewise, the semantic model may contain:

```text
Paragraph(style="first_indent")
```

while the print configuration determines the actual indentation.

This separation is fundamental to the architecture.

---

# 11. Design Requirements

The semantic model MUST:

* preserve the order of content;
* preserve meaningful structural distinctions;
* preserve meaningful character-level formatting;
* support nested inline formatting;
* support multiple handwriting variants;
* remain independent of LaTeX;
* remain independent of EPUB package structure;
* avoid reproducing irrelevant CSS implementation details.

The semantic model SHOULD:

* be straightforward to inspect and test;
* provide useful type information to Python code;
* allow unsupported source features to be detected;
* permit different print configurations to render the same book differently.

The semantic model SHOULD NOT:

* contain page sizes;
* contain margins;
* contain gutter calculations;
* contain LaTeX commands;
* contain font file paths;
* contain EPUB file paths;
* reproduce the complete source CSS.
