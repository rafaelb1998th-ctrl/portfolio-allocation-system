#!/usr/bin/env python3
"""
Example script demonstrating how to use the get_instruments() method
to fetch all instruments from Trading 212 API.

Rate Limit: 1 request per 50 seconds
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.broker.t212_client import T212

def main():
    print("=" * 70)
    print("TRADING 212 INSTRUMENTS API EXAMPLE")
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
        
        # Fetch all instruments
        print("📋 Fetching all instruments from Trading 212 API...")
        print("⚠️  Rate limit: 1 request per 50 seconds")
        print()
        
        # Use get_instruments() method
        instruments = t212.get_instruments(use_cache=False, force_refresh=True)
        
        if not instruments:
            print("❌ Failed to fetch instruments")
            print("   This may be due to rate limiting (1 request per 50 seconds)")
            print("   Please wait and try again later")
            return
        
        print(f"✅ Successfully fetched {len(instruments):,} instruments")
        print()
        
        # Display first few instruments as examples
        print("Sample instruments:")
        print("-" * 70)
        for i, inst in enumerate(instruments[:5]):
            ticker = inst.get('ticker', 'N/A')
            name = inst.get('name', 'N/A')
            inst_type = inst.get('type', 'N/A')
            currency = inst.get('currencyCode', 'N/A')
            print(f"{i+1}. {ticker:20} | {name[:40]:40} | {inst_type:10} | {currency}")
        
        if len(instruments) > 5:
            print(f"... and {len(instruments) - 5:,} more instruments")
        
        print()
        print("=" * 70)
        print("✅ EXAMPLE COMPLETE")
        print("=" * 70)
        print()
        print("Usage in your code:")
        print("  from core.broker.t212_client import T212")
        print("  t212 = T212.from_env()")
        print("  t212.connect()")
        print("  instruments = t212.get_instruments()")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

