# Typst Book — Compile, Visual QA, and Fidelity Re-Verification Report

Working copy: `documents/MBMM_Book_Typst/` (produced from a copy of the original,
pre-QA `book.typ`; this QA pass ran before the directory reorganization described
below, back when the working copy was still named `MBMM_Book_Typst_QA/` and the
untouched original was `documents/MBMM_Book_Typst/`).

**Post-QA update (2026-07-22):** this directory has since been promoted to the
canonical `documents/MBMM_Book_Typst/` — the pre-QA original that this report
compares against has been moved to `archive/documents/MBMM_Book_Typst_preQA/`
(nothing was deleted; see `archive/README.md`).

## 0. Toolchain notes (environment had none of the suggested tools pre-installed)

The sandbox had no `typst`, `pandoc`, `pdftotext`/`pdftoppm` (poppler), `LibreOffice`, or
`cargo`/root access. Substitutions used, all installed without root:

| Needed | Used instead | Why |
|---|---|---|
| `typst compile` | `typst` 0.15.1 static `x86_64-unknown-linux-musl` binary from the GitHub release page | No cargo/rustc, no root for apt |
| `pdftoppm` (page→PNG) | `PyMuPDF` (`fitz`), pip-installed to a local target dir | No poppler-utils, no root |
| `pdftotext` | `PyMuPDF` `.get_text()` | Same |
| `pandoc -t plain` (docx→text) | `python-docx`, walking body paragraphs+tables in document order | No pandoc binary reachable; pip-installable |
| LibreOffice/Word (docx→PDF for pixel side-by-side) | **not available** — no LibreOffice, no root to install it | Substituted with direct visual inspection of the compiled PDF plus targeted `python-docx`/XML checks against the source docx wherever a rendering anomaly was suspected |

Caveat this creates: `python-docx` does not extract Word OMML equation objects as
text (it sees an embedded object, not characters), so a few equation-heavy spots
(resistance targets, cell-area formulas) show as "missing" on the docx side of the
parity diff even though they render correctly in the PDF (verified visually — see
§3). This is noted explicitly in §4 rather than hidden.

## 1. Compile

**Zero syntax/compile errors on the first attempt.** `typst compile --font-path fonts
book.typ book.pdf` exits 0 with empty stderr, both before and after all fixes below.
49 pages, unchanged by any fix (all fixes are local reflows/styling, not content
insertions/deletions). No fixes were needed at the compile-error level — every issue
found in this pass was a *visual/rendering* defect that compiled silently.

## 2. Visual QA — issues found and fixed

All are Typst-mechanics/styling changes; no wording, numbers, captions, or order
were touched anywhere in this pass. Screenshots for the top 5 are in
`qa_screenshots/` (`issueN_before_*.png` / `issueN_after_*.png`).

### Issue 1 — Image torn from its caption across a page break (Figure 7, and latently every figure)
`#image(...)` and its `#strong[Figure N: ...]` caption were two independent flow
items; nothing stopped a page break from landing between them. It did, for Figure 7
(image on p.16, caption orphaned onto p.17 above unrelated text).
**Fix:** wrapped each of the 20 image(-run)+caption groups in `#block(breakable:
false)[...]`, pairing the *caption with its immediately preceding image* (not the
whole multi-image run — two of the combined figures use two 4.68"-tall images whose
combined height alone exceeds the ~9" text column, so wrapping both images with the
caption would have made the block un-fittable on any page; wrapping only the last
image + caption keeps every group ≤ 5.4" while still guaranteeing no caption is ever
orphaned). Screenshots: `issue1_*_fig7_*_p17.png`.

### Issue 2 — Table header row didn't repeat across a page break (Table 5, p.25→26)
All 7 tables built their header row as plain bold cells (`[#strong[...]]`), not
`table.header(...)`. When a table split across pages (Table 5, the only one long
enough to do so), page 2 started with bare data rows and no column labels.
**Fix:** converted the first *N* cells (N = column count) of all 7 tables to
`table.header(...)` so the header now repeats automatically on continuation pages.
Verified for Table 5 (p.25→26).

### Issue 3 — `#blockquote` invisible when nested inside a list (§2.2, 4 instances)
`#let blockquote(body) = quote(block: true, body)` does have a default indent/pad —
but only at top level. Nested inside a `- ` list item (as all 4 §2.2 blockquotes are:
`- #blockquote[...]`), that padding is absorbed by the list layout and the quote
renders identically to a plain bullet, with no visual distinction at all. The docx
confirms these 4 paragraphs really do carry an extra ~0.81" indent beyond their
sibling bullets (`paragraph_format.left_indent` = 742950 EMU vs. `None` for
neighboring items) — i.e. losing the distinction is a real fidelity regression, not
a non-issue.
**Fix:** rewrote `blockquote` to add an explicit left border + inset directly on a
`block(...)`, independent of nesting context:
```typst
#let blockquote(body) = block(
  inset: (left: 1.2em, top: 0.3em, bottom: 0.3em),
  stroke: (left: 2pt + luma(160)),
  quote(block: true, body)
)
```
Confirmed correct both nested (§2.2, p.6) and top-level (§4.3 repo link, p.43).

### Issue 4 — Two section headings truncated mid-title, remainder spilled into body text (§3.1, §3.2)
Typst heading markup (`== ...`) ends at the physical newline unless the line ends
inside an *open* bracket. Two headings were pandoc-wrapped across two source lines
with the `#strong[...]` already closed on line 1:
```
== 3.1. #strong[Granular Workload Diagnostics] (Latency & Power Bar
Charts)
```
— so "Charts)" silently became a new, un-headed body paragraph, and the
auto-generated `#outline()` TOC entry was truncated identically (confirmed:
pre-fix TOC read "...Granular Workload Diagnostics (Latency & Power Bar" with no
"Charts)"). Same bug hit §3.2 ("...Memory Level Parallelism]" / "(Pareto
Frontiers)"). A third instance (§3.1.6) happened to have its `#strong[...]`
bracket still open across the line break, so it already rendered fully — joined it
too for source consistency, no visible change.
**Fix:** joined all three headings onto single source lines. TOC now reads
"3.1. Granular Workload Diagnostics (Latency & Power Bar Charts)" and "3.2.
Architectural Scaling & Memory Level Parallelism (Pareto Frontiers)" in full.

### Issue 5 — Stray bullet injected mid-sentence (§3.1.6, 2 instances)
Two parenthetical " *- clause -* " dashes happened to land as the first two
characters of a wrapped source line:
```
modes that bounded which conclusions this evaluation could honestly draw
- across the ReRAM configurations, the metrics pipeline, and both
non-ReRAM baselines.
```
Typst parsed the line-initial `- ` as a new list item, so the sentence split into
prose + an orphaned one-item bullet + more prose. Confirmed against the docx: this
is one continuous sentence with a plain em-dash-style parenthetical, no list
intended.
**Fix:** escaped the two leading hyphens (`\-`) so they render as literal text.
Searched the rest of the document for the same pattern (line starts with `- `,
previous line is non-blank prose) — the only two other matches (found the same way
by this same scan) are exactly these two; every other `- ` line-start is a genuine,
correctly-intended list item.

### Issue 6 — Reference [25] URL and a general "long-token-after-multi-line-paragraph" Typst quirk
Reference [25]'s citation, split across 5 raw source lines ending in an unusually
long (236-char) unbroken URL, rendered with a spurious paragraph-sized vertical gap
and odd short-line wraps ("Apr. 24,\n2026.  [Online]. Available:\n\n\<url\>") even
though there is no blank line in the source. Isolated and reproduced in a minimal
test file: the bug requires *both* (a) the paragraph spanning multiple raw source
lines *and* (b) a token too wide to fit on a single line — collapsing the paragraph
onto one physical source line fixes it with no visible/semantic change (Typst
treats intra-paragraph newlines as spaces regardless). Reference [22] showed a
milder version of the same thing ("May/June\n2024.  DOI:" with an odd gap).
**Fix:** reflowed the entire References section (all 30 entries, 61 logical
paragraphs) onto one source line per paragraph — the same fix, applied
prophylactically to the one section with several very long tokens (URLs, DOIs)
rather than patching entries one at a time. Verified refs [16]–[30] all render
cleanly with no regressions.

### Issue 7 — Two invisible Word icon glyphs rendered as black "tofu" boxes (Appendix B)
Two Appendix B command lines were prefixed in the *docx itself* by a Private-Use-Area
character (U+EC02, U+EC03 — a Google-Docs/Word-plugin "code block" icon glyph,
colored green, run-adjacent to the Roboto-Mono command text; confirmed present in
the docx's raw run XML, not a conversion artifact). Neither Carlito nor DejaVu Sans
covers the PUA, so Typst drew the fallback `.notdef` glyph — a visible black box —
right before `python3 3_gen_nvmain_config.py --freq 800` and 3 other spots.
**Fix:** kept the literal character (so the text-parity extraction is unaffected)
but made it invisible and zero-width: `#box(width: 0pt)[#text(fill: white)[<char>]]`.
No visible box, no stray indentation, character still present in the source for
fidelity. This is a deliberate compromise, documented here rather than silently
deleting a character from "frozen" content.

### Checked, no issue found
- All 7 tables (7–8 columns): none overflow the 6.5in text width at 11pt/6pt inset —
  contrary to the task's stated suspicion, this was never actually a problem here.
- Image sizing (`width: 6.5in`, explicit heights matching the text-block width):
  renders full-width, aspect intact, on every one of the 27 images.
- Heading sizes (16/13/11.5pt): visually consistent scale throughout, matches TOC
  hierarchy.
- Appendix B literal double-hyphens (`--freq`, `--cycles`, `--trace`, `--models`):
  render correctly as ASCII `--`, no en-dash regression, on both command lines (p.48
  and the pipeline-interface paragraph, p.49).
- References: every URL fully visible across pages 44–46, no truncated line, no
  `//`-comment line-eating (checked every reference for a dropped tail; none found
  once Issue 6 above was fixed).

## 3. Not fixed — noted only

- **Title-page vertical position** (`#v(2in)` then centered title): a rough
  approximation baked in before this pass. Could not compare pixel-for-pixel against
  the docx title page because no LibreOffice/Word was available to render it (see
  §0). Left as-is — cosmetic, cannot verify without a docx renderer, and moving it
  is a judgment call outside this pass's ability to validate.

## 4. Text-parity re-verification

`pdftotext`/`pandoc -t plain` were unavailable (§0); used PyMuPDF text extraction and
python-docx paragraph/table-row extraction instead, in document order, both with the
generated TOC/LoF/LoT block and its docx-side placeholder ("Right-click and choose
Update Field...") excluded, as instructed.

- **Raw diff, no normalization:** 456 words differ (word-level, `difflib`
  SequenceMatcher over whitespace-split tokens).
- **After normalizing** quotes (curly→straight), dashes (en/em/minus→hyphen), `×`→`x`,
  collapsing whitespace, stripping bullet/arrow glyphs (structural, not content),
  and rejoining tokens split by the PDF extractor's line-wrap inside a hyphenated or
  slash-containing word (e.g. `High-` + `Bandwidth` → `High-Bandwidth`, an artifact
  of MuPDF extracting wrapped lines as separate tokens, not a real difference):
  **19 words differ, in 14 hunks.**

All 19 were individually inspected and are tool-extraction artifacts, not content
defects:
- **12 words / 6 hunks** — math content (`10^5 Ω`, `10^9 Ω`, `20F²`, `4F²`):
  `python-docx` does not extract Word OMML equation objects as text at all (they're
  embedded objects, invisible to `.text`), while PyMuPDF extracts Typst's math as
  math-italic Unicode (`𝐹`) glued to exponents. **Visually confirmed correct** on
  p.5 ("10⁵ Ω LRS and 10⁹ Ω HRS") and p.47 (Appendix A, "20 F² for 1T1R, 4 F² for
  1S1R").
- **3 words / 1 hunk** — reference [29]'s URL wraps at "https://www.\nmicron.com/…"
  in PDF extraction (line-wrap inside a `.`-delimited, not hyphen/slash-delimited,
  boundary my rejoin logic didn't cover). **Visually confirmed** the full URL
  renders correctly and legibly on p.46, same as every other reference — not a
  content defect, just a gap in the comparison script's tokenizer.
- **4 words / 2 hunks** — the two intentionally-hidden PUA icon glyphs from Issue 7
  extract as U+EC03 in the docx-side script but as U+0000 (NUL) from the PDF: the
  font has no glyph (hence no `ToUnicode` mapping) for U+EC03, so PyMuPDF's
  extraction of the invisible fallback glyph doesn't round-trip the original
  codepoint. The character is genuinely present in the Typst source (preserved
  exactly for fidelity, per Issue 7); only the *extracted* codepoint differs, and
  only for a glyph that is deliberately invisible on the page.

**Net result: zero real wording/content differences found.** The instruction was to
report the diff count rather than tune the normalizer to hide real diffs — the 19
residual words above are reported, not suppressed, and each is individually
traceable to a specific, explained tool limitation rather than a document defect.

## 5. Anchor checklist

| Anchor | Result |
|---|---|
| 27 `image(` calls, exact order 1,2,3,4,5,25,6,7,8,9,10,11,12,13,14,15,16,17,27,18,19,20,26,21,22,23,24 | **PASS** |
| 7 `#table(` blocks | **PASS** |
| 20 figure-caption entries in LoF (13 single + 7 combined) | **PASS** |
| 7 table captions in LoT, document order 1,2,3,4,5,7,6 | **PASS** |
| Highest bracket reference `[30]` | **PASS** |
| PDF text contains "eleven silent failure modes" | **PASS** |
| PDF text contains "17-25 years" | **FAIL — phrase does not exist.** Checked both the compiled PDF and the source docx directly: the actual text is "worst-case SLC lifetime reaches 9-17 years (the slower-writing selector variant, 12-25)" — "17" and "25" appear, but never adjacent, and "years" is not repeated after "12-25". Reporting this rather than treating it as a pass; it may reflect the anchor spec being written from an earlier draft's wording. |

## 6. Deliverables

- `book.typ` — fixed source, now the canonical copy at `documents/MBMM_Book_Typst/`;
  the original pre-QA `book.typ` lives at
  `archive/documents/MBMM_Book_Typst_preQA/book.typ`.
- `book.pdf` — compiled from the fixed source, 49 pages, 0 compile errors/warnings.
- `qa_screenshots/` — before/after PNGs for the 5 highest-impact fixes (Issues 1–5
  above).
- This report.

No style helper file was factored out — the one styling addition (`blockquote`'s
border/inset) is 5 lines and lives inline in the existing `// GEN-BEGIN preamble` /
`// GEN-END preamble` block where `blockquote` was already defined; splitting it to
a separate file seemed like unwarranted structure for one function.
