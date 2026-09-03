# MBMM Project Book — Typst edition

`Project_Book.typ` is the **canonical, actively-maintained thesis book** (with
`Project_Book.pdf` as its compiled artifact, regenerated on every edit). It
began as a QA-verified faithful copy of `MBMM Project Book UPDATED.docx`, but
has since **deliberately diverged** through the 2026-08 review pass: 40
references (docx era ended at [30]), a new §1.3 Related Work, a rewritten
Conclusion, renamed findings ("Standby Convergence"), renumbered tables, and
many scope/caveat hardening edits. The docx is historical; do not treat it as
a parity target.

## What's in this folder

- `Project_Book.typ` / `Project_Book.pdf` — the book (source / compiled).
- `fonts/`, `media/` — required to compile (Liberation Serif + all figures).
- `Reading_Guide.md` — how to read/review the book efficiently; includes a
  15-minute self-check. **Start here if you're reviewing.**
- `Reference_Guide.md` — one-paragraph summary of all 41 references.
- `Review_Fixes_Tracker.md` — single source of truth for the 2026-08
  super-critique fix pass (all items closed) and the coordination ground
  rules for parallel workers.
- `Presentation_Outline.md`, `presentation_deck.html`,
  `Presentation_Fixes_Tracker.md` — the talk (parallel workstream).
- `NotebookLM_Podcast_Prompt.md` — ready-to-paste prompt for generating an
  audio explainer from the references.

Archived process documents (Tier-3 proposals, Conclusion rewrite draft, Lead
handoff, the original docx-conversion QA report + screenshots) live in
`../../archive/documents/book_review_pass_2026-08/`; the pre-QA original of
the book is at `../../archive/documents/MBMM_Book_Typst_preQA/`.

## To compile

- Locally: `typst compile --font-path fonts Project_Book.typ Project_Book.pdf`
  (needs the four `fonts/LiberationSerif-*.ttf` files on the font path; a local
  `typst` install won't find them automatically without `--font-path`).
- Or via typst.app: go to https://typst.app → new empty project → upload
  `Project_Book.typ`, the `media/media/*.png` images (keep the folder path
  `media/media/`), and the four `fonts/LiberationSerif-*.ttf` files (typst.app
  picks up uploaded fonts automatically) → open `Project_Book.typ`, it compiles
  to PDF.

## Design choices

- All captions and references [1]-[40] are literal text — no auto-numbering,
  no live cross-refs. Adding/removing a reference means renumbering by hand
  and syncing `Reference_Guide.md` (see the tracker's ground rules).
- Table of Contents is generated (`#outline`); List of Figures / List of
  Tables are static, hand-maintained lists (the old `GEN-BEGIN` markers were
  removed — no generator script exists).
- US Letter, 1in margins, Liberation Serif 12pt (metric-compatible with Times
  New Roman).
