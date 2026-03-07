#!/usr/bin/env python3
import os
from pathlib import Path

root_dir = Path(__file__).parent.absolute()
output_file = root_dir / "benchmarks" / "stream.nvt"

ARRAY_SIZE = 100000 
ELEMENT_SIZE = 64 # Use 64-byte alignment to match standard cache lines

# Use a high base address (32-bit range) to prevent underflow in the translator
ADDR_A = 0x10000000  
ADDR_B = 0x20000000  

print(f">>> Generating STABLE STREAM trace: {output_file}")

with open(output_file, "w") as f:
    for i in range(ARRAY_SIZE):
        # Read from A, Write to B
        # Formatting with :08x ensures the address string is always 8 chars (32 bits)
        f.write(f"{i*10} R 0x{ADDR_A + (i * ELEMENT_SIZE):08x} 0x0 0\n")
        f.write(f"{i*10 + 5} W 0x{ADDR_B + (i * ELEMENT_SIZE):08x} 0xDEADBEEF 0\n")

print(f"SUCCESS: Created trace.")