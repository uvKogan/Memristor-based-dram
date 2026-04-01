import sys
import os

if len(sys.argv) != 3:
    print("Usage: python3 parse_trace.py <input> <output>")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

# NVMain requires a 128-character dummy hex string for SLC/MLC padding
dummy_data = "0" * 128

print(f">>> Translating SCALE-Sim trace {input_file} to NVMain format...")

default_op = "W" if "OFMAP" in input_file.upper() else "R"

access_count = 0
cycle_offset = None

with open(input_file, "r") as fin, open(output_file, "w") as fout:
    for line in fin:
        line = line.strip()
        if not line or "Cycle" in line or "Address" in line:
            continue
        
        parts = line.replace(',', ' ').split()
        
        if len(parts) >= 2:
            try:
                raw_cycle = int(float(parts[0]))
                
                # SCALE-Sim schedules DRAM pre-fetches at negative cycles.
                # We must shift the timeline so it starts at >= 0.
                if cycle_offset is None:
                    cycle_offset = abs(raw_cycle) if raw_cycle < 0 else 0
                    
                # Apply the temporal shift
                cycle = raw_cycle + cycle_offset
                
                addr_str = parts[1]
                if addr_str.lower().startswith('0x'):
                    addr_int = int(addr_str, 16)
                else:
                    addr_int = int(float(addr_str))
                    
                addr_hex = hex(addr_int)
                
                fout.write(f"{cycle} {default_op} {addr_hex} {dummy_data} 0\n")
                access_count += 1
                
                if access_count % 1000000 == 0:
                    print(f"  ... Translated {access_count} accesses ...")
            except ValueError:
                continue

print(f"SUCCESS: Created stable NVMain trace at {output_file} with {access_count} memory accesses.")