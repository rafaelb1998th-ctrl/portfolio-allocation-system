# Complete Trading Strategy - Hedge Fund Style

## Overview

This document explains **exactly** how the HEDGE system trades, decides between ETFs and individual stocks, and structures portfolios like hedge funds and banks do.

---

## Table of Contents

1. [Portfolio Structure](#portfolio-structure)
2. [Decision Framework: ETFs vs Individual Stocks](#decision-framework-etfs-vs-individual-stocks)
3. [Market Regime Analysis](#market-regime-analysis)
4. [Confidence-Based Allocation](#confidence-based-allocation)
5. [Sector Rotation Strategy](#sector-rotation-strategy)
6. [Risk Management](#risk-management)
7. [Execution Process](#execution-process)
8. [Example Allocations](#example-allocations)
9. [How It Compares to Hedge Funds](#how-it-compares-to-hedge-funds)

---

## Portfolio Structure

### Core Architecture (Like Hedge Funds)

The portfolio is structured in **sleeves** (like hedge funds):

```
Total Portfolio (100% of NAV)
├── Core Macro Sleeve (60% fixed)
│   ├── ETFs: 55% (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD)
│   ├── Bonds: 3% (IGLT - UK Gilts)
│   └── Cash: 2%
│
├── Individual Stocks Sleeve (10-30% dynamic)
│   ├── Tech/AI: 40% of sleeve (NVDA, TSLA, AAPL, MSFT, GOOGL, META, AMZN)
│   ├── Finance: 20% of sleeve (JPM, BAC, GS, V, MA)
│   ├── Healthcare: 15% of sleeve (UNH, JNJ, LLY, TMO)
│   ├── Consumer: 10% of sleeve (WMT, HD, COST, NKE)
│   ├── Industrial: 8% of sleeve (BA, CAT, RTX)
│   ├── Energy: 5% of sleeve (XOM, CVX)
│   └── Other: 2% of sleeve (VZ, NEE)
│
├── Tactical Sleeve (5-20% dynamic)
│   ├── ETFs: 80% (SPY, GLD, XLK)
│   └── Cash: 20%
│
├── Emerging Markets Sleeve (5-20% dynamic)
│   ├── ETFs: 70% (EEM, VWO, EWZ)
│   └── Cash: 30%
│
└── Dividends Sleeve (10-25% dynamic)
    ├── ETFs: 80% (VIG, XLU, XLP)
    └── Cash: 20%
```

### Total Allocation Breakdown

- **ETFs**: 50-60% of NAV (diversification, broad market exposure)
- **Individual Stocks**: 10-30% of NAV (alpha generation, direct exposure)
- **Bonds**: 3-5% of NAV (defensive, income)
- **Gold**: 2-3% of NAV (real assets, inflation hedge)
- **Cash**: 5-10% of NAV (liquidity, opportunity fund)

---

## Decision Framework: ETFs vs Individual Stocks

### When to Use ETFs

**ETFs are used for:**
1. **Diversification**: Broad market exposure (EQQQ, XLIS, SPY4)
2. **Defensive Positioning**: Lower volatility (XLU, XLP, IGLT)
3. **Low Confidence**: When uncertain about specific stocks
4. **Recession**: When market is uncertain
5. **Core Holdings**: Long-term strategic allocation (60% of portfolio)
6. **Sector Exposure**: When you want sector exposure without single-stock risk (XLK, XLY, XLI)
7. **Emerging Markets**: Diversified EM exposure (EEM, VWO, EWZ)
8. **Income**: Dividend ETFs (VIG, XLU, XLP)

**ETFs in Portfolio:**
- **Core Macro (60%)**: EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT
- **Tactical (10%)**: SPY, GLD, XLK
- **Emerging Markets (13%)**: EEM, VWO, EWZ
- **Dividends (17%)**: VIG, XLU, XLP

### When to Use Individual Stocks

**Individual Stocks are used for:**
1. **Alpha Generation**: Direct exposure to winners (NVDA, TSLA, AAPL)
2. **High Confidence**: When confident about specific stocks
3. **Expansion**: When market is strong (bull market)
4. **Growth**: When seeking higher returns
5. **Specific Themes**: AI, technology, innovation
6. **Satellite Holdings**: Tactical/alpha generation (10-30% of portfolio)

**Individual Stocks in Portfolio:**
- **Tech/AI Leaders**: NVDA, TSLA, AAPL, MSFT, GOOGL, META, AMZN, AMD, AVGO
- **Finance**: JPM, BAC, GS, MS, BLK, V, MA, AXP
- **Healthcare**: UNH, JNJ, PFE, ABT, TMO, LLY, AMGN, GILD
- **Consumer**: WMT, HD, MCD, NKE, SBUX, TGT, COST, LOW, DIS
- **Industrial**: BA, CAT, GE, HON, RTX, LMT, NOC, DE
- **Energy**: XOM, CVX, SLB, COP, EOG
- **Communication**: VZ, T, CMCSA
- **Materials & REITs**: LIN, APD, AMT, PLD, EQIX
- **Utilities**: NEE, DUK, SO

---

## Market Regime Analysis

The system **automatically detects** market regime and adjusts allocation accordingly.

### EXPANSION (Bull Market)

**Characteristics:**
- Strong economic growth
- Rising markets
- High confidence in growth

**Allocation:**
- **Individual Stocks**: 30-40% of NAV (aggressive alpha generation)
  - Tech/AI heavy: NVDA, TSLA, AAPL, MSFT, GOOGL, META, AMZN
  - Growth focus: High-growth stocks
  - Sector rotation: Tech, finance, consumer discretionary
- **ETFs**: 50-60% of NAV (diversification)
  - Broad market: EQQQ, XLIS, SPY4
  - Growth sectors: XLK, XLY
- **Bonds**: 3-5% of NAV (minimal)
- **Cash**: 5-10% of NAV (opportunity fund)

**Example (High Confidence 0.7):**
- Core Macro (60%): ETFs (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT)
- Individual Stocks (30%): NVDA 2.5%, TSLA 1.9%, AAPL 1.6%, MSFT 1.6%, GOOGL 1.3%, META 1.3%, AMZN 1.3%, JPM 1.2%, BAC 1.0%, UNH 0.9%, ... (30+ stocks)
- Tactical (10%): SPY, GLD, XLK
- Emerging Markets (5%): EEM, VWO, EWZ
- Dividends (5%): VIG, XLU, XLP

**Example (Low Confidence 0.3):**
- Core Macro (60%): ETFs (same as above)
- Individual Stocks (10%): JPM 1.5%, UNH 1.5%, JNJ 1.5%, AAPL 1.5%, MSFT 1.5%, BAC 1.3%, WMT 1.3%, GOOGL 1.2%, V 1.2%, MA 1.2% (22 stocks, defensive)
- Tactical (10%): SPY, GLD, XLK
- Emerging Markets (13%): EEM, VWO, EWZ
- Dividends (17%): VIG, XLU, XLP

### RECOVERY

**Characteristics:**
- Market recovering from downturn
- Moderate growth
- Cautious optimism

**Allocation:**
- **Individual Stocks**: 25-30% of NAV (moderate alpha generation)
  - Quality focus: AAPL, MSFT, JPM, UNH, JNJ
  - Balanced: Tech + Finance + Healthcare
- **ETFs**: 60-65% of NAV (diversification)
- **Bonds**: 5% of NAV (defensive)
- **Cash**: 5-10% of NAV

**Example:**
- Core Macro (60%): ETFs (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT)
- Individual Stocks (25%): AAPL 1.5%, MSFT 1.5%, JPM 1.5%, NVDA 1.3%, GOOGL 1.3%, BAC 1.3%, UNH 1.3%, JNJ 1.3%, ... (28 stocks)
- Tactical (10%): SPY, GLD, XLK
- Emerging Markets (5%): EEM, VWO, EWZ
- Dividends (10%): VIG, XLU, XLP

### SLOWDOWN

**Characteristics:**
- Economic slowdown
- Market uncertainty
- Defensive positioning

**Allocation:**
- **Individual Stocks**: 15-20% of NAV (defensive, quality names only)
  - Defensive focus: JPM, UNH, JNJ, WMT, HD
  - Quality names: AAPL, MSFT, GOOGL (mega caps only)
  - Reduce tech: Less NVDA, TSLA, AMD
- **ETFs**: 70-75% of NAV (diversification, defensive)
  - Defensive sectors: XLU, XLP, GLD
  - Broad market: EQQQ, XLIS, SPY4
- **Bonds**: 5-10% of NAV (defensive)
- **Cash**: 10-15% of NAV (liquidity)

**Example:**
- Core Macro (60%): ETFs (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT)
- Individual Stocks (15%): AAPL 1.2%, MSFT 1.2%, JPM 1.2%, UNH 1.2%, JNJ 1.2%, BAC 1.1%, V 1.0%, MA 1.0%, WMT 0.8%, HD 0.8%, ... (19 stocks, defensive)
- Tactical (10%): SPY, GLD, XLK
- Emerging Markets (5%): EEM, VWO, EWZ
- Dividends (10%): VIG, XLU, XLP

### RECESSION

**Characteristics:**
- Economic contraction
- Market decline
- Maximum defensive positioning

**Allocation:**
- **Individual Stocks**: 10-15% of NAV (only highest quality)
  - Only quality: AAPL, MSFT, JPM, UNH, JNJ, WMT, HD
  - No growth stocks: No NVDA, TSLA, AMD
  - Defensive only: Finance, healthcare, consumer staples
- **ETFs**: 75-80% of NAV (diversification, defensive)
  - Defensive sectors: XLU, XLP, GLD
  - Broad market: EQQQ, XLIS, SPY4
- **Bonds**: 10-15% of NAV (defensive, income)
- **Cash**: 10-15% of NAV (liquidity, opportunity)

**Example:**
- Core Macro (60%): ETFs (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT)
- Individual Stocks (10%): UNH 1.2%, JNJ 1.2%, JPM 1.0%, AAPL 0.8%, MSFT 0.8%, BAC 0.8%, V 0.7%, MA 0.7%, WMT 0.6%, HD 0.6%, ... (14 stocks, quality only)
- Tactical (10%): SPY, GLD, XLK
- Emerging Markets (5%): EEM, VWO, EWZ
- Dividends (15%): VIG, XLU, XLP

---

## Confidence-Based Allocation

The system adjusts allocation based on **confidence level** (0.0-1.0).

### High Confidence (>=0.6)

**Strategy: Aggressive Stock Picking**
- **Individual Stocks**: 30-40% of NAV
- **Focus**: Tech/AI winners (NVDA, TSLA, AAPL, MSFT, GOOGL, META, AMZN)
- **Sector**: Tech-heavy, growth-oriented
- **Risk**: Higher risk tolerance
- **Example Stocks**: NVDA 2.5%, TSLA 1.9%, AAPL 1.6%, MSFT 1.6%, GOOGL 1.3%, META 1.3%, AMZN 1.3%, JPM 1.2%, BAC 1.0%, UNH 0.9%, ... (30+ stocks)

### Medium Confidence (0.4-0.6)

**Strategy: Balanced Stock Picking**
- **Individual Stocks**: 20-25% of NAV
- **Focus**: Balanced tech + finance + healthcare
- **Sector**: Diversified across sectors
- **Risk**: Moderate risk tolerance
- **Example Stocks**: NVDA 1.8%, TSLA 1.3%, AAPL 1.0%, MSFT 1.0%, JPM 1.3%, BAC 1.0%, UNH 1.0%, JNJ 1.0%, ... (32 stocks)

### Low Confidence (<0.4)

**Strategy: Defensive Stock Picking**
- **Individual Stocks**: 10-15% of NAV
- **Focus**: Defensive, quality names only
- **Sector**: Finance, healthcare, consumer staples
- **Risk**: Lower risk tolerance
- **Example Stocks**: JPM 1.5%, UNH 1.5%, JNJ 1.5%, AAPL 1.5%, MSFT 1.5%, BAC 1.3%, WMT 1.3%, GOOGL 1.2%, V 1.2%, MA 1.2% (22 stocks, defensive)

---

## Sector Rotation Strategy

The system **rotates sectors** based on market regime (like hedge funds).

### EXPANSION → Tech/AI Heavy

**Sector Allocation (within Individual Stocks Sleeve):**
- **Tech/AI**: 40% of sleeve (NVDA, TSLA, AAPL, MSFT, GOOGL, META, AMZN, AMD, AVGO)
- **Finance**: 20% of sleeve (JPM, BAC, GS, V, MA)
- **Healthcare**: 15% of sleeve (UNH, JNJ, LLY, TMO)
- **Consumer**: 10% of sleeve (WMT, HD, COST, NKE)
- **Industrial**: 8% of sleeve (BA, CAT, RTX)
- **Energy**: 5% of sleeve (XOM, CVX)
- **Other**: 2% of sleeve (VZ, NEE)

**Rationale:**
- Tech/AI companies benefit from expansion
- Growth stocks outperform
- Higher risk tolerance

### SLOWDOWN → Defensive Heavy

**Sector Allocation (within Individual Stocks Sleeve):**
- **Tech**: 25% of sleeve (only mega caps: AAPL, MSFT, GOOGL)
- **Finance**: 30% of sleeve (quality banks: JPM, BAC, V, MA)
- **Healthcare**: 30% of sleeve (defensive: UNH, JNJ, PFE)
- **Consumer**: 10% of sleeve (defensive: WMT, HD)
- **Industrial**: 5% of sleeve (only quality: CAT, HON)

**Rationale:**
- Defensive sectors outperform in slowdown
- Quality names are more resilient
- Lower risk tolerance

### RECESSION → Quality Only

**Sector Allocation (within Individual Stocks Sleeve):**
- **Tech**: 20% of sleeve (only mega caps: AAPL, MSFT, GOOGL)
- **Finance**: 30% of sleeve (quality banks: JPM, BAC, V, MA)
- **Healthcare**: 35% of sleeve (defensive: UNH, JNJ, PFE)
- **Consumer**: 10% of sleeve (defensive: WMT, HD)
- **Industrial**: 5% of sleeve (only quality: CAT)

**Rationale:**
- Only highest quality names
- Defensive sectors only
- Minimal risk tolerance

---

## Risk Management

### Position Limits (Hedge Fund Style)

**Individual Stocks:**
- **Max 2% per stock** (hedge fund style)
- **Max 10% per position** (policy limit)
- **Max 30% total individual stocks** (hedge fund max)

**ETFs:**
- **Max 10% per ETF** (policy limit)
- **Max 25% per sector** (policy limit)

**Total Portfolio:**
- **Max 10% per position** (any instrument)
- **Max 25% per sector** (any instrument)
- **Cash floor: 5%** (liquidity)

### Sector Limits

**Max 25% per sector:**
- Tech: Max 25% (ETFs + stocks combined)
- Finance: Max 25% (ETFs + stocks combined)
- Healthcare: Max 25% (ETFs + stocks combined)
- Consumer: Max 25% (ETFs + stocks combined)
- Industrial: Max 25% (ETFs + stocks combined)
- Energy: Max 25% (ETFs + stocks combined)

### Volatility Management

**High Volatility:**
- Reduce individual stocks
- Increase ETFs
- Increase bonds
- Increase cash

**Low Volatility:**
- Increase individual stocks
- Reduce cash
- More aggressive positioning

---

## Execution Process

### Step 1: Regime Detection

The system **automatically detects** market regime:
- **EXPANSION**: Strong economic growth, rising markets
- **RECOVERY**: Market recovering from downturn
- **SLOWDOWN**: Economic slowdown, market uncertainty
- **RECESSION**: Economic contraction, market decline

**How it works:**
- Analyzes market data (prices, volatility, correlations)
- Calculates regime probability
- Selects regime with highest probability
- Calculates confidence level (0.0-1.0)

### Step 2: Confidence Calculation

The system **calculates confidence level**:
- **High (>=0.6)**: Strong regime signal, high confidence
- **Medium (0.4-0.6)**: Moderate regime signal, medium confidence
- **Low (<0.4)**: Weak regime signal, low confidence

**How it works:**
- Analyzes regime signal strength
- Considers historical accuracy
- Calculates confidence score
- Adjusts allocation accordingly

### Step 3: Stock Allocation Decision

The system **decides how much to allocate to individual stocks**:

**Decision Logic:**
```
If EXPANSION:
    If confidence >= 0.6:
        stocks_allocation = 30-40% of NAV
    Else if confidence >= 0.4:
        stocks_allocation = 20-25% of NAV
    Else:
        stocks_allocation = 10-15% of NAV

Else if RECOVERY:
    stocks_allocation = 25-30% of NAV

Else if SLOWDOWN:
    stocks_allocation = 15-20% of NAV

Else if RECESSION:
    stocks_allocation = 10-15% of NAV
```

**Result:**
- **Individual Stocks**: 10-40% of NAV (dynamic)
- **ETFs**: 50-80% of NAV (remaining allocation)

### Step 4: Stock Selection

The system **selects individual stocks** based on:
1. **Regime**: EXPANSION = tech/AI heavy, RECESSION = defensive heavy
2. **Confidence**: High confidence = aggressive, Low confidence = defensive
3. **Whitelist**: Only approved stocks (70+ stocks in whitelist)
4. **Position Limits**: Max 2% per stock
5. **Sector Limits**: Max 25% per sector

**Selection Process:**
1. Filter by whitelist (only approved stocks)
2. Select stocks based on regime (tech in expansion, defensive in recession)
3. Adjust for confidence (high confidence = more tech, low confidence = more defensive)
4. Apply position limits (max 2% per stock)
5. Apply sector limits (max 25% per sector)
6. Normalize weights

### Step 5: ETF Selection

The system **selects ETFs** for:
1. **Core Macro (60%)**: Broad market exposure (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT)
2. **Tactical (10%)**: Momentum plays (SPY, GLD, XLK)
3. **Emerging Markets (13%)**: EM exposure (EEM, VWO, EWZ)
4. **Dividends (17%)**: Income (VIG, XLU, XLP)

**Selection Process:**
1. Filter by whitelist (only approved ETFs)
2. Select ETFs based on regime (growth in expansion, defensive in recession)
3. Apply position limits (max 10% per ETF)
4. Apply sector limits (max 25% per sector)
5. Normalize weights

### Step 6: Execution

The system **executes trades**:
1. **Sell orders first**: Free up cash
2. **Buy orders second**: Deploy cash
3. **Order priority**: Largest allocations first
4. **Rate limiting**: Wait between orders (2 seconds)
5. **Price validation**: Use real-time prices
6. **Spread checking**: Max 60 bps spread
7. **Minimum ticket**: £1.00 minimum

**Execution Order:**
1. Cancel pending orders
2. Sell positions that need to be reduced
3. Buy new positions
4. Update portfolio.json
5. Log executions

---

## Example Allocations

### Example 1: EXPANSION + High Confidence (0.7)

**Portfolio (NAV: £245.90):**

**Core Macro (60% = £147.54):**
- EQQQ: 25.5% of core = £37.62 (ETF)
- SPY4: 23.8% of core = £35.04 (ETF)
- IDUP: 15.8% of core = £23.24 (ETF)
- XLIS: 4.5% of core = £6.64 (ETF)
- XLU: 3.5% of core = £5.16 (ETF)
- XLP: 7.0% of core = £10.33 (ETF)
- GLD: 5.0% of core = £7.38 (ETF)
- IGLT: 4.5% of core = £6.64 (Bond ETF)
- Cash: 10.5% of core = £15.49

**Individual Stocks (30% = £73.77):**
- NVDA: 2.5% of NAV = £6.15 (AI leader)
- TSLA: 1.9% of NAV = £4.67 (EV/AI)
- AAPL: 1.6% of NAV = £3.93 (Tech)
- MSFT: 1.6% of NAV = £3.93 (AI/Cloud)
- GOOGL: 1.3% of NAV = £3.20 (AI/Search)
- META: 1.3% of NAV = £3.20 (AI/Social)
- AMZN: 1.3% of NAV = £3.20 (AI/Cloud)
- JPM: 1.2% of NAV = £2.95 (Finance)
- BAC: 1.0% of NAV = £2.46 (Finance)
- UNH: 0.9% of NAV = £2.21 (Healthcare)
- ... (30+ stocks total)

**Tactical (10% = £24.59):**
- SPY: 40.6% of tactical = £9.99 (ETF)
- GLD: 12.2% of tactical = £3.00 (ETF)
- XLK: 12.2% of tactical = £3.00 (ETF)
- Cash: 35.0% of tactical = £8.61

**Emerging Markets (5% = £12.30):**
- EEM: 35.0% of EM = £4.30 (ETF)
- VWO: 26.2% of EM = £3.22 (ETF)
- EWZ: 8.8% of EM = £1.08 (ETF)
- Cash: 30.0% of EM = £3.69

**Dividends (5% = £12.30):**
- VIG: 35.6% of div = £4.38 (ETF)
- XLU: 26.7% of div = £3.28 (ETF)
- XLP: 17.8% of div = £2.19 (ETF)
- Cash: 20.0% of div = £2.46

**Total:**
- ETFs: 50% = £122.95
- Individual Stocks: 30% = £73.77
- Bonds: 3% = £7.38
- Gold: 2% = £4.92
- Cash: 15% = £36.89

### Example 2: EXPANSION + Low Confidence (0.3)

**Portfolio (NAV: £245.90):**

**Core Macro (60% = £147.54):**
- Same as Example 1

**Individual Stocks (10% = £24.59):**
- JPM: 1.5% of NAV = £3.69 (Finance)
- UNH: 1.5% of NAV = £3.69 (Healthcare)
- JNJ: 1.5% of NAV = £3.69 (Healthcare)
- AAPL: 1.5% of NAV = £3.69 (Tech - quality)
- MSFT: 1.5% of NAV = £3.69 (Tech - quality)
- BAC: 1.3% of NAV = £3.20 (Finance)
- WMT: 1.3% of NAV = £3.20 (Consumer)
- GOOGL: 1.2% of NAV = £2.95 (Tech - quality)
- V: 1.2% of NAV = £2.95 (Finance)
- MA: 1.2% of NAV = £2.95 (Finance)
- ... (22 stocks total, defensive)

**Tactical (10% = £24.59):**
- Same as Example 1

**Emerging Markets (13% = £31.97):**
- EEM: 35.0% of EM = £11.19 (ETF)
- VWO: 26.2% of EM = £8.38 (ETF)
- EWZ: 8.8% of EM = £2.81 (ETF)
- Cash: 30.0% of EM = £9.59

**Dividends (17% = £41.80):**
- VIG: 35.6% of div = £14.88 (ETF)
- XLU: 26.7% of div = £11.16 (ETF)
- XLP: 17.8% of div = £7.44 (ETF)
- Cash: 20.0% of div = £8.36

**Total:**
- ETFs: 60% = £147.54
- Individual Stocks: 10% = £24.59
- Bonds: 3% = £7.38
- Gold: 2% = £4.92
- Cash: 25% = £61.47

### Example 3: RECESSION + Low Confidence (0.3)

**Portfolio (NAV: £245.90):**

**Core Macro (60% = £147.54):**
- Same as Example 1 (defensive ETFs)

**Individual Stocks (10% = £24.59):**
- UNH: 1.2% of NAV = £2.95 (Healthcare - defensive)
- JNJ: 1.2% of NAV = £2.95 (Healthcare - defensive)
- JPM: 1.0% of NAV = £2.46 (Finance - quality)
- AAPL: 0.8% of NAV = £1.97 (Tech - quality)
- MSFT: 0.8% of NAV = £1.97 (Tech - quality)
- BAC: 0.8% of NAV = £1.97 (Finance - quality)
- V: 0.7% of NAV = £1.72 (Finance - quality)
- MA: 0.7% of NAV = £1.72 (Finance - quality)
- WMT: 0.6% of NAV = £1.48 (Consumer - defensive)
- HD: 0.4% of NAV = £0.98 (Consumer - defensive)
- ... (14 stocks total, quality only)

**Tactical (10% = £24.59):**
- Same as Example 1 (defensive)

**Emerging Markets (5% = £12.30):**
- Same as Example 1

**Dividends (15% = £36.89):**
- VIG: 35.6% of div = £13.13 (ETF)
- XLU: 26.7% of div = £9.85 (ETF)
- XLP: 17.8% of div = £6.57 (ETF)
- Cash: 20.0% of div = £7.38

**Total:**
- ETFs: 70% = £172.13
- Individual Stocks: 10% = £24.59
- Bonds: 5% = £12.30
- Gold: 2% = £4.92
- Cash: 13% = £31.97

---

## How It Compares to Hedge Funds

### Bridgewater Associates

**Portfolio Structure:**
- Core Holdings (50%): ETFs, bonds, commodities
- Individual Stocks (30%): Direct stock picks
- Tactical (10%): ETFs + some stocks
- Other (10%): Bonds, commodities

**Decision Logic:**
- Regime-based allocation
- Confidence-based stock picking
- Sector rotation
- Risk management

**HEDGE System:**
- ✅ Same structure (Core 60% + Individual Stocks 10-30% + Tactical 10% + Other)
- ✅ Same decision logic (regime-based, confidence-based)
- ✅ Same sector rotation
- ✅ Same risk management

### Renaissance Technologies

**Portfolio Structure:**
- Core Holdings (40%): ETFs, bonds
- Individual Stocks (40%): Quantitative stock picking
- Tactical (10%): ETFs + some stocks
- Other (10%): Bonds, commodities

**Decision Logic:**
- Quantitative models
- High stock allocation
- Tech/AI heavy
- Risk management

**HEDGE System:**
- ✅ Similar structure (Core 60% + Individual Stocks 10-30% + Tactical 10% + Other)
- ✅ Regime-based models (similar to quantitative)
- ✅ Tech/AI heavy in expansion
- ✅ Same risk management

### BlackRock

**Portfolio Structure:**
- Core Holdings (60%): ETFs, bonds
- Individual Stocks (30%): Direct stock picks
- Tactical (5%): ETFs + some stocks
- Other (5%): Bonds, commodities

**Decision Logic:**
- Long-term strategic allocation
- Individual stocks for alpha
- Sector diversification
- Risk management

**HEDGE System:**
- ✅ Same structure (Core 60% + Individual Stocks 10-30% + Tactical 10% + Other)
- ✅ Same decision logic (strategic + tactical)
- ✅ Same sector diversification
- ✅ Same risk management

### Goldman Sachs

**Portfolio Structure:**
- Core Holdings (50%): ETFs, bonds
- Individual Stocks (35%): Direct stock picks
- Tactical (10%): ETFs + some stocks
- Other (5%): Bonds, commodities

**Decision Logic:**
- Regime-based allocation
- High stock allocation
- Sector rotation
- Risk management

**HEDGE System:**
- ✅ Similar structure (Core 60% + Individual Stocks 10-30% + Tactical 10% + Other)
- ✅ Same decision logic (regime-based, sector rotation)
- ✅ Similar stock allocation (10-30% dynamic)
- ✅ Same risk management

---

## Institutional-Style Rebalancing (Hold Forever, Layer, Tilt)

### How Institutions Actually Trade

**Big funds, banks, and asset managers rarely sell everything** — they **layer**, **rebalance**, and **tilt** rather than "enter" or "exit" in the retail sense.

### Persistent Core Holdings (Hold Forever)

**Core Macro (60%)** is designed to stay invested for **years or decades**:

- **Persistent Holdings**: EQQQ, XLIS, SPY4, IDUP, IGLT, GLD
- **Holding Period**: 1-10 years (rarely changes)
- **Rebalancing**: Only on large drift (>10%) or quarterly
- **Strategy**: Permanent capital, strategic asset allocation (SAA)

**How it works:**
- System marks core holdings as "persistent"
- Only rebalances if drift > 10% (vs 5% for satellites)
- Skips small drift trades (<10%) for persistent holdings
- Holds positions indefinitely, just adjusts proportions

### Satellite Holdings (Layer, Tilt)

**Satellite Sleeves (40%)** are dynamic and change more frequently:

- **Tactical (10%)**: Rebalance monthly or on regime change
- **Emerging Markets (13%)**: Rebalance quarterly
- **Dividends (17%)**: Rebalance annually
- **Individual Stocks (10-30%)**: Rebalance monthly

**How it works:**
- Rebalances on normal drift (>5%)
- Changes with regime shifts
- Still not "day trades" — think in **months**, not hours

### Rebalancing Logic

**Step 1: Check Regime Change**
- If regime changed → Full rebalance (overrides persistent holdings)

**Step 2: Check Drift**
- **Persistent Holdings**: Only rebalance if drift > 10%
- **Satellite Holdings**: Rebalance if drift > 5%

**Step 3: Trade Only the Difference**
- Don't dump everything
- Trade only the drift (e.g., if bonds are 2% overweight, sell 2%, not all)
- Reinvest proceeds into underweight assets

**Step 4: Skip Small Trades**
- Skip persistent holdings with drift < 10%
- Skip satellite holdings with drift < 5%
- Skip orders < £1.00

### Time Horizons

| Sleeve                        | Horizon         | Trade Frequency              | Typical Holding Period      |
| ----------------------------- | --------------- | ---------------------------- | --------------------------- |
| **Core Macro (60%)**          | Strategic       | Quarterly or large drift (>10%) | 1–10 years (rarely changes) |
| **Tactical (10%)**            | Medium-term     | Monthly or regime change    | 3–12 months typical         |
| **Emerging Markets (13%)**    | Regime-tilt     | Quarterly                    | 6–18 months                 |
| **Dividends (17%)**           | Long-term yield | Annually                     | Multi-year holdings         |
| **Individual Stocks (10-30%)** | Medium-term     | Monthly                      | 3–12 months                |

### Result

**Stable Compounding with Low Turnover:**
- Core holdings held for years (low turnover)
- Satellite holdings rebalanced as needed (moderate turnover)
- No "flipping" — only adjusting capital weightings
- Exactly how large funds maintain long-term positions

---

## Summary

### How the System Works

1. **Regime Detection**: System automatically detects market regime (EXPANSION, RECOVERY, SLOWDOWN, RECESSION)

2. **Confidence Calculation**: System calculates confidence level (0.0-1.0)

3. **Stock Allocation Decision**: System decides how much to allocate to individual stocks (10-40% of NAV)

4. **Stock Selection**: System selects individual stocks based on regime, confidence, and whitelist

5. **ETF Selection**: System selects ETFs for diversification and broad market exposure

6. **Institutional-Style Rebalancing**: 
   - **Persistent Core Holdings**: Hold forever, only rebalance on large drift (>10%) or quarterly
   - **Satellite Holdings**: Rebalance monthly or on regime change
   - **Trade Only Drift**: Don't dump everything, trade only the difference

7. **Execution**: System executes trades (sells first, then buys), skipping small drift trades for persistent holdings

### Key Features

✅ **Regime-Based**: Automatically adjusts based on market regime
✅ **Confidence-Based**: Adjusts based on confidence level
✅ **Sector Rotation**: Rotates sectors based on regime
✅ **Risk Management**: Position limits, sector limits, volatility management
✅ **Hedge Fund Style**: Same structure and decision logic as hedge funds
✅ **Dynamic Allocation**: Individual stocks allocation changes with regime/confidence
✅ **Diversification**: ETFs provide broad market exposure
✅ **Alpha Generation**: Individual stocks provide direct exposure to winners

### Result

**Portfolio Structure (Like Hedge Funds):**
- **50-60% ETFs**: Diversification, broad market exposure
- **10-30% Individual Stocks**: Alpha generation, direct exposure to winners
- **3-5% Bonds**: Defensive, income
- **2-3% Gold**: Real assets, inflation hedge
- **5-10% Cash**: Liquidity, opportunity fund

**This is EXACTLY how hedge funds structure their portfolios!**

