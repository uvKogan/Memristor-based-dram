# MBMM Project Book - Typst edition

There are now two books. `Project_Book.typ` is the short, reader-facing
project book: 24 printed pages (25 sheets), Chapters 1-6 (Introduction,
Method, "What the pipeline taught me," Results, Discussion, Conclusion and
Future Work), Figures 1-6, Tables 1-9, 48 references. It reviewed with 336
numeric claims traced to source with zero mismatches (2026-09-23). Two
conventions run through it that are worth knowing before you read it: every
number is labelled **media** (what this project's own simulated ReRAM/PCM
produces) or **device** (a real, measured, published part), never blended
silently into one number; and results for the cell write pulse are reported
as **a bracket** - a default-mode value and a bounding-mode value (the pulse
excluded versus included on the request path) rather than one single
number, because which branch a write takes depends on the workload.
`Technical_Report.typ` is the **complete technical report and knowledge
base** of the project (with `Technical_Report.pdf` as its compiled artifact,
regenerated on every edit): 122 pages, 100 references, the full detail
behind every number the short book had to compress or cut, including
Section 3.4 (Near and Far Memory - not in the short book at all), the
"Bit errors and error correction" subsection (design-point BER answer),
the write-pulse bounding-run subsection (Table 9), Table 10 (device
reference row) and Figure 28. `Technical_Report.typ` began as a QA-verified
faithful copy of `MBMM Project Book UPDATED.docx`, but
has since **deliberately diverged** through the 2026-08 review pass: 40
references (docx era ended at [30]), a new §1.3 Related Work, a rewritten
Conclusion, renamed findings ("Standby Convergence"), renumbered tables, and
many scope/caveat hardening edits. The docx is historical; do not treat it as
a parity target.

## What's in this folder

- `Project_Book.typ` / `Project_Book.pdf` - the short, reader-facing project
  book (source / compiled). **Start here if you're new to the project.**
- `Technical_Report.typ` / `Technical_Report.pdf` - the complete technical
  report and knowledge base (source / compiled).
- `fonts/`, `media/` - required to compile (Liberation Serif + all figures).
- `Reading_Guide.md` - how to read/review the document set efficiently;
  includes a 15-minute self-check. **Start here if you're reviewing.**
- `Reference_Guide.md` - one-paragraph summary of all 100 references cited
  in `Technical_Report.typ` (`Project_Book.typ` has its own, separate,
  independent 48-reference numbering).
- `research_notes/reviewer_notes_golander_2026-09.md` - how an outside
  reviewer's informal system-level suggestions (near versus far memory,
  media-versus-device honesty, the BER question) were checked against
  primary sources before shaping Section 3.4 and the bit-errors subsection;
  `research_notes/` also holds the working notes behind other corrections
  (leakage, timebase, endurance) folded into the 2026-09 revision.
- `Review_Fixes_Tracker.md` - single source of truth for the 2026-08
  super-critique fix pass (all items closed) and the coordination ground
  rules for parallel workers. `Revision_Workflow_2026-09.md` is the live
  tracker and session log for the 2026-09 revision and the short-book plan.
- `Presentation_Outline.md`, `presentation_deck.html`,
  `Presentation_Fixes_Tracker.md` - the talk (parallel workstream).
- `NotebookLM_Podcast_Prompt.md` - ready-to-paste prompt for generating an
  audio explainer from the references.

The frozen datasets behind the 2026-09 revision's numbers live under
`../../results/` (repo root), not in this folder - notably
`results/system_rev2026-09_writepulse/` (the write-pulse bounding run behind
Table 9, with its own `_csv/` and `run_manifest.json`) alongside the primary
matrix and the sensitivity-run datasets referenced throughout both books.

Archived process documents (Tier-3 proposals, Conclusion rewrite draft, Lead
handoff, the original docx-conversion QA report + screenshots) live in
`../../archive/documents/book_review_pass_2026-08/`; the pre-QA original of
the book is at `../../archive/documents/MBMM_Book_Typst_preQA/`.

## To compile

- Locally: `typst compile --font-path fonts Technical_Report.typ Technical_Report.pdf`
  (needs the four `fonts/LiberationSerif-*.ttf` files on the font path; a local
  `typst` install won't find them automatically without `--font-path`). The
  same command with `Project_Book.typ Project_Book.pdf` compiles the short
  book.
- Or via typst.app: go to https://typst.app → new empty project → upload
  `Technical_Report.typ` (or `Project_Book.typ`), the `media/media/*.png` and
  `media/short_book/*.png` images (keep the folder paths), and the four
  `fonts/LiberationSerif-*.ttf` files (typst.app picks up uploaded fonts
  automatically) → open the `.typ` file, it compiles to PDF.

## Design choices

- All captions and references are literal text - no auto-numbering, no live
  cross-refs. `Technical_Report.typ` runs [1]-[100]; `Project_Book.typ` has
  its own, separate [1]-[48]. Adding/removing a reference in either book
  means renumbering by hand within that book and, for `Technical_Report.typ`,
  syncing `Reference_Guide.md` (see the tracker's ground rules).
- Table of Contents is generated (`#outline`); List of Figures / List of
  Tables are static, hand-maintained lists (the old `GEN-BEGIN` markers were
  removed - no generator script exists).
- US Letter, 1in margins, Liberation Serif 12pt (metric-compatible with Times
  New Roman).
