import sys
import os

if len(sys.argv) != 3:
    print("Usage: python3 parse_trace.py <input_raw_trace> <output_nvt>")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

# NVMain requires a 128-character dummy hex string for SLC/MLC padding
dummy_data = "0" * 128 

print(f">>> Parsing gem5 raw trace {input_file} to NVMain format...")

access_count = 0
with open(input_file, "r") as fin, open(output_file, "w") as fout:
    for line in fin:
        # Only process lines from the memory controller
        if "system.mem_ctrls:" in line:
            parts = line.split()
            
            try:
                # Extract the tick (and strip the coססססססססססlon)
                tick_str = parts[0].replace(':', '')
                # Convert gem5 ticks (ps) to NVMain cycles (assuming 1GHz = 1000ps)
                cycle = int(tick_str) // 1000 
                
                op = "R"
                addr = None
                
                # Scan tokens for the address and the operation type
                for p in parts:
                    if p.startswith('0x'):
                        addr = p
                    elif 'Write' in p:
                        op = "W"
                        
                if addr:
                    # NVMain format: Cycle OP Address Data ThreadID
                    fout.write(f"{cycle} {op} {addr} {dummy_data} 0\n")
                    access_count += 1
                    
                    # Print progress so we know it hasn't frozen on the 2.4GB file
                    if access_count % 1000000 == 0:
                        print(f"  ... Parsed {access_count} accesses ...")
                        
            except Exception as e:
                continue

print(f"SUCCESS: Created stable NVMain trace at {output_file} with {access_count} memory accesses.")

print(f">>> Auto-Cleanup: Vaporizing the massive raw text trace...")
try:
    os.remove(input_file)
    print(f"SUCCESS: {input_file} has been deleted.")
except Exception as e:
    print(f"[!] Warning: Could not delete raw trace: {e}")