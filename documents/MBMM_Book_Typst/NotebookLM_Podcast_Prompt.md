# NotebookLM Podcast Prompt — MBMM Reference Deep-Dive

## How to use this file

1. Create a new NotebookLM notebook.
2. Upload as sources: `Project_Book.pdf` (or `Project_Book.typ`), this file's companion `Reference_Guide.md`, and — if you want maximum fidelity — the individual PDFs in `documents/reference_validation_papers/` (at minimum: the two EMBER papers, the Matsui et al. HRS/LRS paper, and the Wong et al. RRAM review, since those are the load-bearing ones).
3. Go to Studio → Audio Overview → Customize, and paste the prompt below into the "What should the hosts focus on?" box.

---

## Prompt to paste into NotebookLM's customization box

```
This notebook covers the reference sources behind a memristor-based main
memory (ReRAM) research project comparing 22nm ReRAM against commodity
DDR5 as a main-memory replacement. Generate a podcast conversation that
walks a listener with some technical background (comfortable with
computer architecture and basic materials science, but not a memory-
device specialist) through the reference material, organized as follows:

1. START with the big picture: why does this project exist? Cover the
   2025-2026 AI-driven DRAM/HBM supply squeeze (references on the AI
   memory market crunch) and the "memory wall" problem (peak compute
   FLOPS scaling faster than memory bandwidth) that motivates looking at
   alternatives to DRAM at all.

2. THEN explain what ReRAM/memristors actually are at a device level,
   and the two competing cell designs this project evaluates:
   transistor-gated (1T1R) versus selector-gated (1S1R) crossbar
   arrays. Explain WHY the resistance targets (low-resistance and
   high-resistance states) matter for both leakage power and sensing
   reliability, and be explicit that the paired high-resistance target
   used in this project is borrowed from a different (analog
   compute-in-memory) use case than the low-resistance target, since the
   source paper didn't specify one for the digital-memory case directly
   - explain why the project's own sensitivity analysis shows this
   doesn't actually change any conclusions.

3. THEN cover the EMBER research papers - these are the most important
   sources in the whole project. Explain that EMBER is a real
   multi-bit-per-cell RRAM chip with two publications: a short
   conference paper and a fuller journal follow-up by the same team.
   Explain what each paper contributes: the conference paper gives the
   read-energy figures, and the journal follow-up gives the read-latency
   and write-side (bandwidth and energy) figures. Together these define
   the four penalty multipliers (read latency, write latency, read
   energy, write energy) used to model 2-bit-per-cell operation
   throughout the project.

4. THEN cover the DDR5 baseline sources - the JEDEC standard, and the
   Micron/SK hynix datasheets used to calibrate realistic power draw
   instead of default simulator placeholder values. Explain simply what
   "IDD current specifications" mean and why using two vendors' real
   datasheets instead of one gives a more honest power estimate (a
   "floor to ceiling" band rather than a single point value).

5. THEN cover the industry-context sources - server refresh cycles
   (how long data centers actually keep hardware, which sets the
   endurance bar ReRAM has to clear), the Intel Optane/3D-XPoint
   business failure (a cautionary tale that a real, working
   selector-based memory got killed by cost economics, not physics),
   and the recent 3D-DRAM and 3D-X-DRAM roadmap announcements that show
   where DRAM itself is trying to go next.

6. THEN cover the simulation tooling briefly (NVSim, NVMain, gem5,
   SCALE-Sim, SPEC CPU2017, STREAM) - just enough for the listener to
   understand there's a real cross-layer simulation pipeline here, not
   hand-waving: device-level circuit simulation feeding into
   system-level architecture simulation, driven by real captured
   memory-access traces from real benchmark programs.

7. CLOSE with a synthesis: what's the actual bottom-line finding this
   reference material supports - ReRAM's power-efficiency case is real
   and well-grounded; its raw latency is a real tradeoff; the density
   argument depends on DRAM staying stuck on its current scaling
   trajectory, which the sources themselves suggest may not hold
   forever.

Tone: knowledgeable but conversational, the way two engineers would
actually discuss a colleague's reference list over coffee - it's fine to
be skeptical or ask "wait, is that really what the paper says?" out
loud, especially around item 3 above. Avoid reading citations as bare
numbers ("reference 6 says...") - refer to sources by what they are
("the EMBER conference paper," "the Wong review paper") the way a human
would in conversation.
```

---

## Optional shorter variant (if you just want the reference material, not the full narrative)

```
Generate a podcast that walks through each cited source in this notebook
one at a time, in the order they appear in the reference list, briefly
explaining for each one: what kind of source it is (peer-reviewed paper,
industry news article, technical datasheet, or standard), and what
specific claim in the research paper it's being used to support.
```
