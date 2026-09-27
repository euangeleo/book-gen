# Print Book YAML Configuration Contract

## 1. Purpose

The print-book YAML configuration describes the configuration required to convert one unzipped EPUB source into a particular print edition.

The YAML file is specific to one book and MUST reside in that book's print-version directory.

The configuration MUST NOT reproduce the EPUB's `content.opf` or other EPUB package metadata.

The configuration describes:

* book metadata needed by the print pipeline;
* the physical page size;
* page margins;
* gutter calculation parameters;
* fonts used by the print edition;
* handwriting-variant mappings;
* the ordered sections of the printed book;
* the XHTML source file associated with each section.

The YAML configuration MUST NOT contain the semantic representation of the book's textual content. That is produced by parsing the XHTML files into the semantic model.

---

# 2. File Location

The configuration file SHOULD be named:

```text
book.yaml
```

and SHOULD be located at the root of the print-book directory.

For example:

```text
my-book/
├── book.yaml
├── title_page.xhtml
├── frontmatter.xhtml
├── chapter-0001.xhtml
├── chapter-0002.xhtml
├── chapter-0003.xhtml
├── toc.xhtml
├── backmatter.xhtml
└── fonts/
    ├── DancingScript-Regular.otf
    └── ...
```

Paths in the YAML configuration are relative to the directory containing `book.yaml`, unless otherwise specified.

---

# 3. Book Metadata

The `book` section contains metadata needed by the print pipeline.

```yaml
book:
  title: "Book Title"
  author: "Author Name"
```

### Required properties

* `title`
* `author`

The metadata is not intended to reproduce all metadata found in the EPUB.

Additional metadata MAY be added later if required by the print pipeline.

---

# 4. Page Configuration

The `page` section defines the physical dimensions of the printed page.

Example:

```yaml
page:
  width: 6in
  height: 9in
```

Both `width` and `height` MUST be specified.

The values MUST include physical units.

Supported units SHOULD initially include:

* `in`
* `mm`
* `cm`
* `pt`

The Python configuration parser is responsible for validating these values.

The page dimensions apply to every page in the output PDF.

---

# 5. Margin Configuration

The `margins` section defines the margins of the printed book.

Example:

```yaml
margins:
  top: 0.75in
  bottom: 0.75in
  outer: 0.625in
```

The configuration distinguishes **outer margin** from the gutter/inner margin because the inner margin is affected by binding.

The initial configuration SHOULD NOT require the user to specify a final inner margin directly.

Instead, the configuration provides the parameters necessary to calculate it.

---

# 6. Gutter Configuration

The `gutter` section specifies how the binding gutter is calculated.

Example:

```yaml
gutter:
  base: 0.25in
  per_page: 0.002in
```

The final gutter MUST be calculated by the application using the final page count and the applicable print-platform specifications.

The YAML configuration therefore specifies the **parameters for the calculation**, rather than storing a fixed final gutter.

The calculation MUST be performed after the LaTeX document has been rendered sufficiently to determine the final page count, or by another mechanism that produces an equivalent reliable page count.

The configuration MUST NOT require the user to manually calculate the final gutter.

The exact gutter formula and platform-specific requirements belong to the print-rendering layer rather than to the YAML schema itself.

---

# 7. Font Configuration

The `fonts` section defines fonts that are available to the print edition.

Example:

```yaml
fonts:
  body:
    file: "fonts/BodyFont.otf"

  handwriting:
    script: "fonts/DancingScript-Regular.otf"
    print: "fonts/PrintHandwriting.otf"
```

Font paths are relative to the directory containing `book.yaml`.

The semantic model MUST refer to fonts by semantic role or variant rather than by filename.

For example:

```text
HandwritingVariant.SCRIPT
```

is mapped by configuration to:

```text
fonts/DancingScript-Regular.otf
```

The font configuration MAY contain additional roles as the project develops.

---

# 8. Handwriting Configuration

The `handwriting` section specifies how handwriting classes in the source EPUB are interpreted.

Example for an EPUB containing only script-style handwriting:

```yaml
handwriting:
  default_variant: script
```

In this configuration, the generic source class:

```text
text_Handwriting
```

is interpreted as:

```text
Handwriting(variant=script)
```

An EPUB containing only print-style handwriting may instead specify:

```yaml
handwriting:
  default_variant: print
```

---

## 8.1 Multiple Handwriting Variants

If the EPUB distinguishes multiple handwriting variants, the configuration MAY specify explicit source-class mappings.

Example:

```yaml
handwriting:
  default_variant: script

  classes:
    text_Handwriting_script: script
    text_Handwriting_print: print
```

The parser MUST use the explicit mapping when one exists.

The `default_variant` applies to the generic:

```text
text_Handwriting
```

class.

A handwriting variant referenced by the XHTML MUST have a corresponding font configuration.

---

# 9. Sections

The `sections` list defines the complete sequential structure of the printed book.

The order of entries in this list is the order in which the resulting sections MUST appear in the print book.

Example:

```yaml
sections:

  - type: front_matter
    file: frontmatter.xhtml

  - type: title_page
    file: title_page.xhtml

  - type: table_of_contents
    file: toc.xhtml

  - type: chapter
    file: chapter-0001.xhtml

  - type: chapter
    file: chapter-0002.xhtml

  - type: chapter
    file: chapter-0003.xhtml

  - type: back_matter
    file: backmatter.xhtml
```

Each section entry MUST contain:

* `type`
* `file`

The value of `type` MUST correspond to one of the semantic model's `SectionType` values:

```text
front_matter
title_page
table_of_contents
chapter
back_matter
```

The `file` value identifies the XHTML source file.

---

# 10. Chapter Metadata

A chapter MAY contain optional metadata useful to the print renderer.

For example:

```yaml
sections:

  - type: chapter
    file: chapter-0001.xhtml
    number: 1
```

However, chapter numbering SHOULD NOT be duplicated in the YAML configuration if it can be reliably obtained from the XHTML content.

Chapter-specific configuration SHOULD only be added when the print edition requires information that cannot be derived from the source XHTML.

---

# 11. Validation Requirements

The YAML parser MUST validate at least the following:

### Required configuration

* `book` exists.
* `book.title` exists.
* `book.author` exists.
* `page.width` exists.
* `page.height` exists.
* `margins` contains the required margin values.
* `gutter` contains the required calculation parameters.
* `sections` exists and is non-empty.

### Files

Every XHTML file referenced by `sections` MUST exist.

Every font file referenced by `fonts` MUST exist.

### Controlled values

Section types MUST correspond to valid `SectionType` values.

Handwriting variants MUST correspond to valid `HandwritingVariant` values.

### Handwriting

Every handwriting variant that can be produced by the XHTML parser MUST have an associated configured font.

### Physical dimensions

All physical dimensions MUST contain recognized units and MUST represent positive values.

---

# 12. Separation of Configuration and Semantic Content

The YAML configuration describes the **configuration of a print edition**.

The semantic model describes the **content of the book**.

For example, YAML may contain:

```yaml
handwriting:
  default_variant: script

fonts:
  handwriting:
    script: "fonts/DancingScript-Regular.otf"
```

while the semantic model contains:

```python
Handwriting(
    variant=HandwritingVariant.SCRIPT,
    content=[Text("handwritten text")]
)
```

The YAML configuration MUST NOT contain the textual content itself.

Similarly, the YAML configuration specifies that:

```yaml
sections:
  - type: chapter
    file: chapter-0001.xhtml
```

but the contents of `chapter-0001.xhtml` are converted into the semantic model by the XHTML parser.

---

# 13. Deliberately Excluded Configuration

The initial YAML schema does not include configuration for:

* images;
* indexes;
* cross-references;
* EPUB navigation;
* EPUB spine metadata;
* CSS rules;
* individual XHTML elements;
* LaTeX commands;
* PDF output settings unrelated to the book's print design.

These may be added later if the requirements of the project demonstrate a need for them.
