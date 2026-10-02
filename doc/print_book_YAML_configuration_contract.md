# Print Book YAML Configuration Contract

## 1. Purpose

The print-book YAML configuration describes the configuration required to convert one unzipped EPUB source into a particular print edition.

The YAML file is specific to one book and MUST reside in that book's print-version directory.

The configuration MUST NOT reproduce the EPUB's `content.opf` or other EPUB package metadata.

The configuration describes:

* book metadata needed by the print pipeline;
* the physical page size;
* page margins;
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
    ├── JMScrawl.ttf
    ├── LinLibertine_R.otf
    └── Symbola.ttf
```

Paths in the YAML configuration are relative to the directory containing `book.yaml`, unless otherwise specified.

---

# 3. Book Metadata

The `book` section contains metadata needed by the print pipeline.

Example:

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

The `margins` section defines the desired physical margins of the printed book.

Example:

```yaml
margins:
  top: 0.75in
  bottom: 0.75in
  inner: 0.5in
  outer: 0.625in
```

The following properties MUST be specified:

* `top`
* `bottom`
* `inner`
* `outer`

All values MUST include physical units.

The `inner` margin is the margin adjacent to the binding/spine. The `outer` margin is the margin adjacent to the outside edge of the page.

The `inner` margin applies to the binding side of both left-hand and right-hand pages. The LaTeX renderer MUST use the appropriate physical margin on each page when producing a two-sided document.

## 5.1 KDP Minimum Inner Margin

The configured `inner` margin represents the desired **final physical inner margin** for the print edition.

It MUST NOT be smaller than the minimum required by the selected print platform.

For KDP output, the application MUST determine the minimum required inner margin from the final page count using the KDP-specific rules implemented in `kdp.py`.

The KDP page-count-dependent rules MUST NOT be duplicated in each book's YAML configuration.

For example, if a book has 276 pages and KDP's applicable minimum inner margin is 0.5in, then:

```yaml
margins:
  inner: 0.5in
```

is valid, while:

```yaml
margins:
  inner: 0.375in
```

is invalid for that KDP edition.

The configuration parser MAY validate that the margin values are physically valid. Validation of the `inner` margin against page-count-dependent platform requirements belongs to the print-platform validation layer.

The KDP-specific gutter requirements SHOULD be encapsulated by the KDP implementation rather than exposed as per-book configuration parameters.

## 5.2 Physical Margin Requirements

All margin values MUST be positive.

The configured `inner` margin SHOULD be greater than or equal to the configured `outer` margin unless a particular print specification explicitly permits otherwise.

The margin configuration describes the **final physical margins**, rather than the LaTeX commands used to produce them. The translation into `memoir`/LuaLaTeX configuration belongs to the rendering layer.

## 5.3 Page Count and Margin Validation

The final page count cannot necessarily be known before typesetting. Consequently, validation of page-count-dependent platform requirements MUST occur as part of the PDF-generation process, after a reliable final page count is available.

The book configuration MUST NOT require the user to calculate a page-count-dependent gutter manually.

The KDP-specific minimum-margin rules MUST be implemented independently of the book configuration so that the same book configuration can be validated or rendered for different print platforms in the future.

---

# 6. Font Configuration

The `fonts` section defines the font families used by the print edition and maps those font-family names to local font files.

Example:

```yaml
fonts:
  body: "Linux Libertine"

  handwriting:
    default_variant: print
    print: "Johnny Mac Scrawl BRK"
    script: "Dancing Script"

  paths:
    "Dancing Script": fonts/DancingScript-Regular.otf
    "Johnny Mac Scrawl BRK": fonts/JMScrawl.ttf
    "Symbola": fonts/Symbola.ttf
    "Linux Libertine": fonts/LinLibertine_R.otf
```

The configuration makes a deliberate distinction between:

1. a **font-family name**, which is the identity used by the semantic/rendering model; and
2. a **font file path**, which tells the rendering system where that font is installed for the print build.

The font-family name MUST correspond to the name used by the source CSS when a specific source font is required.

The font file path MUST be relative to the directory containing `book.yaml`, unless otherwise specified.

The `paths` mapping MUST contain a path for every concrete font family explicitly specified elsewhere in the configuration.

For example:

```yaml
fonts:
  body: "Linux Libertine"
```

requires:

```yaml
fonts:
  paths:
    "Linux Libertine": fonts/LinLibertine_R.otf
```

The configuration MUST NOT use font filenames as semantic font identifiers.

The semantic model and rendering pipeline SHOULD refer to:

```text
Linux Libertine
```

rather than:

```text
LinLibertine_R.otf
```

## 6.1 Body Font

The `body` property specifies the default body font family for the print edition.

For example:

```yaml
fonts:
  body: "Linux Libertine"
```

The body font provides the print edition's default typeface where no more specific font family is supplied by the source styling.

An explicitly specified font family in the source CSS MUST take precedence over this default.

The `body` property is therefore a default, not a replacement for CSS-specific font-family information.

## 6.2 Font Paths

The `paths` mapping associates a font-family name with the local font file used to render that family.

For example:

```yaml
paths:
  "Linux Libertine": fonts/LinLibertine_R.otf
  "Dancing Script": fonts/DancingScript-Regular.otf
  "Johnny Mac Scrawl BRK": fonts/JMScrawl.ttf
  "Symbola": fonts/Symbola.ttf
```

Font-family names in `paths` MUST be unique.

The configuration parser MUST resolve each configured path relative to the directory containing `book.yaml`.

A configured font path SHOULD be validated during configuration loading.

If a configured font file does not exist, the configuration parser SHOULD issue a warning rather than necessarily failing configuration loading.

Later content validation or rendering validation MAY treat a missing font file as an error when that font is actually required by the book.

The configuration parser SHOULD return the resolved font path as a `Path` value when exposing font configuration to the rest of the application.

## 6.3 CSS Font-Family Names

The source CSS is authoritative for specific font-family choices.

For example, if the source CSS contains:

```css
h3 {
    font-family: "Dancing Script", sans-serif;
}
```

the parser MUST preserve:

```text
Dancing Script
```

as the font-family requirement in the semantic model's `RenderingStyle`.

The YAML configuration provides the local file required to render that family:

```yaml
paths:
  "Dancing Script": fonts/DancingScript-Regular.otf
```

The YAML configuration MUST NOT replace CSS-specific font choices with role-based mappings such as:

```yaml
title_page:
  font: ...
chapter_title:
  font: ...
```

Such role-based font configuration is outside the initial schema.

---

# 7. Handwriting Configuration

The `handwriting` section specifies the font-family associated with each supported handwriting variant.

The initial supported variants are:

* `script`
* `print`

Example:

```yaml
fonts:
  handwriting:
    default_variant: print
    print: "Johnny Mac Scrawl BRK"
    script: "Dancing Script"
```

The values of `print` and `script` are **font-family names**, not font file paths.

The corresponding font files are specified in `fonts.paths`:

```yaml
fonts:
  handwriting:
    default_variant: print
    print: "Johnny Mac Scrawl BRK"
    script: "Dancing Script"

  paths:
    "Johnny Mac Scrawl BRK": fonts/JMScrawl.ttf
    "Dancing Script": fonts/DancingScript-Regular.otf
```

This permits the semantic model to retain the distinction:

```python
HandwritingVariant.PRINT
```

versus:

```python
HandwritingVariant.SCRIPT
```

while leaving the actual font-family choice to configuration.

## 7.1 Default Handwriting Variant

`default_variant` MUST specify the variant used when the XHTML identifies handwriting without specifying a more specific variant.

For example:

```yaml
fonts:
  handwriting:
    default_variant: print
    print: "Johnny Mac Scrawl BRK"
```

This configuration supports an EPUB containing only one kind of handwriting.

A configuration MAY instead specify:

```yaml
fonts:
  handwriting:
    default_variant: script
    script: "Dancing Script"
```

The parser MUST NOT require both `script` and `print` font families merely because the semantic model supports both variants.

A variant only needs to be configured when that variant can actually be produced by the source XHTML or is explicitly configured for use by the book.

## 7.2 Multiple Handwriting Variants

If the EPUB distinguishes multiple handwriting variants, the configuration MAY specify both:

```yaml
fonts:
  handwriting:
    default_variant: script
    print: "Johnny Mac Scrawl BRK"
    script: "Dancing Script"
```

The parser MUST use the explicitly identified variant when the XHTML provides one.

The `default_variant` applies when the XHTML identifies handwriting without providing a more specific variant.

The font-family associated with every handwriting variant that can be produced by the XHTML MUST have a corresponding entry in `fonts.paths`.

## 7.3 Handwriting Source-Class Mappings

If the XHTML uses distinct source classes for handwriting variants, the configuration MAY specify explicit mappings.

Example:

```yaml
fonts:
  handwriting:
    default_variant: script

    classes:
      text_Handwriting_script: script
      text_Handwriting_print: print

    script: "Dancing Script"
    print: "Johnny Mac Scrawl BRK"
```

The parser MUST use an explicit class mapping when one exists.

The generic source class:

```text
text_Handwriting
```

MUST use `default_variant`.

The source CSS remains authoritative for the actual font-family when the CSS directly specifies one.

The handwriting configuration identifies the semantic variant and its configured default family; it does not replace a specific CSS font-family declaration.

---

# 8. Sections

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

# 9. Chapter Metadata

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

# 10. Validation Requirements

The YAML parser MUST validate at least the following.

### Required configuration

* `book` exists.
* `book.title` exists.
* `book.author` exists.
* `page.width` exists.
* `page.height` exists.
* `margins.top` exists.
* `margins.bottom` exists.
* `margins.inner` exists.
* `margins.outer` exists.
* `fonts` exists.
* `fonts.body` exists.
* `fonts.paths` exists.
* `sections` exists and is non-empty.

### Files

Every XHTML file referenced by `sections` MUST exist.

Every font file explicitly configured in `fonts.paths` SHOULD be checked for existence.

A missing configured font file SHOULD produce a warning during configuration loading. A later validation stage MAY promote the missing file to an error if the font is required by the book.

### Font configuration

Every font-family name referenced by:

* `fonts.body`;
* `fonts.handwriting.print`;
* `fonts.handwriting.script`;
* other explicitly configured font-family settings;

MUST have a corresponding entry in `fonts.paths`.

Every font-family name in `fonts.paths` MUST identify a local font file.

### Controlled values

Section types MUST correspond to valid `SectionType` values.

Handwriting variants MUST correspond to valid `HandwritingVariant` values.

### Handwriting

`fonts.handwriting.default_variant` MUST specify a valid handwriting variant.

Every handwriting variant that can be produced by the XHTML parser MUST have an associated configured font-family.

Every such font-family MUST have an entry in `fonts.paths`.

### Physical dimensions

All physical dimensions MUST contain recognized units and MUST represent positive values.

### KDP-specific validation

Validation of the configured `margins.inner` against KDP's page-count-dependent minimum requirements MUST be performed by the KDP-specific validation layer, implemented in `kdp.py`.

The YAML configuration parser MUST NOT contain the KDP page-count table itself.

---

# 11. Separation of Configuration and Semantic Content

The YAML configuration describes the **configuration of a print edition**.

The semantic model describes the **content of the book**.

For example, YAML may contain:

```yaml
fonts:
  handwriting:
    default_variant: script
    script: "Dancing Script"

  paths:
    "Dancing Script": fonts/DancingScript-Regular.otf
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

The semantic model retains the font-family name through `RenderingStyle` where that information is relevant. The path to the physical font file remains configuration/rendering information and MUST NOT be placed in the semantic model.

---

# 12. Deliberately Excluded Configuration

The initial YAML schema does not include configuration for:

* images;
* indexes;
* cross-references;
* EPUB navigation;
* EPUB spine metadata;
* CSS rules;
* individual XHTML elements;
* LaTeX commands;
* CSS selector-to-semantic-object mappings;
* page-count-dependent KDP gutter tables;
* fixed gutter calculation parameters;
* PDF output settings unrelated to the book's print design.

These may be added later if the requirements of the project demonstrate a need for them.
