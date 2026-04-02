# Filtered Instruments - Summary

## Overview

This directory contains filtered and categorized instruments from Trading 212 (T212). The instruments have been filtered based on whitelist criteria and organized by type.

## Important Notes

### 1. These are T212-Specific Instruments

**These are NOT all instruments that banks and hedge funds use.** These are only the instruments available through Trading 212's platform. Banks and hedge funds have access to:

- **Much broader universe**: All major exchanges (NYSE, NASDAQ, LSE, etc.)
- **Derivatives**: Options, futures, swaps, forwards
- **Fixed Income**: Corporate bonds, government bonds, municipal bonds
- **Alternative Investments**: Private equity, hedge funds, real estate
- **Structured Products**: Complex derivatives and structured notes
- **Foreign Exchange**: Full forex market access
- **Commodities**: Futures, physical commodities
- **Cryptocurrencies**: Full crypto market access

### 2. S&P 500 Stocks

**Current Status**: We've identified **79 S&P 500 stocks** from the filtered instruments.

**Why not all 500?**
- Not all S&P 500 stocks are available on T212
- T212 focuses on European/UCITS-compliant instruments
- Some stocks may not meet T212's listing requirements
- The identification is based on a sample list - a complete S&P 500 list would need to be downloaded and matched

**To get all 500 S&P 500 stocks:**
1. Download the official S&P 500 constituent list from S&P Dow Jones Indices
2. Match against T212 available instruments
3. Verify each stock is actually available on T212

### 3. Instrument Categories

- **ETF**: 1,952 instruments (UCITS-compliant, approved issuers only)
- **Stock**: 10,460 instruments (USD and other currencies, >=180 days history)
- **REIT**: 32 instruments
- **Bond**: 330 instruments (when bonds are included)
- **Treasury**: 180 instruments (when treasury is included)
- **Commodity**: 225 instruments (when commodities are included)

## Filtering Criteria

### ETFs
- ✅ Approved issuers only: iShares, Vanguard, SPDR, Xtrackers, Invesco, WisdomTree
- ✅ UCITS-compliant (domicile: IE, LU, UK)
- ✅ Minimum 365 days trading history
- ❌ L&G (Legal & General) excluded

### Stocks
- ✅ Minimum 180 days trading history (more lenient than ETFs)
- ✅ Minimum maxOpenQuantity >= 10 (liquidity filter)
- ✅ All currencies allowed (prefer USD/GBP)
- ✅ No issuer restrictions (stocks don't have issuers like ETFs)

### Bonds, Treasury, Commodities, REITs
- ✅ Minimum 365 days trading history
- ✅ Currency preferences applied
- ✅ Liquidity filters applied

## Files

- `etf.json` - All filtered ETFs
- `stock.json` - All filtered stocks (10,460)
- `sp500_stocks.json` - Identified S&P 500 stocks (79)
- `reit.json` - All filtered REITs
- `bond.json` - All filtered bonds
- `treasury.json` - All filtered treasury instruments
- `commodity.json` - All filtered commodities
- `all_filtered.json` - All filtered instruments combined
- `summary.json` - Statistics and filtering criteria

## Next Steps

1. **For S&P 500**: Download official S&P 500 list and match against T212 instruments
2. **For broader universe**: Consider using multiple data sources (Yahoo Finance, Alpha Vantage, etc.)
3. **For derivatives**: T212 doesn't offer options/futures - would need separate data source
4. **For bonds**: T212 has limited bond selection - consider Bloomberg or other fixed income data

## Data Source

- **Platform**: Trading 212
- **Original file**: `brokers/t212_instruments.json` (15,683 instruments)
- **Filtered file**: `t212_all_instruments.json` (12,444 instruments)
- **Filter date**: See `summary.json` for latest filter date

