import math
import json
import os

def generate_nvmain_config(name, hw_metrics, target_freq_mhz=800):
    cycle_time_ns = 1000.0 / target_freq_mhz
    tREAD = math.ceil(hw_metrics['read_latency_ns'] / cycle_time_ns)
    tWP = math.ceil(hw_metrics['write_latency_ns'] / cycle_time_ns)

    config_content = f"""
; MBMM Auto-Generated Config
; Architecture: {name} | Freq: {target_freq_mhz}MHz
CLK {target_freq_mhz}
MEM_CTL FRFCFS
AddressMappingScheme R:SA:RK:BK:CH:C

tREAD {tREAD}
tWP {tWP}
tRCD {tREAD}
tRP {tREAD}
tCAS {tREAD}

Erd {hw_metrics['read_energy_nj']}
Ewr {hw_metrics['write_energy_nj']}
"""
    file_path = f"simulators/nvmain/Config/reram_{name}.config"
    full_path = os.path.abspath(file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    status = "Overwrote" if os.path.exists(full_path) else "Created"
    with open(full_path, 'w') as f:
        f.write(config_content)
    print(f"[SUCCESS] {status} NVMain config: {full_path}")

def ensure_trace_file():
    trace_path = os.path.abspath("test_reram.nvt")
    if not os.path.exists(trace_path):
        content = "0 R 0x0 0x0 0\n100 W 0x40 0xFF 0\n"
        with open(trace_path, 'w') as f:
            f.write(content)
        print(f"[SUCCESS] Created synthetic trace: {trace_path}")

# Run Generation
if os.path.exists('slc_hardware_metrics.json'):
    with open('slc_hardware_metrics.json', 'r') as f:
        slc_data = json.load(f)
        for track_name, metrics in slc_data.items():
            generate_nvmain_config(track_name, metrics)
    ensure_trace_file()