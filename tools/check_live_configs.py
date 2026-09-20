#!/usr/bin/env python3
"""
tools/check_live_configs.py: guard against tracked configs and the live
NVMain configs diverging silently.

`configs/*.config` (and `configs/silicon/*.config`, an optional subdirectory
this repo currently leaves unused -- T2.8's microsecond-silicon sensitivity
configs are generated straight into `simulators/nvmain/Config/` by
`3_gen_nvmain_config.py --silicon`, so they always follow the primary run
matrix's `--channels`/`--decoder`/`--endurance-model`/`--freq`, and are never
tracked as static files under `configs/`) are the source of truth the
pipeline is meant to run: `simulators/nvmain/Config/`
is a submodule-tracked directory the pipeline actually reads at runtime
(4_execute_simulation.py). A copy that only ever gets edited in one of the
two places is a reproducibility hazard (see
documents/MBMM_Book_Typst/research_notes/access_granularity_study.md, "a
reproducibility hazard on its own" re: the old stale
configs/DDR5_4800_DRAM.config).

For every tracked `*.config` file, the live NVMain copy of the same filename
must exist and be byte-identical. Used as a fail-fast check at the start of
mbmm_master.py's system-simulation stage (see run_check_live_configs there),
and can be run standalone.
"""

import argparse
import difflib
import filecmp
import shutil
import sys
from pathlib import Path

# Directories (relative to the MBMM project root) that hold tracked configs
# needing a byte-identical live copy under the NVMain submodule's Config/.
TRACKED_CONFIG_SUBDIRS = ("", "silicon")


def _tracked_config_files(tracked_dir):
    """Yield every tracked config Path under tracked_dir's watched subdirs.

    Missing subdirectories (e.g. configs/silicon/, which nothing currently
    populates -- see the module docstring) are silently skipped -- their
    absence is not a divergence.
    """
    tracked_dir = Path(tracked_dir)
    for subdir in TRACKED_CONFIG_SUBDIRS:
        d = tracked_dir / subdir if subdir else tracked_dir
        if not d.is_dir():
            continue
        for cfg in sorted(d.glob("*.config")):
            yield cfg


def check_live_configs(tracked_dir, live_dir):
    """Compare every tracked configs/*.config (and configs/silicon/*.config)
    against simulators/nvmain/Config/<same filename>.

    Returns (ok, divergences): ok is True iff every tracked config has a
    byte-identical live copy. divergences is a list of human-readable
    strings, one per problem file (missing live copy, or a differing one
    with a unified-diff head), suitable for printing or logging.
    """
    tracked_dir = Path(tracked_dir)
    live_dir = Path(live_dir)

    divergences = []
    checked = 0

    for tracked_path in _tracked_config_files(tracked_dir):
        checked += 1
        live_path = live_dir / tracked_path.name

        if not live_path.exists():
            divergences.append(
                f"MISSING live copy: {tracked_path} has no counterpart at {live_path}"
            )
            continue

        if not filecmp.cmp(tracked_path, live_path, shallow=False):
            tracked_lines = tracked_path.read_text(errors="replace").splitlines(keepends=True)
            live_lines = live_path.read_text(errors="replace").splitlines(keepends=True)
            diff_head = "".join(
                difflib.unified_diff(
                    tracked_lines, live_lines,
                    fromfile=str(tracked_path), tofile=str(live_path),
                    n=1,
                )
            )
            # Keep the printed diff bounded: first 20 lines is plenty to
            # identify the divergence without flooding the log.
            diff_head_lines = diff_head.splitlines(keepends=True)[:20]
            divergences.append(
                f"DIFFERS: {tracked_path} != {live_path}\n" + "".join(diff_head_lines)
            )

    return (len(divergences) == 0, divergences, checked)


def sync_live_configs(tracked_dir, live_dir):
    """Copy every tracked configs/*.config (and configs/silicon/*.config)
    over its live NVMain counterpart, creating the destination if needed.

    Returns the list of (tracked_path, live_path) pairs that were copied.
    Only called when --sync is passed explicitly; never a default action.
    """
    tracked_dir = Path(tracked_dir)
    live_dir = Path(live_dir)

    copied = []
    for tracked_path in _tracked_config_files(tracked_dir):
        live_path = live_dir / tracked_path.name
        live_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tracked_path, live_path)
        copied.append((tracked_path, live_path))

    return copied


def main():
    parser = argparse.ArgumentParser(
        description="Check that tracked configs/*.config files and the live "
                    "simulators/nvmain/Config/ copies never diverge."
    )
    parser.add_argument(
        "--tracked-dir", default=str(Path(__file__).resolve().parent.parent / "configs"),
        help="Directory of tracked source-of-truth configs (default: configs/).",
    )
    parser.add_argument(
        "--live-dir",
        default=str(Path(__file__).resolve().parent.parent / "simulators" / "nvmain" / "Config"),
        help="Directory of live NVMain configs the pipeline actually reads "
             "(default: simulators/nvmain/Config/).",
    )
    parser.add_argument(
        "--sync", action="store_true",
        help="Copy tracked configs over the live ones instead of failing on "
             "a divergence. Explicit only, never the default.",
    )
    args = parser.parse_args()

    if args.sync:
        copied = sync_live_configs(args.tracked_dir, args.live_dir)
        print(f"[check_live_configs] --sync: repaired {len(copied)} config(s):")
        for tracked_path, live_path in copied:
            print(f"    {tracked_path} -> {live_path}")
        return 0

    ok, divergences, checked = check_live_configs(args.tracked_dir, args.live_dir)

    if ok:
        print(f"[check_live_configs] OK: {checked} tracked config(s) match their live copy.")
        return 0

    print(f"[check_live_configs] FAILED: {len(divergences)} of {checked} tracked "
          f"config(s) diverge from simulators/nvmain/Config/:", file=sys.stderr)
    for d in divergences:
        print(d, file=sys.stderr)
    print("\nRun with --sync to copy the tracked configs over the live ones, "
          "or investigate why the live copy was edited independently.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
