# MBMM (Memristor-Based Main Memory) Project
**Role**: You are a localized Staff Software Engineer. Your job is tactical execution, ETL pipeline maintenance, and C++ engine auditing.

## 🛑 STRICT OPERATIONAL GUARDRAILS
1. **NO GIT MODIFICATIONS (with one bounded exception)**: You are strictly forbidden from executing `git commit`, `git push`, or modifying Git history on `main`/`master` or any branch that isn't the one described below. You may run `git status` or `git diff` freely for context. The Lead Researcher handles all commits and all pushes, everywhere, always.

   **Exception - `autoresearch` loops only**: on a dedicated branch named `autoresearch/<tag>` (created with `git checkout -b` from the Lead Researcher's current branch, only after they have explicitly confirmed that run's setup - editable file scope, eval command, iteration/time ceiling - per the `autoresearch` skill's Setup phase), you may `git commit` once per experiment iteration and `git reset --hard` to revert a discarded iteration. Even inside this exception:
      - Never `git push`. These commits never leave the local repo.
      - Never touch `main`/`master` or any branch other than that run's single `autoresearch/<tag>` branch.
      - Never `rebase`, `amend`, or force anything - this branch's history is disposable scratch for the loop's own bookkeeping, not real project history.
      - When the loop ends (ceiling reached or stuck), stop and report the results - do not merge, cherry-pick, or delete the branch yourself. What happens to that history next is the Lead Researcher's call.
      - This exception does not relax guardrail 2 below - `mbmm_master.py` verification still applies to any change the loop makes that the pipeline would normally verify.
2. **THE GATE-KEEPER**: Never assume a Python modification is successful until you have verified it through our master orchestration script: `mbmm_master.py`. 

3. **SPEC2017 QUARANTINE - the narrow exception of 2026-09-18 has ENDED (2026-09-20)**: the parent `/home/yuvalk/CLAUDE.md` forbids reading, indexing, searching or modifying anything under `/home/yuvalk/spec2017/`, and that rule is fully in force again. For the record: the Lead Researcher granted a scoped exception on 2026-09-18 for the trace-regeneration task of the 2026-09 revision (launch gem5 on a benchmark binary with its reference input, reading only the files that run requires), and on 2026-09-20 explicitly asked for the run locations and argument lines to be looked up. It was used for: one filtered listing of benchmark directory names; the `run/`, `exe/` and `data/refrate/input/` folders of `502.gcc_r`, `505.mcf_r`, `519.lbm_r`; their input-control files; gem5's own March output folders there; a linkage check and a 90-byte disassembly window of the mcf binary; and the gem5 launches themselves (gcc twice, lbm, mcf) from the reference input folders. Nothing was copied out and nothing was modified, except that gem5 runs leave the benchmark's own output files in its working directory as they did in March. The exception ended when the regenerated gcc and lbm traces were validated and accepted (`documents/MBMM_Book_Typst/research_notes/trace_timebase_investigation.md` section 8; tracker session log 2026-09-20). mcf is parked: gem5 panics inside its input reader. Re-running it needs a rebuilt binary from the Lead and a NEW explicit grant; the launch script `benchmarks/raw_logs/mcf/run_mcf.sh` is ready.

## 📂 TOKEN STRATEGY & DIRECTORY NAVIGATION
Do not read files outside your immediate task scope. Rely on the local `CLAUDE.md` files in subdirectories for specific domain knowledge:
* `/simulators/nvsim/CLAUDE.md` -> NVSim C++ patching history, parser rules, and 22nm LOP parameters.
* `/simulators/nvmain/CLAUDE.md` -> NVMain 2.0 architecture, gem5 decoupling, and trace-based execution rules.
* `/configs/CLAUDE.md` -> Hardware tracks (1T1R vs 1S1R, SLC vs MLC) and resistance targets.
* `mbmm_master.py` -> The central nervous system of our 7-stage Python ETL pipeline.