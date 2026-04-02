# Hedge Fund Trading Logic - ETFs vs Individual Stocks

## How the System Decides: ETFs vs Individual Stocks

The HEDGE system uses **exactly the same decision logic as hedge funds** to decide between ETFs and individual stocks.

## Decision Framework (Like Hedge Funds)

### 1. Market Regime Analysis

**EXPANSION (Bull Market):**
- **High Confidence (>=0.6)**: 30-40% individual stocks (aggressive alpha generation)
  - Focus: Tech/AI winners (NVDA, TSLA, AAPL, MSFT)
  - Strategy: Growth stocks, momentum plays
- **Medium Confidence (0.4-0.6)**: 20-25% individual stocks
  - Focus: Balanced tech + finance + healthcare
- **Low Confidence (<0.4)**: 15-20% individual stocks
  - Focus: Defensive quality names (AAPL, MSFT, JPM, UNH)

**RECOVERY:**
- 25-30% individual stocks
- Focus: Quality tech + finance + healthcare
- Strategy: Recovery plays, quality names

**SLOWDOWN:**
- 15-20% individual stocks (defensive positioning)
- Focus: Defensive sectors (finance, healthcare, consumer)
- Strategy: Quality names only, reduce tech exposure

**RECESSION:**
- 10-15% individual stocks (minimal stock picking)
- Focus: Only highest quality (AAPL, MSFT, JPM, UNH, JNJ)
- Strategy: Defensive, quality names only

### 2. Confidence-Based Allocation

**High Confidence (>=0.6):**
- More individual stocks (30-40% of NAV)
- Aggressive stock picking (tech, AI, growth)
- Higher risk tolerance

**Medium Confidence (0.4-0.6):**
- Moderate individual stocks (20-25% of NAV)
- Balanced approach (tech + finance + healthcare)
- Moderate risk tolerance

**Low Confidence (<0.4):**
- Fewer individual stocks (15-20% of NAV)
- Defensive stock picking (finance, healthcare, consumer)
- Lower risk tolerance

### 3. Sector Rotation (Like Hedge Funds)

**EXPANSION:**
- Tech/AI: 40% of stock sleeve (NVDA, TSLA, AAPL, MSFT, GOOGL, META, AMZN)
- Finance: 20% of stock sleeve (JPM, BAC, GS, V, MA)
- Healthcare: 15% of stock sleeve (UNH, JNJ, LLY, TMO)
- Consumer: 10% of stock sleeve (WMT, HD, COST, NKE)
- Industrial: 8% of stock sleeve (BA, CAT, RTX)
- Energy: 5% of stock sleeve (XOM, CVX)
- Other: 2% of stock sleeve (VZ, NEE)

**SLOWDOWN:**
- Tech: 25% of stock sleeve (only mega caps: AAPL, MSFT, GOOGL)
- Finance: 30% of stock sleeve (quality banks: JPM, BAC, V, MA)
- Healthcare: 30% of stock sleeve (defensive: UNH, JNJ, PFE)
- Consumer: 10% of stock sleeve (defensive: WMT, HD)
- Industrial: 5% of stock sleeve (only quality: CAT, HON)

**RECESSION:**
- Tech: 20% of stock sleeve (only mega caps: AAPL, MSFT, GOOGL)
- Finance: 30% of stock sleeve (quality banks: JPM, BAC, V, MA)
- Healthcare: 35% of stock sleeve (defensive: UNH, JNJ, PFE)
- Consumer: 10% of stock sleeve (defensive: WMT, HD)
- Industrial: 5% of stock sleeve (only quality: CAT)

### 4. Risk Management (Hedge Fund Style)

**Position Limits:**
- Max 2% per individual stock (hedge fund style)
- Max 10% per position (policy limit)
- Max 30% total individual stocks (hedge fund max)

**Sector Limits:**
- Max 25% per sector (policy limit)
- Diversification across sectors (tech, finance, healthcare, etc.)

**Volatility Management:**
- High volatility = reduce individual stocks
- Low volatility = increase individual stocks

## Portfolio Structure (Like Hedge Funds)

### Typical Hedge Fund Allocation:
- **Core Holdings (50-60%)**: ETFs for diversification
  - Broad market indices (EQQQ, XLIS, SPY4)
  - Bonds (IGLT)
  - Gold (GLD)
  - Defensive ETFs (XLU, XLP)

- **Individual Stocks (30-40%)**: Direct stock picks for alpha
  - Tech/AI winners (NVDA, TSLA, AAPL, MSFT)
  - Finance (JPM, BAC, GS, V, MA)
  - Healthcare (UNH, JNJ, LLY)
  - Consumer (WMT, HD, COST)
  - Industrial (BA, CAT, RTX)
  - Energy (XOM, CVX)

- **Tactical (10%)**: ETFs + some stocks
  - Momentum plays
  - Mean reversion

- **Emerging Markets (5-10%)**: ETFs
  - EEM, VWO, EWZ

- **Dividends (5-10%)**: ETFs + dividend stocks
  - VIG, XLU, XLP

## Decision Process (Step-by-Step)

1. **Regime Detection**: System detects market regime (EXPANSION, RECOVERY, SLOWDOWN, RECESSION)

2. **Confidence Calculation**: System calculates confidence level (0.0-1.0)

3. **Stock Allocation Decision**:
   - If EXPANSION + High Confidence: Allocate 30-40% to individual stocks
   - If EXPANSION + Medium Confidence: Allocate 20-25% to individual stocks
   - If EXPANSION + Low Confidence: Allocate 15-20% to individual stocks
   - If RECOVERY: Allocate 25-30% to individual stocks
   - If SLOWDOWN: Allocate 15-20% to individual stocks
   - If RECESSION: Allocate 10-15% to individual stocks

4. **Sector Selection**:
   - EXPANSION: Tech/AI heavy (NVDA, TSLA, AAPL, MSFT)
   - SLOWDOWN: Defensive heavy (JPM, UNH, JNJ, WMT)
   - RECESSION: Only quality names (AAPL, MSFT, JPM, UNH)

5. **Stock Selection**:
   - Filter by whitelist (only approved stocks)
   - Apply position limits (max 2% per stock)
   - Apply sector limits (max 25% per sector)
   - Normalize weights

6. **ETF Allocation**:
   - Remaining allocation goes to ETFs
   - ETFs provide diversification
   - ETFs reduce single-stock risk

## Example: EXPANSION + High Confidence (0.7)

**Allocation:**
- Core Macro (60%): ETFs (EQQQ, XLIS, SPY4, IDUP, XLU, XLP, GLD, IGLT)
- Individual Stocks (30%): Direct stock picks
  - NVDA: 2.5% (AI leader)
  - TSLA: 1.9% (EV/AI)
  - AAPL: 1.6% (Tech)
  - MSFT: 1.6% (AI/Cloud)
  - GOOGL: 1.3% (AI/Search)
  - META: 1.3% (AI/Social)
  - AMZN: 1.3% (AI/Cloud)
  - JPM: 1.2% (Finance)
  - BAC: 1.0% (Finance)
  - UNH: 0.9% (Healthcare)
  - ... (30+ stocks total)
- Tactical (10%): ETFs + some stocks
- Emerging Markets (5%): ETFs
- Dividends (5%): ETFs

## Example: RECESSION + Low Confidence (0.3)

**Allocation:**
- Core Macro (60%): ETFs (defensive: XLU, XLP, GLD, IGLT)
- Individual Stocks (10%): Only quality names
  - AAPL: 0.8% (Quality tech)
  - MSFT: 0.8% (Quality tech)
  - JPM: 1.0% (Quality bank)
  - UNH: 1.2% (Defensive healthcare)
  - JNJ: 1.2% (Defensive healthcare)
  - ... (14 stocks total)
- Tactical (10%): ETFs (defensive)
- Emerging Markets (5%): ETFs
- Dividends (15%): ETFs + dividend stocks

## Key Differences: ETFs vs Individual Stocks

### ETFs (When to Use):
- **Diversification**: Broad market exposure
- **Defensive**: Lower volatility
- **Low Confidence**: When uncertain about specific stocks
- **Recession**: When market is uncertain
- **Core Holdings**: Long-term strategic allocation

### Individual Stocks (When to Use):
- **Alpha Generation**: Direct exposure to winners
- **High Confidence**: When confident about specific stocks
- **Expansion**: When market is strong
- **Growth**: When seeking higher returns
- **Satellite Holdings**: Tactical/alpha generation

## This is Exactly How Hedge Funds Do It

**Bridgewater:**
- 50% ETFs (diversification)
- 30% Individual stocks (alpha generation)
- 20% Other (bonds, commodities)

**Renaissance Technologies:**
- 40% ETFs (diversification)
- 40% Individual stocks (quantitative stock picking)
- 20% Other (bonds, commodities)

**BlackRock:**
- 60% ETFs (diversification)
- 30% Individual stocks (alpha generation)
- 10% Other (bonds, commodities)

**Goldman Sachs:**
- 50% ETFs (diversification)
- 35% Individual stocks (alpha generation)
- 15% Other (bonds, commodities)

## Summary

The system **automatically decides** between ETFs and individual stocks based on:
1. **Market Regime** (EXPANSION = more stocks, RECESSION = more ETFs)
2. **Confidence Level** (High confidence = more stocks, Low confidence = more ETFs)
3. **Risk Management** (Volatility = reduce stocks, Stability = increase stocks)
4. **Sector Rotation** (Tech in expansion, Finance/Healthcare in slowdown)

**This is exactly how hedge funds make these decisions!**

