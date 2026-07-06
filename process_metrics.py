#!/usr/bin/env python3
"""
MBMM Pipeline - Data Processing Stage
Process raw simulation metrics and output pre-calculated intermediate data

This module:
- Parses all stats_*.out files from /results/system/
- Performs centralized metric calculations (EDP, power splits, area density)
- Outputs pre-calculated CSV files for visualization stages
- Single source of truth for all mathematical operations
"""

import re
import glob
import json
import pandas as pd
import numpy as np
from pathlib import Path
from logging_config import setup_logging

logger = setup_logging("process_metrics")

# ============================================================================
# CONFIGURATION: Physical Constants and Baseline Values
# ============================================================================

RESULTS_SYS_DIR = "/home/yuvalk/MBMM/results/system"
OUTPUT_DIR = "/home/yuvalk/MBMM/results"
HARDWARE_METRICS_FILE = "/home/yuvalk/MBMM/results/hardware_metrics.json"

# Load hardware metrics (area, capacity) from extraction stage
HARDWARE_METRICS = {}
try:
    if Path(HARDWARE_METRICS_FILE).exists():
        with open(HARDWARE_METRICS_FILE, 'r') as f:
            HARDWARE_METRICS = json.load(f)
            logger.debug(f"Loaded hardware metrics for {len(HARDWARE_METRICS)} technologies")
except Exception as e:
    logger.warning(f"Could not load hardware metrics: {e}")

# Area Density Baseline (Hybrid-Empirical Approach)
DDR5_MM2_PER_GB = 35.0  # DDR5-4800 empirical baseline

# Clock frequencies for latency normalization (cycles → nanoseconds)
# DDR5-4800 transfers at 4800 MT/s on a DDR (double-data-rate) bus → 2400 MHz clock
# All NVMain ReRAM and PCM configs run at 800 MHz
CLOCK_FREQUENCY_MHZ = {
    'DDR5_4800':          2400,
    '2D_DRAM_example':    2400,
    '3D_DRAM_example':    2400,
    'pcm_microsoft_2009':  800,
    '1T1R_SLC':            800,
    '1T1R_MLC':            800,
    '1S1R_SLC':            800,
    '1S1R_MLC':            800,
}

# Power Decomposition Ratios (Technology-Based)
POWER_SPLIT_RATIOS = {
    'DDR5_4800': {'dynamic': 0.70, 'static': 0.30},
    '2D_DRAM_example': {'dynamic': 0.70, 'static': 0.30},
    '3D_DRAM_example': {'dynamic': 0.70, 'static': 0.30},
    'pcm_microsoft_2009': {'dynamic': 0.65, 'static': 0.35},
    '1T1R_SLC': {'dynamic': 0.60, 'static': 0.40},
    '1T1R_MLC': {'dynamic': 0.60, 'static': 0.40},
    '1S1R_SLC': {'dynamic': 0.65, 'static': 0.35},
    '1S1R_MLC': {'dynamic': 0.65, 'static': 0.35},
}

# ============================================================================
# CLASSIFICATION FUNCTIONS
# ============================================================================

def classify_technology(filename):
    """Classify technology from filename using priority matching."""
    filename_lower = filename.lower()
    
    # Priority order: More specific patterns first
    patterns = [
        ('1T1R_MLC', r'reram.*1t1r.*mlc'),
        ('1T1R_SLC', r'reram.*1t1r.*slc(?!.*mlc)'),
        ('1S1R_MLC', r'reram.*selector.*mlc'),
        ('1S1R_SLC', r'reram.*selector.*slc(?!.*mlc)'),
        ('pcm_microsoft_2009', r'pcm_microsoft_2009'),
        ('PCM', r'pcm'),
        ('DDR5_4800', r'ddr5.*4800'),
        ('3D_DRAM_example', r'3d_dram'),
        ('2D_DRAM_example', r'2d_dram'),
    ]
    
    for tech_name, pattern in patterns:
        if re.search(pattern, filename_lower):
            return tech_name
    
    logger.warning(f"Unknown technology in filename: {filename}")
    return None


def extract_architecture(filename):
    """Extract architecture scale from filename."""
    filename_lower = filename.lower()
    
    if 'full_dimm' in filename_lower:
        return 'full_dimm'
    elif '16chip' in filename_lower:
        return '16chip'
    elif '8chip' in filename_lower:
        return '8chip'
    elif 'single' in filename_lower:
        return 'single'
    
    # Default for DRAM/PCM (no architecture suffix)
    if any(x in filename_lower for x in ['ddr5', '2d_dram', '3d_dram', 'pcm']):
        return 'full_dimm'
    
    logger.warning(f"Unknown architecture in filename: {filename}")
    return None


def extract_benchmark(filename):
    """Extract benchmark name from filename."""
    name = filename.replace('stats_', '').replace('.out', '')
    
    # Remove technology/architecture prefixes to isolate benchmark name
    removal_patterns = [
        'DDR5_4800_DRAM_',
        '2D_DRAM_example_',
        '3D_DRAM_example_',
        'pcm_microsoft_2009_',
    ]
    
    for pattern in removal_patterns:
        if pattern in name:
            return name.replace(pattern, '', 1)
    
    # Handle ReRAM models (reram_22nm_[arch]_[mlc/slc]_[scale]_benchmark)
    if 'reram_22nm' in name:
        for arch in ['full_dimm', '16chip', '8chip', 'single']:
            if arch in name:
                idx = name.find(arch + '_') + len(arch + '_')
                return name[idx:]
    
    return name


# ============================================================================
# METRIC EXTRACTION FUNCTIONS
# ============================================================================

def _extract_latency_stat(content, stat_name):
    """
    Extract a named NVMain latency statistic, averaging across all channels.

    NVMain emits one line per channel: channel0.FRFCFS.<stat_name> <value>
    DDR5-4800 has two sub-channels; single-channel ReRAM/PCM has one.
    Averaging gives a single representative number regardless of channel count.
    """
    pattern = rf'{re.escape(stat_name)}\s+([\d\.eE\-]+)'
    matches = re.findall(pattern, content, re.IGNORECASE)
    if not matches:
        return None
    try:
        values = [float(m) for m in matches]
        return sum(values) / len(values)
    except ValueError:
        return None


def extract_total_execution_cycles(content):
    """
    Extract averageTotalLatency (hardware latency + queue wait) from stats file.

    This is the correct end-to-end latency seen by a memory request.
    Previously the parser used a broad 'average.*latency' regex which matched
    averageLatency first (hardware-only, no queuing), losing the ISPV write-
    torture signal that lives in the queue component.
    """
    return _extract_latency_stat(content, 'averageTotalLatency')


def extract_hw_latency(content):
    """
    Extract averageLatency (pure hardware timing, no queue wait).

    Useful as a secondary column to decompose total latency into
    hardware vs queue components.
    """
    return _extract_latency_stat(content, 'averageLatency')


def extract_queue_latency(content):
    """
    Extract averageQueueLatency (time spent waiting in the FRFCFS queue).

    For write-heavy workloads (OFMAP), ISPV MLC writes back up the queue,
    causing a massive spike here relative to read-heavy (IFMAP) workloads.
    This is the primary empirical proof of the Write-Torture / ISPV penalty.
    """
    return _extract_latency_stat(content, 'averageQueueLatency')


def extract_total_power(content):
    """Extract total system power from stats file."""
    # Pattern: "totalPower" followed by value and optional "W" unit
    pattern = r'totalpower\s+([\d\.eE\-]+)(?:\s*w)?'
    matches = re.findall(pattern, content, re.IGNORECASE)
    
    if matches:
        # Filter for reasonable values (0.01W to 100W for memory systems)
        valid_powers = []
        for match_str in matches:
            try:
                power_val = float(match_str)
                if 0.01 <= power_val <= 100.0:
                    valid_powers.append(power_val)
            except ValueError:
                continue
        
        if valid_powers:
            # Use max: picks the most-loaded rank (rank0), which correctly represents
            # active power even when the workload fits in one rank and others are idle.
            # Median fails for full_dimm configs where 7 of 8 ranks are leakage-only.
            return max(valid_powers)
    
    return None


RERAM_KEY_PREFIX = {
    '1T1R_SLC': 'reram_22nm_1t1r_slc',
    '1T1R_MLC': 'reram_22nm_1t1r_mlc',
    '1S1R_SLC': 'reram_22nm_selector_slc',
    '1S1R_MLC': 'reram_22nm_selector_mlc',
}


def _reram_json_entry(technology_model):
    """Return the first matching hardware_metrics.json entry for a ReRAM tech."""
    if not HARDWARE_METRICS or technology_model not in RERAM_KEY_PREFIX:
        return None
    prefix = RERAM_KEY_PREFIX[technology_model]
    for key, entry in HARDWARE_METRICS.items():
        if key.startswith(prefix):
            return entry
    return None


def extract_area_mm2(content, technology_model):
    """
    Extract silicon area in mm² from hardware_metrics.json.
    DRAM/PCM use fixed ratios and return None here.
    """
    if technology_model in ['DDR5_4800', 'pcm_microsoft_2009', '2D_DRAM_example', '3D_DRAM_example']:
        return None

    entry = _reram_json_entry(technology_model)
    if entry is None:
        logger.error(f"[CRITICAL] hardware_metrics.json lookup failed for {technology_model}")
        return None

    area = entry.get('area_mm2', None)
    if area is None or area <= 0:
        logger.error(f"[CRITICAL] Invalid area in hardware_metrics.json for {technology_model}: {area}")
        return None

    logger.debug(f"Found area for {technology_model}: {area} mm²")
    return area


def extract_physical_capacity_gb(technology_model):
    """
    Return per-chip physical capacity (GB) from hardware_metrics.json.

    NVMain stats report the *simulated system* address space, which varies with
    chip count and does not reflect the single-chip physical capacity needed for
    the area-density ratio.  This function always uses the JSON ground-truth.
    """
    if technology_model in ['DDR5_4800', 'pcm_microsoft_2009', '2D_DRAM_example', '3D_DRAM_example']:
        return None

    entry = _reram_json_entry(technology_model)
    if entry is None:
        logger.error(f"[CRITICAL] hardware_metrics.json lookup failed for capacity of {technology_model}")
        return None

    cap = entry.get('capacity_gb', None)
    if cap is None or cap <= 0:
        logger.error(f"[CRITICAL] Invalid capacity in hardware_metrics.json for {technology_model}: {cap}")
        return None

    logger.debug(f"Found per-chip capacity for {technology_model}: {cap} GB")
    return cap


def extract_capacity_gb(content):
    """
    Extract capacity in GB from NVMain stats output.
    
    NVMain format: "defaultMemory.channel0.FRFCFS capacity is 65536 MB."
    Converts MB to GB automatically.
    """
    
    # Primary pattern: NVMain format "capacity is XXXXX MB"
    patterns = [
        (r'capacity\s+is\s+([\d\.]+)\s*MB', 'MB'),
        (r'capacity\s+is\s+([\d\.]+)\s*GB', 'GB'),
        (r'Capacity\s*:\s*([\d\.]+)(MB|GB|KB)', None),  # NVSim format
        (r'capacity\s*[:=]\s*([\d\.]+)\s*g?b', 'GB'),
    ]
    
    for pattern, unit in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            try:
                if unit is None:
                    # Handle (value, unit) tuple from second pattern
                    val, matched_unit = float(matches[0][0]), matches[0][1]
                    if matched_unit.upper() == 'MB':
                        return val / 1024.0
                    elif matched_unit.upper() == 'GB':
                        return val
                    elif matched_unit.upper() == 'KB':
                        return val / (1024.0**2)
                else:
                    val = float(matches[0])
                    if unit == 'MB':
                        return val / 1024.0
                    elif unit == 'GB':
                        return val
                    elif unit == 'KB':
                        return val / (1024.0**2)
            except (ValueError, IndexError, TypeError) as e:
                logger.debug(f"Error parsing capacity with pattern {pattern}: {e}")
                continue
    
    logger.error(f"[CRITICAL] Capacity extraction failed from stats file")
    return None


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def decompose_power(power, technology):
    """Decompose total power into dynamic and static components."""
    if technology not in POWER_SPLIT_RATIOS:
        # Default to ReRAM 1S1R ratios
        ratios = POWER_SPLIT_RATIOS['1S1R_SLC']
        logger.debug(f"Technology {technology} not in power split table, using default")
    else:
        ratios = POWER_SPLIT_RATIOS[technology]
    
    dynamic = power * ratios['dynamic']
    static = power * ratios['static']
    
    return dynamic, static


def calculate_pdp(cycles, power):
    """Calculate Power-Delay Product: Total_Execution_Cycles × Total_System_Power."""
    if cycles > 0 and power > 0:
        return cycles * power
    return 0.0


def calculate_latency_ns(cycles, technology):
    """
    Convert raw cycle count to nanoseconds using the technology clock domain.
    Formula: latency_ns = cycles * (1000 / frequency_mhz)
    """
    freq_mhz = CLOCK_FREQUENCY_MHZ.get(technology, 800)
    return cycles * (1000.0 / freq_mhz)


def calculate_area_density_ratio(area_mm2, capacity_gb, technology):
    """
    Calculate normalized area density ratio (Higher is Better).

    Formula: DDR5_baseline_mm2_per_GB / (tech_mm2_per_GB)
    DDR5 = 1.0.  Values > 1.0 are denser than DDR5; values < 1.0 are less dense.

    For ReRAM: extracted from hardware_metrics.json via hybrid-empirical method.
    For DRAM/PCM: fixed empirical ratios (inverted from the mm²/GB baseline).
    """

    # Fixed ratios expressed as density relative to DDR5 (higher = denser)
    # PCM 0.80 in the old mm²/GB system → inverted: 1/0.80 = 1.25
    fixed_ratios = {
        'DDR5_4800': 1.00,
        'pcm_microsoft_2009': 1.25,
        '2D_DRAM_example': 1.053,
        '3D_DRAM_example': 1.176,
    }

    if technology in fixed_ratios:
        return fixed_ratios[technology]

    # For ReRAM: Require successful extraction (STRICT ERROR LOGGING)
    if area_mm2 is None or capacity_gb is None:
        logger.error(f"[CRITICAL] FAILED to extract area/capacity for {technology}. "
                    f"Area={area_mm2}, Capacity={capacity_gb}. Aborting calculation.")
        return None

    if capacity_gb <= 0:
        logger.error(f"[CRITICAL] Invalid capacity for {technology}: {capacity_gb} GB")
        return None

    if area_mm2 <= 0:
        logger.error(f"[CRITICAL] Invalid area for {technology}: {area_mm2} mm²")
        return None

    # Inverted: DDR5_baseline / tech → higher means denser than DDR5
    reram_mm2_per_gb = area_mm2 / capacity_gb
    ratio = DDR5_MM2_PER_GB / reram_mm2_per_gb

    logger.debug(f"{technology}: Area={area_mm2:.2f} mm², Capacity={capacity_gb:.2f} GB, "
                f"Density ratio = {DDR5_MM2_PER_GB}/({area_mm2:.2f}/{capacity_gb:.2f}) = {ratio:.4f}")

    return ratio


# ============================================================================
# PARSING AND AGGREGATION
# ============================================================================

def parse_raw_stats():
    """Parse all stats_*.out files and extract raw metrics."""
    
    logger.info("="*80)
    logger.info("STAGE 6: DATA PROCESSING - Metric Extraction & Calculation")
    logger.info("="*80)
    logger.info(f"\nScanning for stats files in: {RESULTS_SYS_DIR}")
    
    stat_files = sorted(glob.glob(f"{RESULTS_SYS_DIR}/stats_*.out"))
    
    if not stat_files:
        logger.error(f"No stats files found in {RESULTS_SYS_DIR}")
        return []
    
    logger.info(f"Found {len(stat_files)} stats files\n")
    
    data = []
    # MLPerf excluded: all stats_*_mlperf_inference.out runs (2026-03-29) hit trace
    # EOF at cycle 0 with zero requests — mlperf_inference.nvt was missing/empty at
    # launch. Raw source survives at simulators/gem5/m5out/mlperf_raw.txt if we ever
    # regenerate the .nvt and re-run. See session audit 2026-07-06.
    excluded_benchmarks = ['mlperf_inference', 'mlperf']
    
    for filepath in stat_files:
        filename = Path(filepath).name
        
        # Classify
        tech = classify_technology(filename)
        if not tech:
            logger.debug(f"⊘ {filename}: Unknown technology, skipping")
            continue
        
        arch = extract_architecture(filename)
        if not arch:
            logger.debug(f"⊘ {filename}: Unknown architecture, skipping")
            continue
        
        bench = extract_benchmark(filename)
        if any(excl in bench for excl in excluded_benchmarks):
            logger.debug(f"⊘ {filename}: Excluded benchmark, skipping")
            continue
        
        # Parse file
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            cycles = extract_total_execution_cycles(content)
            power = extract_total_power(content)

            if cycles is None or power is None or cycles <= 0 or power <= 0:
                logger.debug(f"⊘ {filename}: Missing or invalid metrics")
                continue

            hw_latency = extract_hw_latency(content)
            queue_latency = extract_queue_latency(content)

            # Extract area and per-chip physical capacity for ReRAM density ratio.
            # Both come from hardware_metrics.json so they are at the same scale.
            # extract_capacity_gb() reads the NVMain simulated address space which
            # scales with chip count and must NOT be used for the density formula.
            area_mm2 = extract_area_mm2(content, tech)
            capacity_gb = extract_physical_capacity_gb(tech)

            data.append({
                'filename': filename,
                'technology': tech,
                'architecture': arch,
                'benchmark': bench,
                'total_execution_cycles': cycles,
                'hw_latency_cycles': hw_latency,
                'queue_latency_cycles': queue_latency,
                'power': power,
                'area_mm2': area_mm2,
                'capacity_gb': capacity_gb,
            })
            
            if area_mm2 is not None and capacity_gb is not None:
                logger.debug(f"✓ {filename}: Tech={tech:15s} | Arch={arch:10s} | "
                            f"TotalCyc={cycles:10.2f} | HWCyc={hw_latency:8.2f} | QCyc={queue_latency:8.2f} | "
                            f"Power={power:10.4f}W | Area={area_mm2:.2f}mm² | Cap={capacity_gb:.2f}GB")
            else:
                logger.warning(f"⚠ {filename}: Tech={tech:15s} | Arch={arch:10s} | "
                              f"TotalCyc={cycles:10.2f} | HWCyc={hw_latency:8.2f} | QCyc={queue_latency:8.2f} | "
                              f"Power={power:10.4f}W | MISSING AREA/CAPACITY DATA")
        
        except Exception as e:
            logger.error(f"✗ {filename}: Failed to parse - {str(e)}")
            continue
    
    logger.info(f"\nTotal data points extracted: {len(data)}\n")
    return data


def process_metrics(raw_data):
    """Calculate derived metrics from raw data."""
    
    logger.info("Calculating derived metrics...")
    
    processed = []
    
    for record in raw_data:
        tech = record['technology']
        power = record['power']
        cycles = record['total_execution_cycles']
        
        # Power decomposition
        dyn_power, stat_power = decompose_power(power, tech)

        # PDP calculation (uses averageTotalLatency which now includes queue wait)
        edp = calculate_pdp(cycles, power)

        # Latency normalization: cycles → nanoseconds (clock-domain corrected)
        latency_ns = calculate_latency_ns(cycles, tech)
        hw_latency_ns = (calculate_latency_ns(record['hw_latency_cycles'], tech)
                         if record['hw_latency_cycles'] is not None else None)
        queue_latency_ns = (calculate_latency_ns(record['queue_latency_cycles'], tech)
                            if record['queue_latency_cycles'] is not None else None)

        # Area density ratio (ReRAM hybrid-empirical)
        area_ratio = calculate_area_density_ratio(
            record['area_mm2'],
            record['capacity_gb'],
            tech
        )

        # If area extraction failed for ReRAM, use fallback but log it
        if area_ratio is None:
            if tech in ['1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC']:
                logger.error(f"[SKIP-WITH-FALLBACK] {tech}: Using 1.0 ratio due to extraction failure")
                area_ratio = 1.0
            else:
                area_ratio = 1.0  # Safe fallback for DRAM/PCM (shouldn't reach here)

        processed.append({
            'Technology': tech,
            'Architecture': record['architecture'],
            'Benchmark': record['benchmark'],
            'Total_Execution_Cycles': cycles,
            'HW_Latency_Cycles': record['hw_latency_cycles'],
            'Queue_Latency_Cycles': record['queue_latency_cycles'],
            'Latency_ns': latency_ns,
            'HW_Latency_ns': hw_latency_ns,
            'Queue_Latency_ns': queue_latency_ns,
            'Power': power,
            'Dynamic_Power': dyn_power,
            'Static_Power': stat_power,
            'PDP': edp,
            'Area_Density_Ratio': area_ratio,
        })
    
    logger.info(f"Processed {len(processed)} data points\n")
    return processed


def calculate_geometric_mean_pdp(df_metrics):
    """Calculate geometric mean PDP per technology — full DIMM only."""

    logger.info("Calculating geometric mean PDP per technology (full_dimm only)...")

    # Filter to full_dimm for an apples-to-apples comparison.
    # DDR5 and PCM only have full_dimm records; including single/8chip/16chip
    # ReRAM configs would inflate their averages relative to the DRAM baselines.
    df_full_dimm = df_metrics[df_metrics['Architecture'] == 'full_dimm']

    geometric_means = {}

    for tech in df_full_dimm['Technology'].unique():
        tech_df = df_full_dimm[df_full_dimm['Technology'] == tech]
        edp_values = tech_df['PDP'].values

        if len(edp_values) > 0:
            # Geometric mean = exp(mean(ln(values)))
            geom_mean = np.exp(np.mean(np.log(edp_values)))
            geometric_means[tech] = geom_mean

            logger.debug(f"  {tech:20s}: {len(edp_values):2d} data points, "
                        f"Geometric Mean PDP = {geom_mean:12.2f}")

    logger.info(f"Calculated geometric means for {len(geometric_means)} technologies\n")
    return geometric_means


# ============================================================================
# OUTPUT FUNCTIONS
# ============================================================================

def save_bar_chart_metrics(df_processed):
    """Save metrics for bar chart visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_bar_chart_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for bar charts (includes latency decomposition for write-torture analysis)
    df_output = df_processed[[
        'Technology', 'Architecture', 'Benchmark',
        'Total_Execution_Cycles', 'HW_Latency_Cycles', 'Queue_Latency_Cycles',
        'Latency_ns', 'HW_Latency_ns', 'Queue_Latency_ns',
        'Power', 'Dynamic_Power', 'Static_Power', 'PDP'
    ]]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved bar chart metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Benchmarks: {df_output['Benchmark'].nunique()}")


def save_pareto_metrics(df_processed):
    """Save metrics for Pareto frontier visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_pareto_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for Pareto plots (all architectures)
    df_output = df_processed[[
        'Technology', 'Architecture', 'Benchmark',
        'Total_Execution_Cycles', 'Latency_ns', 'Power'
    ]]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved Pareto metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Architectures: {df_output['Architecture'].nunique()}")


def save_hero_metrics(df_processed):
    """Save metrics for hero graph visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_hero_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for hero graphs (include write-torture decomposition + area density)
    df_output = df_processed[[
        'Technology', 'Benchmark',
        'Total_Execution_Cycles', 'HW_Latency_Cycles', 'Queue_Latency_Cycles',
        'Power', 'PDP', 'Area_Density_Ratio'
    ]]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved hero metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Technologies: {df_output['Technology'].nunique()}")


def save_geometric_means(geometric_means_dict):
    """Save pre-calculated geometric mean PDP values."""
    
    output_file = Path(OUTPUT_DIR) / "processed_geometric_means.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df_output = pd.DataFrame(
        list(geometric_means_dict.items()),
        columns=['Technology', 'Geometric_Mean_PDP']
    )
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved geometric means: {output_file}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Execute data processing pipeline."""
    
    try:
        # Step 1: Parse raw stats files
        raw_data = parse_raw_stats()
        
        if not raw_data:
            logger.error("No data extracted from stats files")
            return False
        
        # Step 2: Convert to DataFrame for processing
        df_processed = pd.DataFrame(process_metrics(raw_data))
        
        # Step 3: Calculate geometric means
        geometric_means = calculate_geometric_mean_pdp(df_processed)
        
        # Step 4: Output intermediate CSV files
        logger.info("Saving intermediate metric files...")
        
        save_bar_chart_metrics(df_processed)
        save_pareto_metrics(df_processed)
        save_hero_metrics(df_processed)
        save_geometric_means(geometric_means)
        
        logger.info("="*80)
        logger.info("✅ DATA PROCESSING COMPLETE")
        logger.info("="*80)
        logger.info("\nGenerated intermediate metric files:")
        logger.info("  - processed_bar_chart_metrics.csv")
        logger.info("  - processed_pareto_metrics.csv")
        logger.info("  - processed_hero_metrics.csv")
        logger.info("  - processed_geometric_means.csv")
        logger.info("\nReady for visualization stage.\n")
        
        return True
    
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
