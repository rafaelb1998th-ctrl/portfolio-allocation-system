"""Core configuration - loads from environment variables."""

import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
STATE_DIR = PROJECT_ROOT / "state"
LOGS_DIR = PROJECT_ROOT / "logs"

# Trading 212 configuration (from config.txt / .env)
T212_API_KEY = os.getenv("T212_API_KEY", "")
T212_API_SECRET = os.getenv("T212_API_SECRET", "")
T212_MODE = os.getenv("T212_MODE", "api")  # "api" or "automation"
T212_PROFILE_DIR = os.getenv("T212_PROFILE_DIR", str(PROJECT_ROOT / "t212_profile"))

# Alpha Vantage API configuration (for market data)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# Trading parameters
MIN_TICKET_SIZE_GBP = 1.00
DRIFT_THRESHOLD = 0.03  # 3% weight difference to trigger trade
NAV_PAD = 0.995  # Leave 0.5% for fees/wiggle room
CASH_BUFFER = 0.01  # 1% cash buffer

# Deposit detection
DEPOSIT_THRESHOLD_GBP = 5.00  # If cash increases by >£5, allow trading

# Symbol map path
SYMBOL_MAP_PATH = PROJECT_ROOT / "brokers" / "symbol_map.json"

# System configuration (from config.txt)
HEDGE_ENV = os.getenv("HEDGE_ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Account configuration
ACCOUNT_CCY = os.getenv("ACCOUNT_CCY", "GBP")

# Risk management (from config.txt)
MAX_DRAWDOWN_30D = float(os.getenv("MAX_DRAWDOWN_30D", "0.08"))
MAX_DRAWDOWN_PEAK = float(os.getenv("MAX_DRAWDOWN_PEAK", "0.12"))
CIRCUIT_BREAKER_THRESHOLD = float(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "0.10"))
KILL_SWITCH_THRESHOLD = float(os.getenv("KILL_SWITCH_THRESHOLD", "0.15"))

