"""Logging configuration."""

import logging
import sys
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> None:
    """Setup logging to both file and console."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "hedge_system.log"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

