# MBMM Pipeline Architectural Refactor Proposal
## Separation of Concerns: Data Processing vs. Visualization

**Date:** May 20, 2026  
**Status:** PROPOSAL (Awaiting Approval)

---

## Executive Summary

Current pipeline violates separation of concerns:
- **Visualizers parse raw data** and perform complex calculations
- **Math is scattered** across three separate visualization scripts
- **Logging is inconsistent** (mix of print statements and file logging)
- **Code duplication** across visualize_results.py, visualize_pareto.py, visualize_hero_graphs.py

**Proposed Solution:** Extract all data processing into a single **process_metrics.py** stage that produces clean intermediate CSV files. Visualizers become "dumb" plotters that only consume pre-calculated data.

---

## 1. Python Logging Strategy

### Current State
- `mbmm_master.py`: Uses `logging.basicConfig()` with file handler
- `visualize_results.py`: Uses `print()` statements for console output
- `visualize_pareto.py`: Uses `print()` statements for console output
- `visualize_hero_graphs.py`: Uses `print()` statements for console output
- **Problem:** Inconsistent logging, difficult to track execution flow

### Proposed Implementation

**File:** `logging_config.py` (new utility module)

```python
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(stage_name, log_dir="results"):
    """
    Configure unified logging for all pipeline stages.
    
    Returns:
        logger: Configured logger that writes to both console and file
    
    Features:
    - Console output: INFO and higher levels
    - File output: DEBUG and higher levels
    - Timestamped log files per stage
    - Automatic directory creation
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log file per stage
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{stage_name}_{timestamp}.log"
    
    # Configure logger
    logger = logging.getLogger(stage_name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG and above)
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger

# Example usage in any module:
# from logging_config import setup_logging
# logger = setup_logging("process_metrics")
# logger.info("Starting metric processing...")
```

**Integration Points:**
- `mbmm_master.py`: Calls `setup_logging("mbmm_master")`
- `process_metrics.py`: Calls `setup_logging("process_metrics")`
- `visualize_results.py`: Calls `setup_logging("visualize_bar_charts")`
- `visualize_pareto.py`: Calls `setup_logging("visualize_pareto")`
- `visualize_hero_graphs.py`: Calls `setup_logging("visualize_hero_graphs")`

**Output Structure:**
```
results/
├── mbmm_master_20260520_140530.log
├── process_metrics_20260520_140535.log
├── visualize_bar_charts_20260520_140540.log
├── visualize_pareto_20260520_140545.log
├── visualize_hero_graphs_20260520_140550.log
└── final_graphs/
```

---

## 2. New Data Processing Stage: `process_metrics.py`

### Purpose
**SINGLE SOURCE OF TRUTH** for all data extraction and mathematical calculations.

### Input
- Raw stats files: `/home/yuvalk/MBMM/results/system/stats_*.out`

### Output
Three intermediate CSV files with pre-calculated metrics:

1. **`processed_bar_chart_metrics.csv`**
   - Columns: `Technology`, `Benchmark`, `Architecture`, `Total_Execution_Cycles`, `Power`, `Dynamic_Power`, `Static_Power`, `EDP`
   - Used by: `visualize_results.py` (bar charts only)

2. **`processed_pareto_metrics.csv`**
   - Columns: `Technology`, `Benchmark`, `Architecture`, `Total_Execution_Cycles`, `Power`
   - Used by: `visualize_pareto.py` (Pareto frontier plots)

3. **`processed_hero_metrics.csv`**
   - Columns: `Technology`, `Benchmark`, `Architecture`, `Total_Execution_Cycles`, `Power`, `EDP`
   - Used by: `visualize_hero_graphs.py` (hero graphs + geometric mean calculations)

### Mathematical Operations (All Centralized Here)

#### A. Raw Data Extraction
```
INPUTS: stats_*.out files
- Extract Total_Execution_Cycles from "average.*?latency" field
- Extract Total_System_Power from "totalpower" field
- Classify Technology (1T1R_SLC, 1S1R_SLC, DDR5_4800, PCM, etc.)
- Extract Architecture (single, 8chip, 16chip, full_dimm)
- Extract Benchmark name
```

#### B. Power Decomposition (Technology-Based Split)
```
ALGORITHM:
IF technology in [DDR5, 2D_DRAM, 3D_DRAM]:
    dynamic_power = total_power × 0.70
    static_power = total_power × 0.30
ELSE IF technology == PCM:
    dynamic_power = total_power × 0.65
    static_power = total_power × 0.35
ELSE IF technology contains "1T1R":
    dynamic_power = total_power × 0.60  # Higher transistor leakage
    static_power = total_power × 0.40
ELSE IF technology contains "1S1R":
    dynamic_power = total_power × 0.65  # Lower selector leakage
    static_power = total_power × 0.35
```

#### C. EDP Calculation (Consistent Formula)
```
FORMULA: EDP = Total_Execution_Cycles × Total_System_Power
APPLIES TO: All architectures, all technologies
USED BY: Bar charts, Pareto plots, Hero graphs (for geometric mean)
```

#### D. Hero Graph Calculations
```
GEOMETRIC MEAN EDP:
  FOR EACH technology:
    geom_mean_edp = exp(mean(ln(edp_values_across_all_benchmarks)))

AREA DENSITY (F² Scaling):
  BASELINE_DDR5 = 1.00
  F2_1T1R = 20.0
  F2_1S1R = 4.0
  BASE_1T1R_RATIO = 0.90
  
  area_1T1R_SLC = BASE_1T1R_RATIO
  area_1S1R_SLC = BASE_1T1R_RATIO × (F2_1S1R / F2_1T1R)  # 5× shrink
  area_1T1R_MLC = BASE_1T1R_RATIO / 2.0                  # 2 bits/cell
  area_1S1R_MLC = (BASE_1T1R_RATIO × (F2_1S1R / F2_1T1R)) / 2.0  # 5× + 2bits
```

### Pseudocode Structure

```python
# process_metrics.py

import logging
from logging_config import setup_logging
import pandas as pd
from pathlib import Path

logger = setup_logging("process_metrics")

def main():
    logger.info("="*80)
    logger.info("DATA PROCESSING STAGE: Extract & Calculate Metrics")
    logger.info("="*80)
    
    # Step 1: Parse all raw stats files
    logger.info("Parsing stats_*.out files from /results/system/...")
    raw_data = parse_raw_stats()
    
    # Step 2: Classify technologies and architectures
    logger.info("Classifying technologies and architectures...")
    classified_data = classify_data(raw_data)
    
    # Step 3: Calculate power decomposition
    logger.info("Computing dynamic/static power splits...")
    with_power_split = decompose_power(classified_data)
    
    # Step 4: Calculate EDP (consistent formula)
    logger.info("Computing EDP metrics...")
    with_edp = calculate_edp(with_power_split)
    
    # Step 5: Generate intermediate CSV files
    logger.info("Writing intermediate metric files...")
    save_bar_chart_metrics(with_edp)
    save_pareto_metrics(with_edp)
    save_hero_metrics(with_edp)
    
    logger.info("✅ DATA PROCESSING COMPLETE")
    logger.info("Generated: processed_*.csv files")
```

---

## 3. Refactored Visualization Stage

### Before: Monolithic Visualizers

```
visualize_results.py
├── archive_old_graphs()
├── classify_technology()
├── extract_architecture()
├── extract_benchmark()
├── parse_nvmain_stats()          ← DATA EXTRACTION (MATH HERE)
├── generate_bar_charts()         ← PLOTTING ONLY
└── calls visualize_pareto_main() and visualize_hero_graphs functions

visualize_pareto.py
├── classify_technology()         ← DUPLICATED
├── extract_architecture()        ← DUPLICATED
├── extract_benchmark()           ← DUPLICATED
├── parse_results_files()         ← DATA EXTRACTION (MATH HERE)
└── create_gold_master_plot()     ← PLOTTING ONLY

visualize_hero_graphs.py
├── classify_technology()         ← DUPLICATED
├── extract_architecture()        ← DUPLICATED
├── extract_benchmark()           ← DUPLICATED
├── parse_all_stats_files()       ← DATA EXTRACTION (MATH HERE)
├── calculate_geometric_mean_edp()← CALCULATION (MOVED)
├── generate_hero_area_density()  ← PLOTTING ONLY
└── generate_hero_average_edp()   ← PLOTTING ONLY
```

### After: Clean Separation

```
process_metrics.py (NEW)
├── parse_raw_stats()
├── classify_data()
├── decompose_power()
├── calculate_edp()
├── calculate_geometric_mean_edp()    ← MOVED from hero_graphs
├── save_bar_chart_metrics()
├── save_pareto_metrics()
└── save_hero_metrics()

visualize_results.py (REFACTORED)
├── archive_old_graphs()
├── load_bar_chart_metrics()          ← READ CSV
└── generate_bar_charts()             ← PLOT ONLY

visualize_pareto.py (REFACTORED)
├── load_pareto_metrics()             ← READ CSV
└── create_gold_master_plot()         ← PLOT ONLY

visualize_hero_graphs.py (REFACTORED)
├── load_hero_metrics()               ← READ CSV
├── generate_hero_area_density()      ← PLOT ONLY
└── generate_hero_average_edp()       ← PLOT ONLY
```

### Key Changes per Visualizer

#### visualize_results.py
**Remove:**
- `classify_technology()`, `extract_architecture()`, `extract_benchmark()`
- `parse_nvmain_stats()` entire function

**Add:**
```python
def load_bar_chart_metrics():
    """Load pre-calculated metrics from CSV."""
    metrics_file = Path("results") / "processed_bar_chart_metrics.csv"
    logger.info(f"Loading metrics from {metrics_file}")
    df = pd.read_csv(metrics_file)
    logger.info(f"Loaded {len(df)} data points across {df['Benchmark'].nunique()} benchmarks")
    return df
```

**Result:** ~70% of code removed. Only plotting remains.

#### visualize_pareto.py
**Remove:**
- All data parsing functions (`classify_technology`, etc.)
- `parse_results_files()` entire function

**Add:**
```python
def load_pareto_metrics():
    """Load pre-calculated Pareto frontier metrics from CSV."""
    metrics_file = Path("results") / "processed_pareto_metrics.csv"
    logger.info(f"Loading Pareto metrics from {metrics_file}")
    df = pd.read_csv(metrics_file)
    benchmark_data = df.groupby('Benchmark').apply(lambda x: x.to_dict('records')).to_dict()
    logger.info(f"Loaded data for {len(benchmark_data)} benchmarks")
    return benchmark_data
```

**Result:** ~60% of code removed. Only Pareto plotting remains.

#### visualize_hero_graphs.py
**Remove:**
- All data parsing functions (`classify_technology`, etc.)
- `parse_all_stats_files()` entire function
- `calculate_geometric_mean_edp()` entire function (moved to process_metrics.py)

**Add:**
```python
def load_hero_metrics():
    """Load pre-calculated hero graph metrics from CSV."""
    metrics_file = Path("results") / "processed_hero_metrics.csv"
    logger.info(f"Loading hero metrics from {metrics_file}")
    return pd.read_csv(metrics_file)

def load_geometric_means():
    """Load pre-calculated geometric mean EDP values from CSV."""
    means_file = Path("results") / "processed_geometric_means.csv"
    logger.info(f"Loading geometric means from {means_file}")
    geom_means = pd.read_csv(means_file)
    return dict(zip(geom_means['Technology'], geom_means['Geometric_Mean_EDP']))
```

**Result:** ~75% of code removed. Only plotting remains.

---

## 4. Integration into mbmm_master.py

### Current Flow (Stage 6)
```
visualize_results.py
  ↓
visualize_pareto.py
  ↓
visualize_hero_graphs.py
```

### Proposed Flow (Stages 6-7)

```
STAGE 6: METRIC PROCESSING
├── process_metrics.py
│   ├── Parse stats_*.out files
│   ├── Perform all calculations
│   └── Output: processed_*.csv
│
STAGE 7: VISUALIZATION (Three parallel visualizers - no dependencies)
├── visualize_results.py      (reads processed_bar_chart_metrics.csv)
├── visualize_pareto.py       (reads processed_pareto_metrics.csv)
└── visualize_hero_graphs.py  (reads processed_hero_metrics.csv)
```

### mbmm_master.py Changes

**Current:**
```python
# Stage 6: Triple-track Visualization
print("[EXECUTION] Generating Diagnostic Bar Charts...")
subprocess.run([sys.executable, "visualize_results.py"], check=False)

print("[EXECUTION] Generating Pareto Frontiers...")
subprocess.run([sys.executable, "visualize_pareto.py"], check=False)

print("[EXECUTION] Generating Hero Graphs...")
subprocess.run([sys.executable, "visualize_hero_graphs.py"], check=False)
```

**Proposed:**
```python
# Stage 6: Data Processing (centralized metric calculation)
print("\n" + "="*80)
print("STAGE 6: METRIC PROCESSING")
print("="*80)
print("\n[EXECUTION] Extracting and calculating metrics...")
try:
    result = subprocess.run(
        [sys.executable, "process_metrics.py"],
        capture_output=True,
        text=True,
        timeout=600,
        check=True
    )
    if result.stdout:
        print(result.stdout)
    logger.info("Stage 6 complete: metrics processed")
except subprocess.CalledProcessError as e:
    logger.error(f"Metric processing failed: {e}")
    logger.error(f"STDERR: {e.stderr}")
    raise

# Stage 7: Visualization (three independent plotters)
print("\n" + "="*80)
print("STAGE 7: VISUALIZATION (BAR CHARTS + PARETO + HERO GRAPHS)")
print("="*80)

tasks = [
    ("Bar Charts", "visualize_results.py"),
    ("Pareto Frontiers", "visualize_pareto.py"),
    ("Hero Graphs", "visualize_hero_graphs.py")
]

for task_name, script in tasks:
    print(f"\n[EXECUTION] Generating {task_name}...")
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )
        if result.stdout:
            print(result.stdout)
        logger.info(f"{task_name} generated successfully")
    except Exception as e:
        logger.warning(f"{task_name} generation warning: {e}")

print("\n[EXECUTION] Stage 7 visualization complete")
print("="*80)
```

---

## 5. Data File Specifications

### `processed_bar_chart_metrics.csv`
```
Technology,Architecture,Benchmark,Total_Execution_Cycles,Power,Dynamic_Power,Static_Power,EDP
DDR5_4800,full_dimm,gcc_spec2017,1000.50,0.3200,0.2240,0.0960,320.160
DDR5_4800,full_dimm,lbm_spec2017,950.25,0.2800,0.1960,0.0840,266.070
1T1R_SLC,full_dimm,gcc_spec2017,800.00,0.4100,0.2460,0.1640,328.000
1T1R_SLC,single,gcc_spec2017,850.00,0.3900,0.2340,0.1560,331.500
1S1R_SLC,full_dimm,gcc_spec2017,600.00,0.2500,0.1625,0.0875,150.000
...
```

### `processed_pareto_metrics.csv`
```
Technology,Architecture,Benchmark,Total_Execution_Cycles,Power
DDR5_4800,full_dimm,gcc_spec2017,1000.50,0.3200
DDR5_4800,full_dimm,lbm_spec2017,950.25,0.2800
1T1R_SLC,full_dimm,gcc_spec2017,800.00,0.4100
1T1R_SLC,8chip,gcc_spec2017,850.00,0.3900
1S1R_SLC,full_dimm,gcc_spec2017,600.00,0.2500
...
```

### `processed_hero_metrics.csv`
```
Technology,Benchmark,Total_Execution_Cycles,Power,EDP
DDR5_4800,gcc_spec2017,1000.50,0.3200,320.160
DDR5_4800,lbm_spec2017,950.25,0.2800,266.070
1T1R_SLC,gcc_spec2017,800.00,0.4100,328.000
1S1R_SLC,gcc_spec2017,600.00,0.2500,150.000
PCM,gcc_spec2017,900.00,0.2900,261.000
...
```

### `processed_geometric_means.csv` (for hero graphs)
```
Technology,Geometric_Mean_EDP
DDR5_4800,285.450
PCM,234.200
2D_DRAM_example,278.900
3D_DRAM_example,265.300
1T1R_SLC,320.000
1S1R_SLC,145.500
1T1R_MLC,162.000
1S1R_MLC,72.500
```

---

## 6. Benefits of This Architecture

| Aspect | Before | After |
|--------|--------|-------|
| **Code Duplication** | 3 copies of classify_technology, extract_architecture, etc. | Single source of truth |
| **Test Coverage** | Math scattered across visualizers | Can unit test process_metrics.py independently |
| **Maintainability** | Bug fix in power split requires changes in 3 files | Single fix in process_metrics.py |
| **Reproducibility** | Visualization can re-run and re-calculate (non-deterministic) | Metrics locked in CSV, visualizers deterministic |
| **Performance** | Re-parse stats files on every visualization run | Parse once, visualize multiple times |
| **Separation of Concerns** | Visualizers do math AND plotting (violation) | Data processing ≠ plotting (clean split) |
| **Debugging** | Unclear which visualizer's calculation is wrong | process_metrics.py is the single point of truth |
| **Python Logging** | Inconsistent print() statements | Unified logger with file + console output |

---

## 7. Implementation Roadmap

### Phase 1: Create Logging Infrastructure
- Create `logging_config.py`
- Update `mbmm_master.py` to use logging
- Update existing visualizers to use logging (no other changes)
- **Deliverable:** Unified logging across pipeline

### Phase 2: Create Data Processing Pipeline
- Create `process_metrics.py`
- Implement all data extraction and calculation logic
- Output three intermediate CSV files
- **Deliverable:** CSV files with pre-calculated metrics

### Phase 3: Refactor Visualizers
- Update `visualize_results.py` to read CSV instead of parsing
- Update `visualize_pareto.py` to read CSV instead of parsing
- Update `visualize_hero_graphs.py` to read CSV instead of parsing
- **Deliverable:** "Dumb" plotters with no data extraction logic

### Phase 4: Integration & Testing
- Update `mbmm_master.py` pipeline flow
- End-to-end testing of full pipeline
- Performance benchmarking
- **Deliverable:** Fully refactored production pipeline

---

## 8. Risk Assessment & Mitigation

| Risk | Probability | Mitigation |
|------|------------|-----------|
| CSV format breaks visualizers | Low | Version CSV schema, add validation |
| Performance regression | Low | Process_metrics runs once, visualizers faster |
| Floating-point precision loss | Low | Use double precision in CSV, test edge cases |
| Architecture mismatch between stages | Medium | Unit tests + integration tests |

---

## Approval Checklist

- [ ] Logging strategy approved
- [ ] Data processing stage (process_metrics.py) design approved
- [ ] CSV file schemas approved
- [ ] Refactored visualizer approach approved
- [ ] mbmm_master.py integration flow approved
- [ ] Timeline & resource allocation confirmed

---

## Next Steps (Upon Approval)

1. **Week 1:** Implement Phase 1 (logging_config.py)
2. **Week 2:** Implement Phase 2 (process_metrics.py)
3. **Week 3:** Implement Phase 3 (refactor visualizers)
4. **Week 4:** Phase 4 (integration & testing)

**Estimated Timeline:** 4 weeks  
**Code Lines Removed:** ~500-700 (duplication elimination)  
**Code Lines Added:** ~400-500 (process_metrics.py + logging)  
**Net Change:** -100 to -200 lines (cleaner codebase)

---

**Prepared by:** Lead Software Engineer  
**Date:** May 20, 2026  
**Status:** AWAITING APPROVAL
