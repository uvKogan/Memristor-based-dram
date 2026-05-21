#!/usr/bin/env python3
"""
Unified Logging Configuration for MBMM Pipeline

Provides consistent logging across all pipeline stages with:
- Console output (INFO and above)
- File output (DEBUG and above)  
- Timestamped log files per stage
- Automatic directory creation
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_logging(stage_name, log_dir="/home/yuvalk/MBMM/results/logs"):
    """
    Configure unified logging for pipeline stages.
    
    Args:
        stage_name (str): Name of the pipeline stage (e.g., "process_metrics", "visualize_pareto")
        log_dir (str): Directory to write log files (default: /results/logs/)
    
    Returns:
        logging.Logger: Configured logger that writes to both console and file
    
    Features:
        - Console: INFO and higher (user-friendly)
        - File: DEBUG and higher (detailed debugging)
        - Timestamped log files for traceability
        - Automatic /results/logs/ directory creation
        - Automatic logger name deduplication
    
    Example:
        >>> from logging_config import setup_logging
        >>> logger = setup_logging("process_metrics")
        >>> logger.info("Starting metric processing...")
        >>> logger.debug("Detailed debugging information")
    """
    
    # Create log directory if it doesn't exist (absolute path)
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log file per stage
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{stage_name}_{timestamp}.log"
    
    # Get or create logger (prevent duplicate handlers if called multiple times)
    logger = logging.getLogger(stage_name)
    
    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # ====================================================================
        # CONSOLE HANDLER: User-facing output (INFO and above)
        # ====================================================================
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # ====================================================================
        # FILE HANDLER: Detailed logging (DEBUG and above)
        # ====================================================================
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


if __name__ == "__main__":
    # Test logging configuration
    logger = setup_logging("test_logging")
    logger.info("This is an INFO message (shown on console)")
    logger.debug("This is a DEBUG message (file only)")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    print(f"\n✓ Logging configured successfully")
    print(f"  Log file: results/test_logging_*.log")
