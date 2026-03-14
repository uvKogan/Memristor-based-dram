#!/usr/bin/env python3
import os
from pathlib import Path

root_dir = Path(__file__).parent.absolute()
output_file = root_dir / "benchmarks" / "stream.nvt"

ARRAY_SIZE = 100000 
ELEMENT_SIZE = 64 

ADDR_A = 0x10000000  
ADDR_B = 0x20000000  

# NVMain requires a 128-character dummy hex string for SLC data fields
DUMMY_DATA = "0" * 128

print(f">>> Generating STABLE STREAM trace: {output_file}")

with open(output_file, "w") as f:
    for i in range(ARRAY_SIZE):
        # Read from A, Write to B
        # Standard format: Cycle Type Address Data ThreadID
        f.write(f"{i*10} R 0x{ADDR_A + (i * ELEMENT_SIZE):08x} {DUMMY_DATA} 0\n")
        f.write(f"{i*10 + 5} W 0x{ADDR_B + (i * ELEMENT_SIZE):08x} {DUMMY_DATA} 0\n")

print(f"SUCCESS: Created trace with valid 128-char data fields.")