# AI & Long-Term Investment Strategy

## Overview

This document outlines how the HEDGE system incorporates AI, technology, and long-term thematic investments, similar to how hedge funds and banks structure their portfolios.

## Available Investments

### AI-Specific ETFs (71 available)
- **WTAI** - WisdomTree Artificial Intelligence (Acc) - **RECOMMENDED**
- **XAIX** - Xtrackers Artificial Intelligence & Big Data (Acc)
- **INTL** - WisdomTree Artificial Intelligence (Acc)

### Technology Sector ETFs (42 available)
- **XLK** - Technology Select Sector SPDR - **CURRENTLY IN USE**
- **XLKS** - Invesco Technology S&P US Select Sector
- **WTEC** - SPDR MSCI World Technology
- **WDTE** - Invesco S&P World Information Technology ESG

### Long-Term Theme ETFs (160 available)
- **ESG/Climate**: Clean energy, renewable, sustainable investing
- **Healthcare/Biotech**: Healthcare innovation, biotech
- **Innovation**: Future technologies, innovation themes

## How Hedge Funds & Banks Structure Portfolios

### Typical Institutional Allocation:
1. **Core Holdings (60-70%)**: Broad market indices, bonds, defensive assets
2. **Tactical (10-15%)**: Short-term momentum, mean reversion
3. **Thematic/Long-term (10-20%)**: AI, technology, innovation, ESG themes
4. **Emerging Markets (5-10%)**: Growth opportunities
5. **Income (5-10%)**: Dividends, REITs, bonds

### Examples:
- **Bridgewater**: ~15% in thematic/innovation
- **Renaissance Technologies**: Heavy tech/AI exposure
- **BlackRock**: ~20% in long-term themes (AI, climate, healthcare)
- **Goldman Sachs**: ~15% in thematic investments

## Current HEDGE Strategy

### Current Allocation:
- **Core Macro (60%)**: EQQQ, SPY4, IDUP, XLIS, XLU, XLP, GLD, IGLT
- **Tactical (10%)**: SPY, GLD, XLK (Technology)
- **Emerging Markets (13.2%)**: EEM, VWO, EWZ
- **Dividends (16.8%)**: VIG, XLU, XLP
- **Cash (26.9%)**

### What's Missing:
- **Dedicated AI exposure**: Currently only indirect via EQQQ (Nasdaq 100)
- **Long-term thematic sleeve**: Not explicitly allocated
- **Technology overweight**: Only XLK in tactical (small allocation)

## Recommended Updates

### Option 1: Add Long-Term Thematic Sleeve (10-15% of NAV)
- **WTAI**: 5-7% (AI-specific)
- **XLK**: 3-5% (Technology sector)
- **EQQQ**: 2-3% (Tech-heavy, includes AI companies)

### Option 2: Increase Technology in Existing Sleeves
- **Core Macro**: Add XLK (5% of core = 3% of NAV)
- **Tactical**: Increase XLK from 12% to 25% of tactical (2.5% of NAV)

### Option 3: Hybrid Approach (Recommended)
- **Core Macro (60%)**: Keep as is (includes EQQQ which has AI exposure)
- **Tactical (10%)**: Increase XLK to 20% (2% of NAV)
- **Long-Term Thematic (10%)**: NEW SLEEVE
  - WTAI: 50% of sleeve = 5% of NAV
  - XLK: 30% of sleeve = 3% of NAV
  - EQQQ: 20% of sleeve = 2% of NAV
- **Emerging Markets (10%)**: Reduce from 13.2%
- **Dividends (10%)**: Reduce from 16.8%

## Implementation

The whitelist has been updated to include:
- **WTAI** - WisdomTree Artificial Intelligence
- **XLK** - Technology Select Sector SPDR
- **EQQQ** - Nasdaq 100 (tech-heavy)
- **XLIS** - S&P 500 (includes tech/AI leaders)

These are now available in the `long_term_thematic` bucket in `whitelist.yaml`.

## Next Steps

1. **Update allocator** to include long-term thematic sleeve
2. **Adjust dynamic sleeve allocation** to include thematic (10-15% of NAV)
3. **Run allocator** to generate new targets
4. **Execute trades** to buy AI/tech positions

## Risk Considerations

- **Concentration Risk**: AI/tech can be volatile
- **Sector Risk**: Overweighting technology
- **Mitigation**: 
  - Limit thematic sleeve to 10-15% of NAV
  - Diversify within thematic (AI + Tech + Broad Tech)
  - Maintain defensive assets (bonds, gold, utilities)

