# Rendering Style Contract

## 1. Purpose

A `RenderingStyleConfiguration` specifies typographic choices that are necessary to render a semantic `Book` as a print document.

It is concerned with **how semantic content is rendered**, not with the source representation from which that content was obtained.

The rendering-style configuration must not contain XHTML elements, CSS selectors, CSS properties, or EPUB-specific terminology.

---

## 2. Font Roles

A font role identifies a typeface used for a particular semantic or typographic purpose.

### 2.1 Body Font

The `body` font is the default typeface for ordinary book text.

If no `body` font is specified, the LaTeX renderer may use its configured default font.

### 2.2 Handwriting Fonts

Handwriting fonts correspond to the `HandwritingVariant` enumeration in the semantic model.

The configuration may specify:

* a `script` handwriting font;
* a `print` handwriting font.

Either may be omitted.

If a book uses only one handwriting variant, the configuration need only provide that variant.

### 2.3 SMS Font

The `sms` font is the typeface used to render `SMS` semantic elements.

The font is independent of the semantic meaning of `SMS`; the semantic model records that content is SMS text, while the rendering configuration determines its appearance.

### 2.4 Chapter-Title Font

The `chapter_title` font is used for chapter titles when the print design specifies a typeface different from the body font.

The semantic model identifies the chapter title as a heading. The rendering configuration determines its typeface.

### 2.5 Table-of-Contents Fonts

The rendering configuration may specify separate fonts for:

* `toc_heading`: the "Table of Contents" heading;
* `toc_entry`: entries in the table of contents.

If omitted, the renderer uses the appropriate general/default font.

### 2.6 Title-Page Font

The `title_page` font is used for title-page text when a typeface different from the normal book font is required.

The exact application of this font to individual title-page elements is a rendering concern.

---

## 3. Font Identity

A font role identifies a **font by its family name**, not by its file path.

For example:

```text
"Dancing Script"
```

is a font identity.

The location of the corresponding font file is a book-specific configuration concern.

This distinction permits a font's internal family name to differ from its filename.

For example:

```text
Font family: "Johnny Mac Scrawl BRK"
File:        fonts/JMScrawl.ttf
```

---

## 4. CSS Interpretation

The CSS interpreter may inspect the EPUB's `styles.css` to determine which font family is associated with a source style.

For example:

```css
h3 {
    font-family: "Dancing Script", sans-serif;
}
```

may establish that the source's chapter-title style uses the font family:

```text
"Dancing Script"
```

The CSS interpreter resolves source-specific presentation into rendering-style information. It does not modify the semantic model merely to preserve CSS properties.

---

## 5. Font Resolution

The rendering pipeline must ultimately resolve each required font family to a local font file that can be loaded by LuaLaTeX.

Conceptually:

```text
semantic/rendering role
        ↓
font family name
        ↓
font file path
        ↓
LuaLaTeX font definition
```

For example:

```text
Handwriting(SCRIPT)
        ↓
"Dancing Script"
        ↓
fonts/DancingScript-Regular.otf
```

The rendering-style configuration should therefore be independent of the physical location of the EPUB's font files.

---

## 6. Missing Fonts

A configured font family whose corresponding font file cannot be found should be reported during configuration/content validation.

A font that is not required by the book need not be configured.

The system should distinguish between:

1. a font that is not configured because the book does not use it; and
2. a font that is configured or required but whose file cannot be found.

---