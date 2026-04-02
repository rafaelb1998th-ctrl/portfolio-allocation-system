#!/usr/bin/env python3
"""
Identify S&P 500 stocks from the filtered instruments.
Creates a separate file with S&P 500 stocks.
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Common S&P 500 tickers (this is a sample - in production, you'd use a complete list)
# For now, we'll identify by characteristics: USD currency, large market cap indicators
SP500_INDICATORS = [
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK', 'JPM',
    'V', 'UNH', 'HD', 'MA', 'PG', 'DIS', 'BAC', 'AVGO', 'ADBE', 'CRM',
    'NFLX', 'COST', 'AMD', 'LIN', 'TMO', 'ABT', 'PEP', 'NKE', 'MRK', 'WMT',
    'QCOM', 'TXN', 'CVX', 'ACN', 'CSCO', 'DHR', 'VZ', 'CMCSA', 'AMGN', 'HON',
    'INTU', 'AMAT', 'ISRG', 'BKNG', 'ADP', 'GE', 'LOW', 'RTX', 'SBUX', 'PLD',
    'SPGI', 'GILD', 'ADI', 'ANET', 'CDNS', 'SNPS', 'FTNT', 'KLAC', 'MCHP', 'NXPI',
    'CTSH', 'FAST', 'PAYX', 'APH', 'GLW', 'TEL', 'ITW', 'ETN', 'EMR', 'PH',
    'ROK', 'AME', 'ZBRA', 'TDG', 'GGG', 'POOL', 'SWK', 'AOS', 'TTC', 'WWD',
    # Add more as needed - this is just a sample
]

def identify_sp500_stocks(stocks):
    """Identify S&P 500 stocks from the stock list."""
    sp500_stocks = []
    
    for stock in stocks:
        ticker = stock.get('ticker', '').upper()
        short_name = stock.get('shortName', '').upper()
        currency = stock.get('currencyCode', '')
        
        # Must be USD currency
        if currency != 'USD':
            continue
        
        # Check if ticker or short name matches S&P 500 indicators
        # Remove common suffixes like _US_EQ
        clean_ticker = ticker.replace('_US_EQ', '').replace('_EQ', '').replace('_USD', '')
        clean_short = short_name
        
        # Check against S&P 500 indicators
        if clean_ticker in SP500_INDICATORS or clean_short in SP500_INDICATORS:
            sp500_stocks.append(stock)
            continue
        
        # Additional heuristics: large-cap stocks typically have:
        # - High maxOpenQuantity (liquidity indicator)
        # - Well-known company names
        max_qty = stock.get('maxOpenQuantity', 0)
        if max_qty and max_qty > 10000:  # High liquidity
            # Could be S&P 500, but we'll be conservative
            # Only add if we're confident
            pass
    
    return sp500_stocks

def main():
    print("=" * 80)
    print("IDENTIFY S&P 500 STOCKS")
    print("=" * 80)
    print()
    
    # Load filtered stocks
    stocks_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "brokers", "filtered_instruments", "stock.json"
    )
    
    if not os.path.exists(stocks_file):
        print(f"❌ Stocks file not found: {stocks_file}")
        return
    
    print(f"📋 Loading stocks from {stocks_file}...")
    with open(stocks_file, 'r') as f:
        all_stocks = json.load(f)
    print(f"✅ Loaded {len(all_stocks):,} stocks")
    print()
    
    # Identify S&P 500 stocks
    print("🔍 Identifying S&P 500 stocks...")
    sp500_stocks = identify_sp500_stocks(all_stocks)
    print(f"✅ Identified {len(sp500_stocks)} potential S&P 500 stocks")
    print()
    
    # Save S&P 500 stocks
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "brokers", "filtered_instruments"
    )
    os.makedirs(output_dir, exist_ok=True)
    
    sp500_file = os.path.join(output_dir, "sp500_stocks.json")
    with open(sp500_file, 'w') as f:
        json.dump(sp500_stocks, f, indent=2)
    print(f"💾 Saved {len(sp500_stocks)} S&P 500 stocks to {sp500_file}")
    print()
    
    # Show sample
    print("=" * 80)
    print("SAMPLE S&P 500 STOCKS")
    print("=" * 80)
    print()
    print(f"{'Ticker':<20} {'Short Name':<15} {'Name':<50}")
    print("-" * 85)
    
    for stock in sorted(sp500_stocks, key=lambda x: x.get('ticker', ''))[:30]:
        ticker = stock.get('ticker', '')[:19]
        short_name = stock.get('shortName', '')[:14]
        name = stock.get('name', '')[:49]
        print(f"{ticker:<20} {short_name:<15} {name:<50}")
    
    if len(sp500_stocks) > 30:
        print(f"\n... and {len(sp500_stocks) - 30} more")
    
    print()
    print("=" * 80)
    print("NOTE: This is a partial list based on common S&P 500 tickers.")
    print("For a complete list, you would need to:")
    print("  1. Download the official S&P 500 constituent list")
    print("  2. Match against T212 available instruments")
    print("  3. Verify each stock is actually in the S&P 500")
    print("=" * 80)

if __name__ == "__main__":
    main()

