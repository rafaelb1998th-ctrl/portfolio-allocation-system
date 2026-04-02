# HEDGE - Institutional-Grade Automated Trading System

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [File Structure & Purpose](#file-structure--purpose)
5. [Technologies & Dependencies](#technologies--dependencies)
6. [Data Flow](#data-flow)
7. [Systemd Services](#systemd-services)
8. [Configuration Files](#configuration-files)
9. [Trading Logic](#trading-logic)
10. [Risk Management](#risk-management)

---

## 🎯 Project Overview

**HEDGE** is an institutional-grade automated trading system designed to manage a portfolio using a multi-sleeve allocation strategy similar to hedge funds like Bridgewater, Renaissance Technologies, and BlackRock. The system:

- **Automatically rebalances** portfolios based on market regimes (SLOWDOWN, EXPANSION, RECESSION, RECOVERY)
- **Enforces whitelist-only trading** - only approved instruments can be traded
- **Implements multi-sleeve allocation** - 60% Core Macro (fixed) + 40% dynamic satellite sleeves
- **Uses real-time data** from Trading 212 API as the single source of truth
- **Executes trades** automatically with proper risk controls and position sizing
- **Monitors performance** and generates reports

### Key Features

- ✅ **Regime-Based Allocation**: Adjusts portfolio weights based on detected market conditions
- ✅ **Whitelist Enforcement**: Only trades approved instruments from curated lists
- ✅ **Multi-Sleeve Strategy**: Core Macro (60%) + Tactical, Emerging Markets, Dividends, Individual Stocks (40%)
- ✅ **Hedging Capabilities**: Uses bonds (UK Gilts, US Treasuries) and gold for defensive positioning
- ✅ **Real-Time Execution**: Automated trade execution with proper order management
- ✅ **Risk Controls**: Position limits, sector limits, cash buffers, drawdown protection
- ✅ **Performance Tracking**: Attribution analysis, NAV tracking, sleeve performance scoring

---

## 🏗️ Architecture

The system follows a **modular, service-oriented architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Trading 212 API                           │
│              (Single Source of Truth)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Collection Layer                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  data_collector_t212.py                              │   │
│  │  • Fetches prices, positions, cash                   │   │
│  │  • Updates state/prices.json, state/portfolio.json   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Signal Generation Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  regime_from_market.py                               │   │
│  │  • Analyzes market signals (XLP/XLY, XLU/XLI, GLD)  │   │
│  │  • Determines regime (SLOWDOWN/EXPANSION/etc.)      │   │
│  │  • Calculates confidence score                       │   │
│  │  • Updates state/regime.json                         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Allocation Layer                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  meta_allocator.py (via allocator.py service)        │   │
│  │  • Combines sleeve allocations                       │   │
│  │  • Applies policy constraints                        │   │
│  │  • Generates target weights                          │   │
│  │  • Updates state/targets.json                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Sleeve Allocators:                                          │
│  • core_macro.py - Regime-based core allocation             │
│  • tactical_shortterm.py - Momentum/mean-reversion          │
│  • emerging_markets.py - EM exposure                        │
│  • dividends_income.py - Income-focused                     │
│  • individual_stocks.py - Stock picking                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Trade Generation Layer                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  position_checker.py                                 │   │
│  │  • Compares targets vs current positions             │   │
│  │  • Calculates required trades                        │   │
│  │  • Validates whitelist compliance                    │   │
│  │  • Maps symbols to T212 tickers                      │   │
│  │  • Generates state/trade_list.json                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Execution Layer                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  trade_executor.py                                   │   │
│  │  • Loads trade_list.json                             │   │
│  │  • Executes SELL orders first                        │   │
│  │  • Scales BUY orders to fit cash                     │   │
│  │  • Places orders via T212 API                        │   │
│  │  • Logs executions to state/executions.log.jsonl     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure & Purpose

### Core Directory (`core/`)

#### Broker Integration (`core/broker/`)

**`t212_client.py`**
- **Purpose**: Trading 212 API client with dual backend support (API + Automation)
- **Key Features**:
  - Connects to Trading 212 via REST API or Playwright automation
  - Fetches real-time prices, positions, cash, portfolio summary
  - Places market and limit orders
  - Handles rate limiting and retries
  - Caches instrument data for symbol mapping
- **Methods**:
  - `connect()` - Establishes connection
  - `get_positions()` - Returns current holdings
  - `get_cash()` - Returns available cash
  - `get_market_prices()` - Returns current prices for symbols
  - `place_market_order()` - Places market buy/sell orders
  - `get_pending_orders()` - Returns pending orders

**`price_feed.py`**
- **Purpose**: Composite price feed that aggregates prices from multiple sources
- **Sources**: Trading 212 API, Yahoo Finance (via yfinance)
- **Features**: Fallback logic, currency conversion, caching

**`symbol_map.json`**
- **Purpose**: Maps internal symbols (e.g., "XLP") to Trading 212 tickers (e.g., "SXLPl_EQ")
- **Structure**: Includes primary ticker, alternatives, ISIN, currency, provider info
- **Critical**: Ensures correct instrument selection (e.g., avoids XLPEl_EQ for XLP)

#### Services (`core/services/`)

**`data_collector_t212.py`**
- **Purpose**: Collects real-time market data and portfolio state
- **Frequency**: Runs every minute (via systemd timer)
- **Outputs**:
  - `state/prices.json` - Current market prices for all tracked symbols
  - `state/portfolio.json` - Current positions, cash, equity, NAV
- **Data Source**: Trading 212 API only (single source of truth)

**`regime_from_market.py`**
- **Purpose**: Detects current market regime from price signals
- **Frequency**: Runs every 30-60 minutes
- **Signals Used**:
  - Defensive vs Cyclical: `XLP/XLY`, `XLU/XLI` ratios
  - Healthcare vs Technology: `XLV/XLK` ratio
  - Hard Assets: `GLD/SPY` ratio
  - Financials vs Utilities: `XLF/XLU` ratio
- **Outputs**:
  - `state/regime.json` - Current regime (SLOWDOWN/EXPANSION/RECESSION/RECOVERY), confidence score, signal values
- **Logic**: Combines multiple signals to determine regime with confidence score (0-1)

**`allocator.py`** (Legacy - being phased out)
- **Purpose**: Simple rule-based allocator (older implementation)
- **Note**: Being replaced by `meta_allocator.py` for institutional-grade allocation

**`meta_allocator.py`** (via `core/allocator/meta_allocator.py`)
- **Purpose**: Main allocation engine that combines all sleeves
- **Frequency**: Runs daily (e.g., 08:05 UTC)
- **Process**:
  1. Loads policy configuration (`core/policy.yaml`)
  2. Loads whitelist (`core/universe/whitelist.yaml`)
  3. Gets regime and confidence from `state/regime.json`
  4. Calls individual sleeve allocators:
     - `core_macro_weights()` - 60% fixed allocation
     - `tactical_weights()` - Dynamic tactical sleeve
     - `emerging_markets_weights()` - EM exposure
     - `dividends_income_weights()` - Income sleeve
     - `individual_stocks_weights()` - Stock picking
  5. Calculates sleeve scores based on performance (Sharpe ratios)
  6. Allocates 40% dynamically across satellite sleeves
  7. Applies policy constraints (max position, max sector, cash floor)
  8. Outputs `state/targets.json` with target weights

**`position_checker.py`**
- **Purpose**: Analyzes current positions vs targets and generates trade list
- **Frequency**: Runs before trade execution (on-demand or scheduled)
- **Process**:
  1. Loads `state/targets.json` (target weights)
  2. Fetches current positions from T212 API (real-time)
  3. Fetches available cash from T212 API
  4. Calculates NAV (cash + positions)
  5. Maps T212 tickers to internal symbols using `symbol_map.json`
  6. For each target weight:
     - Calculates target value = weight × NAV
     - Gets current value from positions
     - Calculates allocation = target - current
  7. Filters trades (only if |allocation| > £1.0)
  8. Validates whitelist compliance
  9. **Special handling for XLP**: Ensures correct ticker (SXLPl_EQ, not XLPEl_EQ)
  10. Sorts trades (SELLS first, then BUYS)
  11. Outputs `state/trade_list.json` with list of trades to execute

**`trade_executor.py`**
- **Purpose**: Executes trades from trade list
- **Frequency**: Runs after position_checker (on-demand or scheduled)
- **Process**:
  1. Loads `state/trade_list.json`
  2. Gets fresh cash from T212 API
  3. Calculates total BUYS and SELLS
  4. Scales BUY orders if insufficient cash (proportional scaling)
  5. Executes SELL orders first (to free cash)
  6. Waits 2 seconds for sells to process
  7. Re-checks cash after sells
  8. Executes BUY orders (scaled to fit available cash)
  9. Handles FX conversion for USD instruments
  10. Logs all executions to `state/executions.log.jsonl`
  11. Checks pending orders at end

**`rebalance_manager.py`**
- **Purpose**: Manages rebalancing logic and drift detection
- **Features**: Drift thresholds, hysteresis bands, staggered rebalances

**`performance_reporter.py`**
- **Purpose**: Generates performance reports with attribution analysis
- **Outputs**: Sleeve performance, Sharpe ratios, NAV history

**`reporter.py`**
- **Purpose**: Simple text-based report generator
- **Outputs**: Weekly/monthly reports to `out/weekly_report_*.txt`

**`health_monitor.py`**
- **Purpose**: Monitors system health and alerts on issues
- **Checks**: API connectivity, data freshness, error rates

**`check_portfolio_status.py`**
- **Purpose**: Utility script to check current positions and pending orders
- **Features**: 
  - Lists all current positions with values
  - Lists all pending orders with status
  - Validates XLP ticker correctness
  - Checks whitelist compliance

#### Allocators (`core/allocator/`)

**`meta_allocator.py`**
- **Purpose**: Main allocator that orchestrates all sleeves
- **Key Functions**:
  - `get_sleeve_scores()` - Calculates performance scores for dynamic sleeves
  - `allocate_sleeves()` - Allocates 40% across satellite sleeves based on scores
  - `combine_weights()` - Combines all sleeve weights into final targets
  - `apply_policy_constraints()` - Enforces risk limits

**`core_macro.py`**
- **Purpose**: Core Macro sleeve allocator (60% fixed)
- **Regime Templates**:
  - `SLOWDOWN`: Heavy defensive (XLU, XLP, GLD, bonds)
  - `EXPANSION`: Growth-focused (EQQQ, SPY4, IDUP)
  - `RECESSION`: Maximum defensive (cash, utilities, staples, bonds)
  - `RECOVERY`: Balanced growth (mix of defensive and cyclical)
- **Features**: Confidence adjustment, whitelist filtering

**`tactical_shortterm.py`**
- **Purpose**: Tactical sleeve for short-term momentum/mean-reversion
- **Allocation**: Dynamic (5-20% of NAV based on performance)

**`emerging_markets.py`**
- **Purpose**: Emerging markets exposure sleeve
- **Allocation**: Dynamic (5-20% of NAV based on performance)

**`dividends_income.py`**
- **Purpose**: Income-focused sleeve (REITs, dividend ETFs, utilities)
- **Allocation**: Dynamic (10-25% of NAV based on performance)

**`individual_stocks.py`**
- **Purpose**: Individual stock picking sleeve (alpha generation)
- **Stocks**: Curated list of major stocks (NVDA, TSLA, AAPL, MSFT, JPM, etc.)
- **Allocation**: Dynamic based on performance and risk limits

#### Configuration (`core/`)

**`config.py`**
- **Purpose**: Central configuration loader
- **Settings**:
  - Trading 212 API credentials (from environment)
  - Trading parameters (min ticket size, drift threshold, cash buffer)
  - Risk limits (max drawdown, circuit breaker, kill switch)
  - Paths (state directory, logs directory, symbol map)

**`policy.yaml`**
- **Purpose**: Institutional-grade policy configuration
- **Sections**:
  - `benchmark`: Benchmark for performance comparison
  - `allocation`: Core allocation constants (60% fixed core)
  - `saa_weights`: Strategic Asset Allocation baseline weights
  - `risk`: Risk management limits (max position, max sector, cash floor)
  - `rebalancing`: Rebalancing rules (drift thresholds, hysteresis, frequency)
  - `execution`: Execution rules (min ticket, spread limits, liquidity guards)
  - `sleeves`: Dynamic sleeve allocation parameters

**`universe/whitelist.yaml`**
- **Purpose**: Curated list of approved instruments per sleeve
- **Buckets**:
  - `core_macro`: EQQQ, XLIS, SPY4, IDUP, VUKE, XLU, XLP, GLD, IGLT, DTLE, TRSY, XGLD
  - `tactical`: EQQQ, XLIS, XLY, XLI, GLD, XLK, SPY
  - `individual_stocks`: 100+ individual stocks (NVDA, TSLA, AAPL, MSFT, JPM, etc.)
  - `emerging`: EEM, VWO, FXI, EWZ
  - `dividends`: VIG, IDUP, XLU, XLP, VHYL, IWD
- **Rules**: UCITS-only, approved issuers, currency preferences, expense ratio limits

#### Utilities (`core/utils/`)

**`io.py`**
- **Purpose**: File I/O utilities with atomic writes
- **Functions**:
  - `read_json()` - Reads JSON file safely
  - `write_json()` - Writes JSON atomically (temp file + rename)
  - `append_jsonl()` - Appends to JSONL log file
- **Features**: Atomic writes prevent corruption, error handling

**`logging.py`**
- **Purpose**: Logging configuration
- **Features**: Structured logging, log rotation, log levels

### State Directory (`state/`)

**`prices.json`**
- **Purpose**: Current market prices for all tracked symbols
- **Format**: `{"ts": "ISO timestamp", "prices": {"SYMBOL": price, ...}}`
- **Updated**: Every minute by `data_collector_t212.py`

**`portfolio.json`**
- **Purpose**: Current portfolio state
- **Format**: `{"ts": "ISO timestamp", "cash": amount, "equity": amount, "nav": amount, "positions": [...]}`
- **Updated**: Every minute by `data_collector_t212.py`

**`regime.json`**
- **Purpose**: Current market regime and confidence
- **Format**: `{"ts": "ISO timestamp", "regime": "SLOWDOWN|EXPANSION|RECESSION|RECOVERY", "confidence": 0.0-1.0, "signals": {...}}`
- **Updated**: Every 30-60 minutes by `regime_from_market.py`

**`targets.json`**
- **Purpose**: Target portfolio weights
- **Format**: `{"ts": "ISO timestamp", "weights": {"SYMBOL": weight, ...}, "notes": "...", "meta": {...}}`
- **Updated**: Daily by `meta_allocator.py` (via `allocator.py` service)

**`trade_list.json`**
- **Purpose**: List of trades to execute
- **Format**: `{"ts": "ISO timestamp", "nav": amount, "cash": amount, "trades": [{"symbol": "...", "t212_ticker": "...", "allocation": amount, ...}, ...]}`
- **Updated**: Before each execution by `position_checker.py`

**`executions.log.jsonl`**
- **Purpose**: Execution log (append-only)
- **Format**: One JSON object per line with execution details
- **Updated**: After each trade by `trade_executor.py`

**`nav_history.jsonl`**
- **Purpose**: NAV history for performance tracking
- **Format**: One JSON object per line with timestamp and NAV

**`sleeve_performance.json`**
- **Purpose**: Sleeve performance metrics (Sharpe ratios, returns)
- **Updated**: By `performance_reporter.py`

**`sleeve_attribution_history.jsonl`**
- **Purpose**: Historical sleeve attribution data
- **Format**: One JSON object per line with sleeve contributions

**`health_status.json`**
- **Purpose**: System health status
- **Updated**: By `health_monitor.py`

**`last_regime.json`**
- **Purpose**: Last detected regime (for change detection)

**`last_drift_state.json`**
- **Purpose**: Last drift state (for rebalancing logic)

### Brokers Directory (`brokers/`)

**`symbol_map.json`**
- **Purpose**: Maps internal symbols to Trading 212 tickers
- **Critical**: Ensures correct instrument selection (e.g., XLP → SXLPl_EQ, not XLPEl_EQ)

**`filtered_instruments/`**
- **Purpose**: Categorized instrument lists
- **Files**: `all_filtered.json`, `stock.json`, `etf.json`, `bond.json`, `treasury.json`, etc.

**`t212_instruments.json`**
- **Purpose**: Full Trading 212 instrument catalog
- **Updated**: By `export_instruments.py` script

### Services Directory (`services/`)

**Systemd Service Files**:
- `hedge-data.service` / `hedge-data.timer` - Data collection (every minute)
- `hedge-regime.service` / `hedge-regime.timer` - Regime detection (every 30-60 min)
- `hedge-ai.service` / `hedge-ai.timer` - Allocation (daily at 08:05 UTC)
- `hedge-trader.service` / `hedge-trader.timer` - Trade execution (on-demand or scheduled)
- `hedge-reporter.service` / `hedge-reporter.timer` - Reporting (weekly/monthly)
- `hedge-health.service` / `hedge-health.timer` - Health monitoring (every 5 minutes)
- `hedge-performance.service` / `hedge-performance.timer` - Performance tracking (daily)
- `hedge-rebalance.service` / `hedge-rebalance.timer` - Rebalancing (on drift threshold)
- `hedge-deposit.path` - Triggers on cash deposit detection

### Scripts Directory (`scripts/`)

**Utility Scripts**:
- `check_instruments.py` - Validates instrument data
- `filter_and_categorize_instruments.py` - Categorizes instruments
- `get_instruments_example.py` - Example instrument fetching
- `list_all_instruments.py` - Lists all available instruments
- `search_instruments.py` - Searches instruments by criteria
- `test_prices.py` - Tests price feed
- `update_instruments.py` - Updates instrument catalog
- `verify_instruments.py` - Verifies instrument mappings

### Output Directory (`out/`)

**Generated Reports**:
- `comprehensive_data.json` - Comprehensive data export
- `weekly_report_*.txt` - Weekly performance reports
- `t212_instruments_*.csv/json/xlsx` - Instrument exports

---

## 🛠️ Technologies & Dependencies

### Core Technologies

- **Python 3.12+**: Main programming language
- **Trading 212 API**: Broker integration (REST API + Playwright automation)
- **Yahoo Finance (yfinance)**: Price feed fallback
- **Systemd**: Service management and scheduling

### Python Packages

**Core Dependencies**:
- `requests` - HTTP client for API calls
- `yfinance` - Yahoo Finance data
- `playwright` - Browser automation (for T212 automation backend)
- `pyyaml` - YAML configuration parsing
- `python-dotenv` - Environment variable management

**Data & Utilities**:
- `json` - JSON handling (standard library)
- `datetime` - Timestamp handling (standard library)
- `pathlib` - Path management (standard library)
- `logging` - Logging (standard library)
- `typing` - Type hints (standard library)

### External Services

- **Trading 212**: Broker platform (API + web interface)
- **Yahoo Finance**: Price data fallback
- **Alpha Vantage** (optional): Market data API

### Infrastructure

- **Linux Systemd**: Service orchestration
- **JSON/JSONL**: State and log storage
- **YAML**: Configuration files

---

## 🔄 Data Flow

### 1. Data Collection (Every Minute)

```
Trading 212 API
    ↓
data_collector_t212.py
    ↓
state/prices.json (market prices)
state/portfolio.json (positions, cash, NAV)
```

### 2. Regime Detection (Every 30-60 Minutes)

```
state/prices.json
    ↓
regime_from_market.py
    ↓ (analyzes XLP/XLY, XLU/XLI, GLD/SPY ratios)
state/regime.json (regime, confidence, signals)
```

### 3. Allocation (Daily)

```
state/regime.json
state/portfolio.json
state/prices.json
core/policy.yaml
core/universe/whitelist.yaml
    ↓
meta_allocator.py
    ↓ (calls sleeve allocators, applies constraints)
state/targets.json (target weights)
```

### 4. Trade Generation (Before Execution)

```
state/targets.json
Trading 212 API (current positions, cash)
brokers/symbol_map.json
core/universe/whitelist.yaml
    ↓
position_checker.py
    ↓ (calculates allocations, validates whitelist)
state/trade_list.json (list of trades)
```

### 5. Trade Execution (On-Demand or Scheduled)

```
state/trade_list.json
Trading 212 API (fresh cash, prices)
    ↓
trade_executor.py
    ↓ (executes SELLS first, then BUYS)
Trading 212 API (order placement)
state/executions.log.jsonl (execution log)
```

### 6. Performance Tracking (Daily)

```
state/portfolio.json
state/nav_history.jsonl
state/executions.log.jsonl
    ↓
performance_reporter.py
    ↓ (calculates Sharpe ratios, attribution)
state/sleeve_performance.json
state/sleeve_attribution_history.jsonl
```

---

## ⚙️ Systemd Services

### Service Overview

All services run as systemd units with timers for scheduling:

| Service | Timer | Frequency | Purpose |
|---------|-------|-----------|---------|
| `hedge-data` | `hedge-data.timer` | Every 1 minute | Collect prices and portfolio data |
| `hedge-regime` | `hedge-regime.timer` | Every 30-60 min | Detect market regime |
| `hedge-ai` | `hedge-ai.timer` | Daily 08:05 UTC | Generate target allocations |
| `hedge-trader` | `hedge-trader.timer` | On-demand or scheduled | Execute trades |
| `hedge-reporter` | `hedge-reporter.timer` | Weekly/Monthly | Generate reports |
| `hedge-health` | `hedge-health.timer` | Every 5 minutes | Monitor system health |
| `hedge-performance` | `hedge-performance.timer` | Daily | Track performance |
| `hedge-rebalance` | `hedge-rebalance.timer` | On drift threshold | Trigger rebalancing |
| `hedge-deposit` | `hedge-deposit.path` | On cash deposit | Detect deposits |

### Installation

```bash
# Copy service files
sudo cp services/*.service /etc/systemd/system/
sudo cp services/*.timer /etc/systemd/system/
sudo cp services/*.path /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timers
sudo systemctl enable --now hedge-data.timer
sudo systemctl enable --now hedge-regime.timer
sudo systemctl enable --now hedge-ai.timer
sudo systemctl enable --now hedge-trader.timer
sudo systemctl enable --now hedge-reporter.timer
sudo systemctl enable --now hedge-health.timer
sudo systemctl enable --now hedge-performance.timer
sudo systemctl enable --now hedge-rebalance.timer
sudo systemctl enable --now hedge-deposit.path
```

### Monitoring

```bash
# Check service status
systemctl status hedge-data.service
systemctl status hedge-trader.service

# View logs
journalctl -u hedge-data.service -f
journalctl -u hedge-trader.service -f

# Check timer status
systemctl list-timers hedge-*.timer
```

---

## 📝 Configuration Files

### Environment Variables (`.env` or `config.txt`)

```bash
# Trading 212 API
T212_API_KEY="your_api_key"
T212_API_SECRET="your_api_secret"
T212_MODE="api"  # or "automation"
T212_PROFILE_DIR="/path/to/t212_profile"

# Optional: Alpha Vantage
ALPHA_VANTAGE_API_KEY="your_key"

# System
HEDGE_ENV="production"
DEBUG="false"
LOG_LEVEL="INFO"
ACCOUNT_CCY="GBP"

# Risk Management
MAX_DRAWDOWN_30D=0.08
MAX_DRAWDOWN_PEAK=0.12
CIRCUIT_BREAKER_THRESHOLD=0.10
KILL_SWITCH_THRESHOLD=0.15
```

### Policy Configuration (`core/policy.yaml`)

Key settings:
- **Core allocation**: 60% fixed Core Macro
- **SAA weights**: Strategic Asset Allocation baseline
- **Risk limits**: Max position (10%), max sector (25%), cash floor (10%)
- **Rebalancing**: Drift thresholds, hysteresis bands, frequency
- **Execution**: Min ticket size (£1), spread limits, liquidity guards
- **Sleeves**: Dynamic allocation parameters (5-25% ranges)

### Whitelist (`core/universe/whitelist.yaml`)

- **Approved issuers**: iShares, Vanguard, SPDR, Xtrackers, Invesco, WisdomTree
- **Rules**: UCITS-only, approved domiciles, currency preferences, expense ratio limits
- **Buckets**: Instruments grouped by sleeve (core_macro, tactical, individual_stocks, etc.)

### Symbol Map (`brokers/symbol_map.json`)

Maps internal symbols to Trading 212 tickers:
```json
{
  "XLP": {
    "t212": "SXLPl_EQ",
    "t212_alt": ["XLPSl_EQ"],
    "isin": "US78463A1030",
    "currency": "USD",
    "provider": "SPDR",
    "note": "Consumer Staples - Use SXLPl_EQ (NOT XLPEl_EQ)"
  }
}
```

---

## 📊 Trading Logic

### Allocation Strategy

1. **Core Macro (60% fixed)**:
   - Regime-based allocation using templates
   - SLOWDOWN: Defensive (utilities, staples, bonds, gold)
   - EXPANSION: Growth (Nasdaq, S&P 500, mid-cap, developed markets)
   - RECESSION: Maximum defensive (cash, utilities, staples, bonds)
   - RECOVERY: Balanced growth (mix of defensive and cyclical)

2. **Satellite Sleeves (40% dynamic)**:
   - **Tactical (5-20%)**: Momentum/mean-reversion ETFs
   - **Emerging Markets (5-20%)**: EM exposure
   - **Dividends (10-25%)**: Income-focused instruments
   - **Individual Stocks (variable)**: Stock picking for alpha

3. **Sleeve Scoring**:
   - Uses Sharpe ratios (3-month and 6-month)
   - EWMA smoothing for stability
   - Score floor to prevent zero allocation
   - Dynamic allocation based on performance

### Trade Generation

1. **Position Checker**:
   - Loads target weights from `state/targets.json`
   - Fetches current positions from T212 API
   - Calculates NAV (cash + positions)
   - For each target:
     - Target value = weight × NAV
     - Current value = position value (or 0)
     - Allocation = target - current
   - Filters trades (only if |allocation| > £1.0)
   - Validates whitelist compliance
   - Maps symbols to T212 tickers (with special handling for XLP)
   - Sorts trades (SELLS first, then BUYS)

2. **Trade Executor**:
   - Loads trade list from `state/trade_list.json`
   - Gets fresh cash from T212 API
   - Calculates total BUYS and SELLS
   - Scales BUY orders if insufficient cash (proportional scaling)
   - Executes SELL orders first (to free cash)
   - Waits for sells to process
   - Re-checks cash after sells
   - Executes BUY orders (scaled to fit available cash)
   - Handles FX conversion for USD instruments
   - Logs all executions

### Risk Controls

1. **Position Limits**:
   - Max position: 10% of NAV
   - Max sector: 25% of NAV
   - Cash floor: 10% of NAV

2. **Execution Limits**:
   - Min ticket size: £1.00
   - Max spread: 60 bps
   - Liquidity guard: Skip if order > 2% of ADV

3. **Rebalancing Controls**:
   - Drift threshold: 5% (core), 3% (satellites)
   - Hysteresis bands: Prevent ping-pong rebalancing
   - Staggered rebalances: Split core rebalance across days

4. **Drawdown Protection**:
   - Max 30-day drawdown: 8%
   - Max peak drawdown: 12%
   - Circuit breaker: 10% threshold
   - Kill switch: 15% threshold

---

## 🛡️ Risk Management

### Position-Level Risk

- **Max Position Weight**: 10% of NAV per instrument
- **Max Sector Weight**: 25% of NAV per sector
- **Whitelist Enforcement**: Only approved instruments can be traded
- **Symbol Validation**: Ensures correct ticker selection (e.g., XLP → SXLPl_EQ)

### Portfolio-Level Risk

- **Cash Floor**: Minimum 10% cash buffer
- **Cash Buffer**: Additional 1% unallocated buffer
- **FX Buffer**: 0.3% cash for FX slippage on USD instruments

### Execution Risk

- **Min Ticket Size**: £1.00 minimum order size
- **Spread Limits**: Skip orders with spread > 60 bps
- **Liquidity Guards**: Skip orders > 2% of average daily volume
- **Rate Limiting**: 0.5-1 second delays between orders

### Drawdown Protection

- **30-Day Drawdown**: Alert if > 8%
- **Peak Drawdown**: Alert if > 12%
- **Circuit Breaker**: Pause trading if > 10%
- **Kill Switch**: Stop all trading if > 15%

### Regime-Based Risk

- **Confidence Adjustment**: Lower confidence → more cash/defensive
- **Regime Templates**: Different risk profiles per regime
- **Hedging**: Bonds (IGLT, DTLE) and gold (GLD) for defensive positioning

---

## 🚀 Getting Started

### Prerequisites

1. **Trading 212 Account**: With API access enabled
2. **Python 3.12+**: Installed and configured
3. **Linux System**: With systemd (for service management)
4. **API Credentials**: Trading 212 API key and secret

### Installation

1. **Clone/Download Project**:
   ```bash
   cd /home/teckz/Documents/HEDGE
   ```

2. **Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install requests yfinance playwright pyyaml python-dotenv
   playwright install chromium
   ```

3. **Configure Environment**:
   ```bash
   # Create .env file or set environment variables
   export T212_API_KEY="your_key"
   export T212_API_SECRET="your_secret"
   export T212_MODE="api"
   ```

4. **Install Systemd Services**:
   ```bash
   sudo cp services/*.service /etc/systemd/system/
   sudo cp services/*.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now hedge-data.timer
   ```

5. **Test Connection**:
   ```bash
   python3 -m core.services.data_collector_t212
   ```

### Manual Execution

```bash
# Check positions
python3 -m core.services.check_portfolio_status

# Generate trade list
python3 -m core.services.position_checker

# Execute trades
python3 -m core.services.trade_executor
```

---

## 📚 Additional Documentation

- **`README.md`** (repo root): Quick start guide
- **`docs/strategy/complete_trading_strategy.md`**: Detailed trading strategy
- **`docs/strategy/hedge_fund_trading_logic.md`**: Hedge fund logic explanation
- **`docs/architecture/institutional_architecture.md`**: Architecture details
- **`docs/setup/institutional_setup.md`**: Setup instructions

---

## 🔍 Key Design Decisions

1. **Single Source of Truth**: Trading 212 API only (no external data feeds)
2. **Modular Architecture**: Clear separation between data collection, allocation, and execution
3. **Whitelist Enforcement**: Only approved instruments can be traded
4. **Real-Time Data**: Always uses fresh data from T212 API (no stale portfolio.json fallback)
5. **Position Checker + Trade Executor**: Separated decision-making from execution
6. **Symbol Mapping**: Explicit mapping to avoid wrong instrument selection (e.g., XLP)
7. **Proportional Scaling**: BUY orders scaled proportionally if insufficient cash
8. **SELL First**: Always executes SELL orders before BUY orders to free cash

---

## ⚠️ Important Notes

- **Whitelist Compliance**: System only trades instruments in `core/universe/whitelist.yaml`
- **Symbol Mapping**: Always use `brokers/symbol_map.json` for ticker mapping (especially for XLP)
- **Real-Time Data**: System uses T212 API for all position and cash data (no fallback to stale files)
- **Cash Management**: System scales BUY orders if insufficient cash (proportional scaling)
- **Rate Limiting**: Built-in delays to respect T212 API rate limits
- **Error Handling**: All services have fallback logic and error logging

---

## 📞 Support

For issues or questions:
1. Check logs: `journalctl -u hedge-*.service -f`
2. Check state files: `state/*.json`
3. Verify configuration: `core/policy.yaml`, `core/universe/whitelist.yaml`
4. Test connection: `python3 -m core.services.check_portfolio_status`

---

**Last Updated**: 2025-01-10
**Version**: 1.0.0

