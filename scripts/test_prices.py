#!/usr/bin/env python3
"""
Test script to fetch prices for a few instruments from the updated list.
"""

import sys
import os
import json
import random

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.broker.t212_client import T212

def get_sample_instruments(count=10):
    """Get a sample of instruments from the updated file."""
    instruments_file = os.path.join(project_root, "t212_all_instruments.json")
    
    if not os.path.exists(instruments_file):
        print(f"❌ Instruments file not found: {instruments_file}")
        return []
    
    with open(instruments_file, 'r') as f:
        instruments = json.load(f)
    
    # Get a mix of different types
    stocks = [inst for inst in instruments if inst.get('type') == 'STOCK']
    etfs = [inst for inst in instruments if inst.get('type') == 'ETF']
    
    sample = []
    
    # Add some stocks
    if stocks:
        sample.extend(random.sample(stocks, min(5, len(stocks))))
    
    # Add some ETFs
    if etfs:
        sample.extend(random.sample(etfs, min(5, len(etfs))))
    
    # Limit to requested count
    return sample[:count]

def main():
    print("=" * 70)
    print("TESTING PRICE FETCHING FOR INSTRUMENTS")
    print("=" * 70)
    print()
    
    # Get sample instruments
    print("📋 Loading sample instruments from updated file...")
    sample = get_sample_instruments(10)
    
    if not sample:
        print("❌ No instruments found")
        return
    
    print(f"✅ Selected {len(sample)} sample instruments")
    print()
    
    # Display sample instruments
    print("Sample instruments to test:")
    print("-" * 70)
    for i, inst in enumerate(sample, 1):
        ticker = inst.get('ticker', 'N/A')
        name = inst.get('name', 'N/A')[:50]
        inst_type = inst.get('type', 'N/A')
        short_name = inst.get('shortName', 'N/A')
        print(f"{i:2}. {ticker:20} | {short_name:15} | {inst_type:5} | {name[:40]}")
    print()
    
    # Connect to T212
    try:
        t212 = T212.from_env()
        if not t212.connect():
            print("❌ Failed to connect to Trading 212")
            return
        
        print("✅ Connected to Trading 212")
        print()
        
        # Try two approaches:
        # 1. Use shortName (if it matches symbol mapping)
        # 2. Use ticker directly via API
        
        print(f"📊 Testing price fetching for {len(sample)} instruments...")
        print()
        print("Method 1: Using shortName (symbol mapping)...")
        print("-" * 70)
        
        # Method 1: Try using shortName
        symbols_shortname = []
        symbol_to_ticker = {}
        for inst in sample:
            short_name = inst.get('shortName', '')
            ticker = inst.get('ticker', '')
            if short_name:
                symbols_shortname.append(short_name)
                symbol_to_ticker[short_name] = ticker
        
        quotes1 = t212.get_quotes(symbols_shortname) if symbols_shortname else []
        
        print()
        print("Method 2: Using ticker directly via API...")
        print("-" * 70)
        
        # Method 2: Try using ticker directly
        quotes2 = []
        for inst in sample:
            ticker = inst.get('ticker', '')
            if not ticker:
                continue
            
            try:
                # Call the API directly with the ticker
                response = t212.backend._request("GET", f"/equity/quote/{ticker}")
                if response.status_code == 200:
                    data = response.json()
                    last_price = float(data.get('last', 0) or data.get('price', 0) or 0)
                    bid_price = float(data.get('bid', 0) or 0)
                    ask_price = float(data.get('ask', 0) or 0)
                    
                    if last_price > 0 or bid_price > 0 or ask_price > 0:
                        short_name = inst.get('shortName', ticker)
                        quote = {
                            'symbol': short_name,
                            'ticker': ticker,
                            'bid': bid_price,
                            'ask': ask_price,
                            'last': last_price if last_price > 0 else (ask_price if ask_price > 0 else bid_price)
                        }
                        quotes2.append(quote)
                        print(f"    ✅ {short_name} ({ticker}): ${quote['last']:.2f}")
                    else:
                        print(f"    ⚠️  {ticker}: No price data")
                elif response.status_code == 404:
                    print(f"    ❌ {ticker}: Not found (404)")
                else:
                    print(f"    ❌ {ticker}: Status {response.status_code}")
            except Exception as e:
                print(f"    ❌ {ticker}: Error - {e}")
        
        # Combine results
        quotes = quotes1 + quotes2
        
        print()
        print("=" * 70)
        print("PRICE RESULTS")
        print("=" * 70)
        print()
        
        if quotes:
            print(f"✅ Successfully retrieved {len(quotes)}/{len(sample)} quotes")
            print()
            print(f"{'Symbol':<15} {'Ticker':<25} {'Last Price':<12} {'Bid':<12} {'Ask':<12} {'Status':<10}")
            print("-" * 90)
            
            for quote in quotes:
                # Handle both Quote objects and dicts
                if isinstance(quote, dict):
                    symbol = quote.get('symbol', 'N/A')
                    ticker = quote.get('ticker', 'N/A')
                    last = quote.get('last', 0)
                    bid = quote.get('bid', 0)
                    ask = quote.get('ask', 0)
                else:
                    symbol = quote.get('symbol', 'N/A') if hasattr(quote, 'get') else getattr(quote, 'symbol', 'N/A')
                    ticker = symbol_to_ticker.get(symbol, 'N/A')
                    last = quote.get('last', 0) if hasattr(quote, 'get') else getattr(quote, 'last', 0)
                    bid = quote.get('bid', 0) if hasattr(quote, 'get') else getattr(quote, 'bid', 0)
                    ask = quote.get('ask', 0) if hasattr(quote, 'get') else getattr(quote, 'ask', 0)
                
                if last > 0 or bid > 0 or ask > 0:
                    status = "✅ OK"
                    print(f"{symbol:<15} {ticker:<25} ${last:<11.2f} ${bid:<11.2f} ${ask:<11.2f} {status:<10}")
                else:
                    status = "❌ No data"
                    print(f"{symbol:<15} {ticker:<25} {'N/A':<12} {'N/A':<12} {'N/A':<12} {status:<10}")
            
            # Show summary
            successful = sum(1 for q in quotes if (q.get('last', 0) if isinstance(q, dict) else (q.get('last', 0) if hasattr(q, 'get') else getattr(q, 'last', 0))) > 0)
            print()
            print(f"Summary: {successful}/{len(quotes)} quotes have valid price data")
        else:
            print("❌ No quotes retrieved")
            print()
            print("Possible reasons:")
            print("  - Symbols don't match T212 ticker format")
            print("  - Instruments not available for your account")
            print("  - Rate limiting")
            print("  - Market closed or instruments not tradeable")
        
        print()
        print("=" * 70)
        print("✅ TEST COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

