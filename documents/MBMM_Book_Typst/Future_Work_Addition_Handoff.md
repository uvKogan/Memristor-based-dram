# Handoff: add a new Future Work item — standalone simulator wrapper

**Status: approved, ready to execute.** Not a Tier-3-style discussion item — the
Lead has decided this goes in. Per `Review_Fixes_Tracker.md`'s ground rules: claim
this item (Owner + `in-progress`) before editing, run the compile gate after, and
append a Change Log entry when done. No edits made to `Project_Book.typ` from this
file or this session.

## What to add

A new bullet in **§4.1 (Future Work: Simulator and Infrastructure Enhancements)**,
not §4.2 — this is an infrastructure/tooling idea (generalizing the ETL pipeline
itself), not an architectural-scaling one, so it belongs alongside Power-Down
Restoration / Parameter Optimization / Native MLC Logic, not alongside the density
and node-scaling items. (Placement call, not a hard requirement — use judgment if
there's a reason §4.2 fits better once you're looking at the surrounding prose.)

Suggested text, matching the existing bullet style (`#strong[Title:] description`):

```
- #strong[Standalone Device-to-System Simulator Wrapper:] Generalizing "The
  Bridge" (Section 2.1) - the cross-layer ETL pipeline that translates NVSim's
  device-level physical metrics into NVMain's cycle-accurate architectural
  parameters - into a reusable, project-independent simulator wrapper. The
  toolchain audit (Section 3.1.6) already demonstrated that this translation
  layer is precisely where correctness risk concentrates; packaging it as a
  standalone, hardened tool would let other device-level-to-system-level
  simulation pairings benefit from the same repairs and validation discipline,
  beyond this project's specific NVSim/NVMain pairing.
```

Origin note (context for the editor, not necessarily book text): this idea came
from the author's HW/SW co-design coursework, not from this book's own critique
pass — mention this in the Change Log entry, not necessarily in the book prose
itself, unless the surrounding style calls for an attribution.

## After adding

- Run the compile gate: `typst compile --font-path fonts Project_Book.typ <out>.pdf` must exit 0.
- No new citation is introduced, so `Reference_Guide.md` shouldn't need a count
  update — but double-check nothing in `Reading_Guide.md`'s §4 coverage notes
  needs a corresponding mention.
- Append a Change Log entry per the tracker's template, noting this originated
  outside the critique pass (course discussion) and was Lead-approved directly,
  not drafted via the Tier-3 proposal process.

## Already done (not part of this handoff)

`Presentation_Outline.md` Slide 33 ("Other fronts") already lists this item —
edited directly in this session, since that file isn't part of the book's
parallel-editing coordination.
