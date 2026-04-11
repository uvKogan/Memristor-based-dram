import os
import re
from pathlib import Path

def get_project_root():
    return Path(__file__).parent.absolute()

def should_include_file(filename):
    """Filter: Include reram_22nm, DDR5, 2D_DRAM, 3D_DRAM. Exclude sample_, test_, SRAM, nvsim.cfg"""
    filename_lower = filename.lower()
    
    # Strict exclusions
    exclude = ['sample_', 'test_', 'sram', 'nvsim.cfg']
    for pattern in exclude:
        if pattern in filename_lower:
            return False
    
    # Must match at least one inclusion pattern
    include = ['reram_22nm', 'ddr5', '2d_dram', '3d_dram']
    for pattern in include:
        if pattern in filename_lower:
            return True
    
    return False

def extract_lrs(content):
    """Extract LRS with robust regex"""
    patterns = [
        r"(?:LRS|ResistanceOn)\s*(?:\([^)]*\))?\s*[:=]?\s*([\d.eE+-]+)",
        r"ResistanceOn(?:AtReadVoltage|AtSetVoltage)\s*(?:\([^)]*\))?\s*[:=]?\s*([\d.eE+-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
    return None

def extract_hrs(content):
    """Extract HRS with robust regex"""
    patterns = [
        r"(?:HRS|ResistanceOff)\s*(?:\([^)]*\))?\s*[:=]?\s*([\d.eE+-]+)",
        r"ResistanceOff(?:AtReadVoltage|AtResetVoltage)\s*(?:\([^)]*\))?\s*[:=]?\s*([\d.eE+-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
    return None

def extract_timing(content):
    """Extract tCAS, tRCD, tRP"""
    tcas = re.search(r"tCAS\s*[:=]?\s*(\d+(?:\.\d+)?)", content, re.IGNORECASE | re.MULTILINE)
    trcd = re.search(r"tRCD\s*[:=]?\s*(\d+(?:\.\d+)?)", content, re.IGNORECASE | re.MULTILINE)
    trp = re.search(r"tRP\s*[:=]?\s*(\d+(?:\.\d+)?)", content, re.IGNORECASE | re.MULTILINE)
    
    tcas_val = tcas.group(1) if tcas else "—"
    trcd_val = trcd.group(1) if trcd else "—"
    trp_val = trp.group(1) if trp else "—"
    
    if tcas_val != "—" or trcd_val != "—" or trp_val != "—":
        return f"{tcas_val}–{trcd_val}–{trp_val}"
    return "—"

def extract_latency_from_results(config_name):
    """Extract average latency from simulation results"""
    results_dir = Path(__file__).parent / "results" / "system"
    if not results_dir.exists():
        return None
    
    latencies = []
    for f in results_dir.glob("*"):
        if config_name.lower() in f.name.lower():
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                    match = re.search(r"averageLatency\s+([\d.]+)", fp.read())
                    if match:
                        latencies.append(float(match.group(1)))
            except:
                pass
    
    if latencies:
        avg = sum(latencies) / len(latencies)
        return f"{avg:.2f}"
    return None

def extract_power_from_config(config_name):
    """Extract StandbyPower directly from NVMain .config file"""
    config_dir = Path(__file__).parent / "simulators" / "nvmain" / "Config"
    config_file = config_dir / f"{config_name}.config"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                match = re.search(r"StandbyPower\s+([\d.]+)", f.read())
                if match:
                    return f"{float(match.group(1)):.4f}"
        except:
            pass
    return None

def extract_power_from_results(config_name):
    """Extract average StandbyPower from simulation results (fallback)"""
    results_dir = Path(__file__).parent / "results" / "system"
    if not results_dir.exists():
        return None
    
    powers = []
    for f in results_dir.glob("*"):
        if config_name.lower() in f.name.lower():
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                    match = re.search(r"StandbyPower\s+=\s*([\d.]+)", fp.read())
                    if match:
                        powers.append(float(match.group(1)))
            except:
                pass
    
    if powers:
        avg = sum(powers) / len(powers)
        return f"{avg:.4f}"
    return None

def to_scientific_notation(val_str):
    """Convert to LaTeX scientific notation"""
    if not val_str or val_str == "—":
        return "—"
    try:
        num = float(val_str)
        if num == 0:
            return "$0$"
        
        formatted = f"{num:.1e}"
        
        if 'e' in formatted:
            mantissa, exp = formatted.split('e')
            exp_int = int(exp)
            mantissa = mantissa.rstrip('0').rstrip('.')
            return f"${mantissa} \\times 10^{{{exp_int}}}$"
        else:
            return f"${num}$"
    except:
        return val_str

def main():
    root = get_project_root()
    configs_dir = root / "configs"
    
    physics_rows = []  # .cell files
    arch_rows = {}     # .cfg/.config files keyed by config name
    
    # Scan configs directory recursively
    if configs_dir.exists():
        for path in sorted(configs_dir.rglob("*")):
            if not path.is_file():
                continue
            
            filename = path.name
            if not should_include_file(filename):
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except:
                continue
            
            # Extract physics data from .cell files
            if filename.endswith('.cell'):
                lrs = extract_lrs(content)
                hrs = extract_hrs(content)
                
                if lrs and hrs:
                    try:
                        lrs_float = float(lrs)
                        hrs_float = float(hrs)
                        ratio = hrs_float / lrs_float
                        
                        arch_name = filename.replace('.cell', '')
                        
                        physics_rows.append({
                            'arch': arch_name,
                            'lrs': to_scientific_notation(lrs),
                            'hrs': to_scientific_notation(hrs),
                            'ratio': to_scientific_notation(str(ratio)),
                        })
                    except:
                        pass
            
            # Extract architecture timing data from .cfg/.config files
            elif filename.endswith(('.cfg', '.config')):
                timing = extract_timing(content)
                config_name = filename.replace('.cfg', '').replace('.config', '')
                
                arch_rows[config_name] = {
                    'config': config_name,
                    'timing': timing,
                    'latency': "—",
                    'power': "—",
                }
    
    # Now augment architecture data with latency and power from simulation results
    for config_name in arch_rows:
        latency = extract_latency_from_results(config_name)
        
        # Try config file first (deterministic, fresh data), fall back to results
        power = extract_power_from_config(config_name)
        if not power:
            power = extract_power_from_results(config_name)
        
        if latency:
            arch_rows[config_name]['latency'] = latency
        if power:
            arch_rows[config_name]['power'] = power
    
    # Build Table 1: Physics
    table1_md = "# Phase 1 - NVSim Physics (Device Level)\n\n"
    table1_md += "| Target Architecture | LRS (Ω) | HRS (Ω) | Resistance Ratio (HRS/LRS) |\n"
    table1_md += "| :--- | :--- | :--- | :--- |\n"
    
    for row in sorted(physics_rows, key=lambda x: x['arch']):
        table1_md += f"| {row['arch']} | {row['lrs']} | {row['hrs']} | {row['ratio']} |\n"
    
    # Build Table 2: Architecture
    table2_md = "\n# Phase 2 - NVMain Architecture (System Level)\n\n"
    table2_md += "| System Configuration | Timing (tCAS/tRCD/tRP) | Latency (ns) | StandbyPower (W) |\n"
    table2_md += "| :--- | :--- | :--- | :--- |\n"
    
    for config_name in sorted(arch_rows.keys()):
        row = arch_rows[config_name]
        table2_md += f"| {row['config']} | {row['timing']} | {row['latency']} | {row['power']} |\n"
    
    # Combine and output
    output = table1_md + table2_md
    
    # Write to file
    output_file = root / "PROJECT_BOOK_TABLES.md"
    with open(output_file, 'w') as f:
        f.write(output)
    
    # Print to console
    print(output)
    print(f"\n{'='*70}")
    print(f"[✓] Tables successfully written to: {output_file}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
