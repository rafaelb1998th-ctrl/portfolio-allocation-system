#!/usr/bin/env python3
"""
Search Trading 212 instruments by symbol, name, or provider.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.broker.t212_client import T212
import time

def search_instruments(query, instruments):
    """Search instruments by query."""
    query_upper = query.upper()
    results = []
    
    for inst in instruments:
        ticker = inst.get('ticker', '').upper()
        name = inst.get('name', '').upper()
        short_name = inst.get('shortName', '').upper()
        isin = inst.get('isin', '').upper()
        
        if (query_upper in ticker or 
            query_upper in name or 
            query_upper in short_name or
            query_upper in isin):
            results.append(inst)
    
    return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Search Trading 212 instruments')
    parser.add_argument('query', nargs='?', help='Search query (symbol, name, or provider)')
    parser.add_argument('--provider', help='Filter by provider (Vanguard, iShares, SPDR, etc.)')
    parser.add_argument('--type', help='Filter by type (ETF, Stock, REIT, etc.)')
    parser.add_argument('--limit', type=int, default=50, help='Limit results (default: 50)')
    parser.add_argument('--save', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("TRADING 212 INSTRUMENT SEARCH")
    print("=" * 70)
    print()
    
    # Connect to T212
    try:
        t212 = T212.from_env()
        if not t212.connect():
            print("❌ Failed to connect to Trading 212")
            return
        
        print("✅ Connected to Trading 212")
        print()
        
        # Load instruments
        print("📋 Loading instruments...")
        max_retries = 5
        for attempt in range(max_retries):
            response = t212.backend._request("GET", "/equity/metadata/instruments")
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"⚠️  Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed: status {response.status_code}")
                return
        
        if response.status_code != 200:
            print(f"❌ Failed after {max_retries} attempts")
            return
        
        instruments = response.json()
        print(f"✅ Loaded {len(instruments)} instruments")
        print()
        
        # Search or filter
        if args.query:
            results = search_instruments(args.query, instruments)
            print(f"🔍 Search results for '{args.query}': {len(results)} found")
        else:
            results = instruments
            print(f"📋 All instruments: {len(results)}")
        
        # Filter by provider
        if args.provider:
            provider_upper = args.provider.upper()
            results = [inst for inst in results 
                      if provider_upper in inst.get('name', '').upper() or 
                         provider_upper in inst.get('shortName', '').upper()]
            print(f"📊 Filtered by provider '{args.provider}': {len(results)} found")
        
        # Filter by type
        if args.type:
            type_upper = args.type.upper()
            results = [inst for inst in results 
                      if type_upper in inst.get('name', '').upper() or 
                         type_upper in inst.get('shortName', '').upper() or
                         type_upper in inst.get('ticker', '').upper()]
            print(f"📊 Filtered by type '{args.type}': {len(results)} found")
        
        # Limit results
        results = results[:args.limit]
        
        print()
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()
        
        if not results:
            print("No instruments found.")
            return
        
        print(f"{'Ticker':<25} {'Short Name':<40} {'ISIN':<15}")
        print("-" * 80)
        
        for inst in results:
            ticker = inst.get('ticker', '')[:24]
            short_name = inst.get('shortName', '')[:39]
            isin = inst.get('isin', '')[:14]
            print(f"{ticker:<25} {short_name:<40} {isin:<15}")
        
        if args.save:
            with open(args.save, 'w') as f:
                json.dump(results, f, indent=2)
            print()
            print(f"💾 Results saved to: {args.save}")
        
        print()
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

