import os
import re
import math
from collections import defaultdict

def normalize_value(val_str):
    """Convert scientific or decimal notation to float for comparison."""
    if not val_str:
        return None
    try:
        return float(val_str)
    except:
        return None

def extract_resistance(content, res_type):
    """
    Extract LRS or HRS from various naming conventions.
    res_type: 'LRS' or 'HRS'
    """
    patterns = {
        'LRS': [r"(?:-)?LRS\s*(?:\([^)]*\))?\s*[:=]\s*([\d.e+\-]+)", 
                r"(?:-)?ResistanceOn(?:AtReadVoltage|AtSetVoltage)?\s*(?:\([^)]*\))?\s*[:=]\s*([\d.e+\-]+)"],
        'HRS': [r"(?:-)?HRS\s*(?:\([^)]*\))?\s*[:=]\s*([\d.e+\-]+)",
                r"(?:-)?ResistanceOff(?:AtReadVoltage|AtResetVoltage)?\s*(?:\([^)]*\))?\s*[:=]\s*([\d.e+\-]+)"]
    }
    
    for pattern in patterns.get(res_type, []):
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
    return None

def extract_timing(content, param):
    """Extract timing parameters: tCAS, tRCD, tRP, ReadLatency, WriteLatency."""
    patterns = [
        rf"(?:-)?{param}\s*(?:\([^)]*\))?\s*[:=]\s*(\d+(?:\.\d+)?)",
        rf"(?:-)?{param}\s*[:=]\s*(\d+(?:\.\d+)?)",
        rf"(?:-)?{param}\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
    return None

def extract_power(content):
    """Extract StandbyPower."""
    patterns = [
        r"(?:-)?StandbyPower\s*(?:\([^)]*\))?\s*[:=]\s*([\d.]+)",
        r"(?:-)?StandbyPower\s*[:=]\s*([\d.]+)",
        r"(?:-)?StandbyPower\s+=\s*([\d.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
    return None

def extract_devices(content):
    """Extract total_devices."""
    patterns = [
        r"(?:-)?total_devices\s*[:=]\s*(\d+)",
        r"(?:-)?total_devices\s+(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)
    return None

def is_close_to(value, target, tolerance=0.1):
    """Check if value is within tolerance of target (10% by default)."""
    if value is None or target is None:
        return False
    return abs(value - target) / target <= tolerance

def get_avg_power_from_results(config_name):
    """Get average StandbyPower from results/system/ files for a config."""
    results_dir = "results/system"
    if not os.path.exists(results_dir):
        return None
    
    powers = []
    for f in os.listdir(results_dir):
        if config_name.lower() in f.lower():
            try:
                with open(os.path.join(results_dir, f), 'r', encoding='utf-8', errors='ignore') as fp:
                    match = re.search(r"StandbyPower\s+=\s*([\d.]+)", fp.read())
                    if match:
                        powers.append(float(match.group(1)))
            except:
                pass
    
    if powers:
        return str(sum(powers) / len(powers))
    return None

def get_avg_latency_from_results(config_name):
    """Get average latency from results/system/ files for a config."""
    results_dir = "results/system"
    if not os.path.exists(results_dir):
        return None
    
    latencies = []
    for f in os.listdir(results_dir):
        if config_name.lower() in f.lower():
            try:
                with open(os.path.join(results_dir, f), 'r', encoding='utf-8', errors='ignore') as fp:
                    match = re.search(r"averageLatency\s+([\d.]+)", fp.read())
                    if match:
                        latencies.append(float(match.group(1)))
            except:
                pass
    
    if latencies:
        return str(sum(latencies) / len(latencies))
    return None

def validate_row(f_name, lrs, hrs, tcas, trcd, trp, rlat, wlat, latency_map=None):
    """Determine PASS/FAIL/WARN status."""
    is_reram = "reram" in f_name.lower() or "rram" in f_name.lower()
    is_mlc = "mlc" in f_name.lower()
    is_slc = "slc" in f_name.lower()
    is_ddr5 = "ddr5" in f_name.lower()
    
    status = "PASS"
    issues = []
    
    if is_reram:
        # Check LRS ≈ 10^5
        lrs_val = normalize_value(lrs)
        if lrs_val is not None:
            if not is_close_to(lrs_val, 1e5, tolerance=0.15):
                issues.append(f"LRS={lrs}")
        
        # Check HRS ≈ 10^9
        hrs_val = normalize_value(hrs)
        if hrs_val is not None:
            if not is_close_to(hrs_val, 1e9, tolerance=0.15):
                issues.append(f"HRS={hrs}")
        
        # Check MLC penalty: ReadLatency should be ~3x SLC baseline
        if is_mlc and latency_map:
            # Extract config variant (e.g., "1t1r" from "reram_22nm_1t1r_mlc")
            config_match = re.search(r"(22nm_\w+)_mlc", f_name.lower())
            if config_match:
                config_variant = config_match.group(1)
                slc_key = f"reram_{config_variant}_slc"
                
                if slc_key in latency_map:
                    slc_lat = normalize_value(latency_map[slc_key])
                    mlc_lat = normalize_value(rlat)
                    
                    if slc_lat and mlc_lat:
                        ratio = mlc_lat / slc_lat
                        # MLC penalty should be approximately 3x (within tolerance 20%)
                        # This means: 2.4x to 3.6x (3.0 ± 0.6)
                        if not is_close_to(ratio, 3.0, tolerance=0.20):
                            issues.insert(0, f"MLC Penalty Not Applied (ratio={ratio:.2f}x)")
        
        if issues:
            status = "FAIL (" + ", ".join(issues) + ")"
    
    if is_ddr5:
        # JEDEC DDR5-4800 Targets: 34-34-34
        timings = []
        if tcas: timings.append(tcas)
        if trcd: timings.append(trcd)
        if trp: timings.append(trp)
        
        if timings and all(t == "34" for t in timings):
            status = "PASS"
        elif timings:
            status = f"FAIL (DDR5:{'-'.join(timings)})"
    
    return status

def audit():
    # Paths to scan
    paths = ["results", "configs"]
    print("# MBMM Model Audit Log\n")
    print("| File | LRS (Ω) | HRS (Ω) | Timing (CAS/RCD/RP) | Pwr (W) | Lat (ns) | Status |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    found_files = []
    for p in paths:
        if os.path.exists(p):
            for root, dirs, files in os.walk(p):
                for f in files:
                    if f.endswith((".config", ".cfg", ".cell")):
                        found_files.append(os.path.join(root, f))
    
    # First pass: collect latency data for MLC penalty validation
    latency_map = {}
    for path in sorted(found_files):
        f_name = os.path.basename(path)
        config_key = f_name.replace(".cfg", "").replace(".cell", "").replace(".config", "")
        
        # Try to get average latency from results first
        avg_lat = get_avg_latency_from_results(config_key)
        if avg_lat:
            latency_map[config_key] = avg_lat
        else:
            # If no results, try to extract from the file directly
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    rlat = extract_timing(content, 'ReadLatency')
                    if rlat:
                        latency_map[config_key] = rlat
            except:
                pass

    # Second pass: generate audit table
    for path in sorted(found_files):
        f_name = os.path.basename(path)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract all parameters from config/cell files
                lrs = extract_resistance(content, 'LRS')
                hrs = extract_resistance(content, 'HRS')
                tcas = extract_timing(content, 'tCAS')
                trcd = extract_timing(content, 'tRCD')
                trp = extract_timing(content, 'tRP')
                rlat = extract_timing(content, 'ReadLatency')
                wlat = extract_timing(content, 'WriteLatency')
                pwr = extract_power(content)
                devs = extract_devices(content)
                
                # For .cfg/.config files, try to get average latency from results
                if not rlat:
                    config_key = f_name.replace(".cfg", "").replace(".cell", "").replace(".config", "")
                    avg_lat = get_avg_latency_from_results(config_key)
                    if avg_lat:
                        rlat = avg_lat
                
                # Try to get power from results if not found in config
                if not pwr:
                    config_name = f_name.replace(".cfg", "").replace(".config", "")
                    pwr = get_avg_power_from_results(config_name)
                
                # Format output
                lrs_v = lrs if lrs else "N/A"
                hrs_v = hrs if hrs else "N/A"
                timing_v = "-".join([x for x in [tcas, trcd, trp] if x]) if (tcas or trcd or trp) else "N/A"
                pwr_v = pwr[:6] if pwr else "N/A"  # Truncate power to 6 chars
                lat_v = f"{float(rlat):.2f}" if rlat and rlat != "N/A" else "N/A"  # Format latency to 2 decimals
                
                status = validate_row(f_name, lrs, hrs, tcas, trcd, trp, rlat, wlat, latency_map)
                
                print(f"| {f_name} | {lrs_v} | {hrs_v} | {timing_v} | {pwr_v} | {lat_v} | {status} |")
        except Exception as e:
            print(f"| {f_name} | ERROR | - | - | - | - | Error: {str(e)[:30]} |")

if __name__ == "__main__":
    audit()
