#!/usr/bin/env python3
import sys
import re
from pathlib import Path

# Paths based on MBMM structure
input_file = Path("simulators/gem5/m5out/mcf_raw.txt")
output_file = Path("benchmarks/mcf_spec2017.nvt")

# NVMain requires exactly 128 chars of hex data for our SLC modeling
DUMMY_DATA = "0" * 128 

print(f">>> Parsing gem5 raw trace to NVMain format...")

parsed_lines = 0
with open(input_file, "r") as fin, open(output_file, "w") as fout:
    for line in fin:
        # Matches: "   500: system.mem_ctrls: recvAtomic: ReadReq 0x2b540"
        match = re.search(r'^\s*(\d+):.*?(ReadReq|WriteReq)\s+(0x[0-9a-fA-F]+)', line)
        if match:
            cycle = match.group(1)
            op_str = match.group(2)
            addr = match.group(3)
            
            # Convert operation to NVMain 'R' or 'W'
            op = "R" if op_str == "ReadReq" else "W"
            
            # Format: Cycle Operation Address Data ThreadID
            fout.write(f"{cycle} {op} {addr} {DUMMY_DATA} 0\n")
            parsed_lines += 1

print(f"SUCCESS: Created stable NVMain trace at {output_file} with {parsed_lines} memory accesses.")