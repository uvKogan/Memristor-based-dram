# MBMM Project Book — Typst edition

Faithful copy of `MBMM Project Book UPDATED.docx`. This is the canonical, QA-passed
copy — see `TYPST_QA_REPORT.md` in this directory for the full compile/visual-QA/
text-parity pass (compiles clean, 49 pages, 19 residual word-level diffs after
normalization, all explained tool-extraction artifacts). The pre-QA original is
archived at `../../archive/documents/MBMM_Book_Typst_preQA/`.

To compile:
- Locally: `typst compile --font-path fonts Project_Book.typ Project_Book.pdf`
  (needs the four `fonts/LiberationSerif-*.ttf` files on the font path; a local
  `typst` install won't find them automatically without `--font-path`).
- Or via typst.app: go to https://typst.app → new empty project → upload
  `Project_Book.typ`, the `media/media/*.png` images (keep the folder path
  `media/media/`), and the four `fonts/LiberationSerif-*.ttf` files (typst.app
  picks up uploaded fonts automatically) → open `Project_Book.typ`, it compiles
  to PDF.

Design choices (fidelity-first):
- All captions ("Figure 4 & 5: ...") and references [1]-[30] are literal text,
  exactly as in the docx — no auto-numbering, no live cross-refs.
- Table of Contents is generated (#outline); List of Figures / List of Tables
  are static lists built from the captions. In the docx all three are EMPTY
  (unrefreshed Word fields), so the Typst copy is strictly more complete here.
- US Letter, 1in margins, Liberation Serif 12pt (metric-compatible with Times
  New Roman — the standard academic-paper serif face; the docx original used
  Calibri, but Times New Roman/12pt is the more conventional choice for a
  research paper).

Verified against the docx: zero word-level text differences (normalized),
27/27 images byte-identical and in document order, 7/7 tables, refs to [30].
