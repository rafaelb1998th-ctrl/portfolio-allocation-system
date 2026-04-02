#!/usr/bin/env python3
"""
List all instruments available on Trading 212.
Categorizes by type (ETFs, Stocks, etc.) and provider.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.broker.t212_client import T212
import json
from collections import defaultdict

def categorize_instrument(inst):
    """Categorize an instrument by type."""
    ticker = inst.get('ticker', '').upper()
    name = inst.get('name', '').upper()
    short_name = inst.get('shortName', '').upper()
    
    # Check for REIT first (more specific)
    if 'REIT' in name or 'REIT' in short_name:
        return 'REIT'
    
    # Check for bond/fixed income
    if any(x in name or x in short_name for x in ['BOND', 'TREASURY', 'GOVERNMENT', 'CORPORATE', 'FIXED INCOME']):
        return 'Bond'
    
    # Check for commodity
    if any(x in name or x in short_name for x in ['GOLD', 'SILVER', 'OIL', 'COMMODITY']):
        return 'Commodity'
    
    # Check for ETF indicators (must be explicit)
    if any(x in name or x in short_name for x in ['ETF', 'EXCHANGE TRADED FUND', 'ETP', 'ETC']):
        return 'ETF'
    
    # Check for _EQ suffix (usually indicates ETF/ETP on T212)
    if '_EQ' in ticker or '_ETF' in ticker:
        return 'ETF'
    
    # Default to stock
    return 'Stock'

def get_provider(inst):
    """Extract provider from instrument name."""
    name = inst.get('name', '')
    short_name = inst.get('shortName', '')
    
    providers = ['VANGUARD', 'ISHARES', 'SPDR', 'INVESCO', 'WISDOMTREE', 'LEGAL & GENERAL', 'L&G']
    
    for provider in providers:
        if provider in name.upper() or provider in short_name.upper():
            return provider.replace('&', '&').title()
    
    return 'Other'

def main():
    print("=" * 70)
    print("TRADING 212 - ALL INSTRUMENTS")
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
        
        # Get instruments list with retry
        print("📋 Loading all instruments from T212 API...")
        import time
        
        max_retries = 5
        for attempt in range(max_retries):
            response = t212.backend._request("GET", "/equity/metadata/instruments")
            
            if response.status_code == 200:
                break
            elif response.status_code == 429:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️  Rate limited (429). Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"❌ Failed to load instruments: status {response.status_code}")
                return
        
        if response.status_code != 200:
            print(f"❌ Failed to load instruments after {max_retries} attempts")
            return
        
        instruments = response.json()
        print(f"✅ Loaded {len(instruments)} instruments")
        print()
        
        # Categorize instruments
        by_type = defaultdict(list)
        by_provider = defaultdict(list)
        
        for inst in instruments:
            inst_type = categorize_instrument(inst)
            provider = get_provider(inst)
            
            by_type[inst_type].append(inst)
            by_provider[provider].append(inst)
        
        # Display by type
        print("=" * 70)
        print("INSTRUMENTS BY TYPE")
        print("=" * 70)
        print()
        
        for inst_type in sorted(by_type.keys()):
            count = len(by_type[inst_type])
            print(f"{inst_type}: {count} instruments")
        print()
        
        # Display ETFs
        print("=" * 70)
        print("ETFs (First 50)")
        print("=" * 70)
        print()
        print(f"{'Ticker':<20} {'Short Name':<40} {'Provider':<15}")
        print("-" * 75)
        
        etfs = sorted(by_type.get('ETF', []), key=lambda x: x.get('ticker', ''))[:50]
        for etf in etfs:
            ticker = etf.get('ticker', '')[:19]
            short_name = etf.get('shortName', '')[:39]
            provider = get_provider(etf)[:14]
            print(f"{ticker:<20} {short_name:<40} {provider:<15}")
        
        if len(by_type.get('ETF', [])) > 50:
            print(f"\n... and {len(by_type.get('ETF', [])) - 50} more ETFs")
        print()
        
        # Display by provider
        print("=" * 70)
        print("INSTRUMENTS BY PROVIDER (Top 10)")
        print("=" * 70)
        print()
        
        provider_counts = sorted(by_provider.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        for provider, insts in provider_counts:
            print(f"{provider}: {len(insts)} instruments")
        print()
        
        # Save to file
        output_file = "t212_all_instruments.json"
        with open(output_file, 'w') as f:
            json.dump(instruments, f, indent=2)
        
        print(f"💾 Full list saved to: {output_file}")
        print()
        
        # Summary statistics
        print("=" * 70)
        print("SUMMARY STATISTICS")
        print("=" * 70)
        print()
        print(f"Total instruments: {len(instruments)}")
        print(f"ETFs: {len(by_type.get('ETF', []))}")
        print(f"Stocks: {len(by_type.get('Stock', []))}")
        print(f"REITs: {len(by_type.get('REIT', []))}")
        print(f"Bonds: {len(by_type.get('Bond', []))}")
        print(f"Commodities: {len(by_type.get('Commodity', []))}")
        print()
        
        # Show some popular ETFs
        print("=" * 70)
        print("POPULAR ETF PROVIDERS")
        print("=" * 70)
        print()
        
        popular_providers = ['Vanguard', 'iShares', 'SPDR', 'Invesco', 'WisdomTree']
        for provider in popular_providers:
            provider_etfs = [inst for inst in by_type.get('ETF', []) 
                           if provider.upper() in inst.get('name', '').upper() or 
                              provider.upper() in inst.get('shortName', '').upper()]
            if provider_etfs:
                print(f"{provider}: {len(provider_etfs)} ETFs")
                # Show first 5
                for etf in sorted(provider_etfs, key=lambda x: x.get('ticker', ''))[:5]:
                    print(f"  - {etf.get('ticker', ''):<20} {etf.get('shortName', '')[:40]}")
                if len(provider_etfs) > 5:
                    print(f"  ... and {len(provider_etfs) - 5} more")
                print()
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

