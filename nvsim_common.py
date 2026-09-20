"""Shared NVSim helpers (T2.6).

Both `1_run_nvsim_hardware.py` (the primary NVSim run script) and
`4_execute_simulation.py` (Stage 4's own, older per-architecture NVSim call)
invoke the NVSim binary directly and need the same two things done to its
output: strip Mat.cpp's debug prints, and gate on the forced subarray
organization. This module is the single place those live, so the two
digit-prefixed scripts (imported elsewhere via
`importlib.util.spec_from_file_location`, since a module name cannot start
with a digit) both import it as an ordinary module instead of duplicating
the logic.
"""
import re
from pathlib import Path

# The local NVSim build has debug prints in Mat.cpp (lines starting ">>> [")
# that can emit millions of lines per run. They must never be stored or
# parsed; strip them out of anything a caller saves or gate-checks.
DEBUG_LINE_RE = re.compile(r'^>>> \[')
SENSITIVITY_1024_RE = re.compile(r"_1024(?:_(?:single|8chip|16chip|full_dimm))?$")


def strip_debug_lines(text):
    """Removes NVSim's Mat.cpp '>>> [' debug prints from captured stdout."""
    return "\n".join(line for line in text.splitlines() if not DEBUG_LINE_RE.match(line))


def expected_organization(cfg_path):
    """The literal 'N Rows x N Columns' string a forced-organization cfg must
    print. '_1024' cfgs are the T2.6 1024x1024 sensitivity variant; every
    other cfg is held to the T2.6 2048x2048 baseline organization."""
    stem = Path(cfg_path).stem
    # '_1024' counts only as the sensitivity suffix (optionally followed by an
    # architecture suffix), never as a substring elsewhere in the name.
    size = 1024 if SENSITIVITY_1024_RE.search(stem) else 2048
    return f"{size} Rows x {size} Columns"


def check_forced_organization(stdout, cfg_path):
    """Gate: a run only counts if it reports the forced subarray organization
    literally. A misspelled or unparsed -Force* key still exits 0: NVSim then
    explores on its own and reports some other organization (or prints
    'cannot be found' for the missing key), and both must fail this gate even
    though the process itself exited 0.

    Returns (ok, message).
    """
    expected = expected_organization(cfg_path)
    if "cannot be found" in stdout:
        return False, (f"Organization gate FAILED: NVSim reported a missing/unparsed "
                        f"force key ('cannot be found'); expected '{expected}'.")
    # Anchored match: '12048 Rows x 2048 Columns' or '2048 Rows x 20480 Columns'
    # must NOT pass as '2048 Rows x 2048 Columns'.
    if not re.search(r"(?<!\d)" + re.escape(expected) + r"\b", stdout):
        return False, (f"Organization gate FAILED: expected '{expected}' not present "
                        f"in NVSim output; the forced organization was not honored.")
    return True, f"Organization gate PASSED: '{expected}' found."
