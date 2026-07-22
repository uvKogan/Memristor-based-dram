# MBMM Project Book — Typst edition

Faithful copy of `MBMM Project Book UPDATED.docx`. To compile:
1. Go to https://typst.app → new empty project.
2. Upload: `book.typ`, the `media/media/*.png` images (keep the folder path
   `media/media/`), and the four `fonts/Carlito-*.ttf` files (typst.app picks
   up uploaded fonts automatically).
3. Open book.typ → it compiles to PDF.

Design choices (fidelity-first):
- All captions ("Figure 4 & 5: ...") and references [1]-[30] are literal text,
  exactly as in the docx — no auto-numbering, no live cross-refs.
- Table of Contents is generated (#outline); List of Figures / List of Tables
  are static lists built from the captions. In the docx all three are EMPTY
  (unrefreshed Word fields), so the Typst copy is strictly more complete here.
- US Letter, 1in margins, Carlito 11pt (metric-compatible with Calibri).

Verified against the docx: zero word-level text differences (normalized),
27/27 images byte-identical and in document order, 7/7 tables, refs to [30].
