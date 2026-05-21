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

# Area Density Baseline (Hybrid-Empirical Approach)
DDR5_MM2_PER_GB = 35.0  # DDR5-4800 empirical baseline

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

def extract_total_execution_cycles(content):
    """Extract total execution cycles (average total latency) from stats file."""
    # Pattern: "averageTotalLatency" followed by a numeric value
    pattern = r'average.*?latency\s+([\d\.eE\-]+)'
    matches = re.findall(pattern, content, re.IGNORECASE)
    
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            return None
    
    return None


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
            # Use median to be robust to outliers
            return sorted(valid_powers)[len(valid_powers) // 2]
    
    return None


def extract_area_mm2(content):
    """Extract silicon area in mm² from NVSim output."""
    # Pattern: "Area" in mm² notation
    patterns = [
        r'Total Area\s*[:=]\s*([\d\.eE\-]+)\s*mm',
        r'area\s*[:=]\s*([\d\.eE\-]+)\s*mm',
        r'mm\s*2\s*[:=]\s*([\d\.eE\-]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                continue
    
    return None


def extract_capacity_gb(content):
    """Extract capacity in GB from NVSim configuration."""
    # Pattern: Capacity in GB notation
    patterns = [
        r'Capacity\s*[:=]\s*([\d\.eE\-]+)\s*(?:Gb|GB)',
        r'capacity\s*[:=]\s*([\d\.]+)\s*g?b',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            try:
                val = float(matches[0])
                # Convert Gb to GB if needed (Gb / 8 = GB)
                if val > 100:  # Likely in Gb
                    val = val / 8.0
                return val
            except ValueError:
                continue
    
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


def calculate_edp(cycles, power):
    """Calculate Energy-Delay Product: Total_Execution_Cycles × Total_System_Power."""
    if cycles > 0 and power > 0:
        return cycles * power
    return 0.0


def calculate_area_density_ratio(area_mm2, capacity_gb, technology):
    """
    Calculate area density ratio using hybrid-empirical approach.
    
    For ReRAM: Extract actual area/capacity from NVSim, normalize to DDR5 baseline.
    For DRAM/PCM: Use fixed empirical ratios.
    """
    
    # Fixed ratios for DRAM and PCM (empirically determined)
    fixed_ratios = {
        'DDR5_4800': 1.00,
        'pcm_microsoft_2009': 0.80,
        '2D_DRAM_example': 0.95,
        '3D_DRAM_example': 0.85,
    }
    
    if technology in fixed_ratios:
        return fixed_ratios[technology]
    
    # For ReRAM: Calculate from extracted metrics
    if area_mm2 is not None and capacity_gb is not None and capacity_gb > 0:
        reram_mm2_per_gb = area_mm2 / capacity_gb
        ratio = reram_mm2_per_gb / DDR5_MM2_PER_GB
        return ratio
    
    # Fallback: Use design-based estimate
    logger.warning(f"Could not extract area/capacity for {technology}, using fallback")
    return 1.0  # Default to DDR5 equivalent


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
            
            # Extract area and capacity for ReRAM density calculation
            area_mm2 = extract_area_mm2(content)
            capacity_gb = extract_capacity_gb(content)
            
            data.append({
                'filename': filename,
                'technology': tech,
                'architecture': arch,
                'benchmark': bench,
                'total_execution_cycles': cycles,
                'power': power,
                'area_mm2': area_mm2,
                'capacity_gb': capacity_gb,
            })
            
            logger.debug(f"✓ {filename}: Tech={tech:15s} | Arch={arch:10s} | "
                        f"Cycles={cycles:10.2f} | Power={power:10.4f}W")
        
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
        
        # EDP calculation
        edp = calculate_edp(cycles, power)
        
        # Area density ratio (ReRAM hybrid-empirical)
        area_ratio = calculate_area_density_ratio(
            record['area_mm2'],
            record['capacity_gb'],
            tech
        )
        
        processed.append({
            'Technology': tech,
            'Architecture': record['architecture'],
            'Benchmark': record['benchmark'],
            'Total_Execution_Cycles': cycles,
            'Power': power,
            'Dynamic_Power': dyn_power,
            'Static_Power': stat_power,
            'EDP': edp,
            'Area_Density_Ratio': area_ratio,
        })
    
    logger.info(f"Processed {len(processed)} data points\n")
    return processed


def calculate_geometric_mean_edp(df_metrics):
    """Calculate geometric mean EDP per technology."""
    
    logger.info("Calculating geometric mean EDP per technology...")
    
    geometric_means = {}
    
    for tech in df_metrics['Technology'].unique():
        tech_df = df_metrics[df_metrics['Technology'] == tech]
        edp_values = tech_df['EDP'].values
        
        if len(edp_values) > 0:
            # Geometric mean = exp(mean(ln(values)))
            geom_mean = np.exp(np.mean(np.log(edp_values)))
            geometric_means[tech] = geom_mean
            
            logger.debug(f"  {tech:20s}: {len(edp_values):2d} data points, "
                        f"Geometric Mean EDP = {geom_mean:12.2f}")
    
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
    
    # Select columns for bar charts
    df_output = df_processed[[
        'Technology', 'Architecture', 'Benchmark',
        'Total_Execution_Cycles', 'Power',
        'Dynamic_Power', 'Static_Power', 'EDP'
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
        'Total_Execution_Cycles', 'Power'
    ]]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved Pareto metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Architectures: {df_output['Architecture'].nunique()}")


def save_hero_metrics(df_processed):
    """Save metrics for hero graph visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_hero_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for hero graphs (include area density ratio)
    df_output = df_processed[[
        'Technology', 'Benchmark',
        'Total_Execution_Cycles', 'Power', 'EDP', 'Area_Density_Ratio'
    ]]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved hero metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Technologies: {df_output['Technology'].nunique()}")


def save_geometric_means(geometric_means_dict):
    """Save pre-calculated geometric mean EDP values."""
    
    output_file = Path(OUTPUT_DIR) / "processed_geometric_means.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df_output = pd.DataFrame(
        list(geometric_means_dict.items()),
        columns=['Technology', 'Geometric_Mean_EDP']
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
        geometric_means = calculate_geometric_mean_edp(df_processed)
        
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
