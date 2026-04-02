#!/usr/bin/env python3
"""
Verify which instruments are available on Trading 212.
Checks all instruments used in the system against T212 API.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.broker.t212_client import T212
from core.utils.io import read_json
import json

# Instruments to check
INSTRUMENTS_TO_CHECK = {
    # SPDR Sector ETFs
    "XLU": {"name": "Utilities Select Sector SPDR", "provider": "SPDR"},
    "XLP": {"name": "Consumer Staples Select Sector SPDR", "provider": "SPDR"},
    "XLV": {"name": "Healthcare Select Sector SPDR", "provider": "SPDR"},
    "XLI": {"name": "Industrial Select Sector SPDR", "provider": "SPDR"},
    "XLY": {"name": "Consumer Discretionary Select Sector SPDR", "provider": "SPDR"},
    "XLK": {"name": "Technology Select Sector SPDR", "provider": "SPDR"},
    "XLF": {"name": "Financial Select Sector SPDR", "provider": "SPDR"},
    "GLD": {"name": "SPDR Gold Trust", "provider": "SPDR"},
    
    # Vanguard ETFs
    "VUAG": {"name": "Vanguard S&P 500 (Acc) - LSE GBP", "provider": "Vanguard"},
    "VUSA": {"name": "Vanguard S&P 500 (Dist) - LSE GBP", "provider": "Vanguard"},
    "VWRP": {"name": "Vanguard FTSE All-World (Acc) - LSE GBP", "provider": "Vanguard"},
    "VFEG": {"name": "Vanguard FTSE Emerging Markets (Acc) - LSE GBP", "provider": "Vanguard"},
    "VOO": {"name": "Vanguard S&P 500 - USD", "provider": "Vanguard"},
    "VTI": {"name": "Vanguard Total Stock Market - USD", "provider": "Vanguard"},
    "VXUS": {"name": "Vanguard Total International - USD", "provider": "Vanguard"},
    "VIG": {"name": "Vanguard Dividend Appreciation - USD", "provider": "Vanguard"},
    
    # iShares ETFs
    "EEM": {"name": "iShares MSCI Emerging Markets - USD", "provider": "iShares"},
    "VWO": {"name": "Vanguard FTSE Emerging Markets - USD", "provider": "Vanguard"},
    "EWZ": {"name": "iShares MSCI Brazil - USD", "provider": "iShares"},
    "SGLN": {"name": "iShares Physical Gold - LSE GBP", "provider": "iShares"},
    
    # Broad Market
    "SPY": {"name": "SPDR S&P 500 - USD", "provider": "SPDR"},
    "IVV": {"name": "iShares Core S&P 500 - USD", "provider": "iShares"},
}

def main():
    print("=" * 70)
    print("TRADING 212 INSTRUMENTS VERIFICATION")
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
        
        # Get instruments list from API
        print("📋 Loading instruments list from T212 API...")
        if hasattr(t212.backend, '_instruments_list') and t212.backend._instruments_list:
            instruments = t212.backend._instruments_list
        else:
            # Force load instruments
            response = t212.backend._request("GET", "/equity/metadata/instruments")
            if response.status_code == 200:
                instruments = response.json()
                t212.backend._instruments_list = instruments if isinstance(instruments, list) else []
            else:
                print(f"❌ Failed to load instruments: status {response.status_code}")
                return
        
        print(f"✅ Loaded {len(instruments)} instruments from T212")
        print()
        
        # Load symbol mapping
        try:
            with open('brokers/symbol_map.json', 'r') as f:
                symbol_map = json.load(f)
        except:
            symbol_map = {}
        
        # Check each instrument
        print("🔍 Checking instruments...")
        print()
        
        results = {
            "available": [],
            "not_found": [],
            "needs_verification": []
        }
        
        for symbol, info in INSTRUMENTS_TO_CHECK.items():
            # Try to find instrument
            t212_ticker = None
            
            # Check symbol mapping first
            if symbol in symbol_map:
                t212_ticker = symbol_map[symbol].get('t212')
            
            # Try to find in instruments list
            found = False
            found_ticker = None
            
            # Search by ISIN if available
            if symbol in symbol_map and symbol_map[symbol].get('isin'):
                target_isin = symbol_map[symbol]['isin']
                for inst in instruments:
                    if inst.get('isin') == target_isin:
                        found = True
                        found_ticker = inst.get('ticker', '')
                        break
            
            # Search by ticker
            if not found:
                for inst in instruments:
                    ticker = inst.get('ticker', '')
                    short_name = inst.get('shortName', '')
                    
                    # Check various formats
                    if (ticker == symbol or 
                        ticker == f"{symbol}_US_EQ" or 
                        ticker == f"{symbol}_US_ETF" or
                        ticker.startswith(f"{symbol}") and ticker.endswith("_EQ") or
                        short_name == symbol):
                        found = True
                        found_ticker = ticker
                        break
            
            if found:
                results["available"].append({
                    "symbol": symbol,
                    "t212_ticker": found_ticker,
                    "name": info["name"],
                    "provider": info["provider"]
                })
            else:
                results["not_found"].append({
                    "symbol": symbol,
                    "name": info["name"],
                    "provider": info["provider"]
                })
        
        # Print results
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()
        
        print(f"✅ AVAILABLE ({len(results['available'])}):")
        for item in results["available"]:
            print(f"   {item['symbol']:6} → {item['t212_ticker']:20} ({item['provider']})")
        print()
        
        if results["not_found"]:
            print(f"❌ NOT FOUND ({len(results['not_found'])}):")
            for item in results["not_found"]:
                print(f"   {item['symbol']:6} → {item['name']} ({item['provider']})")
            print()
            print("⚠️  These instruments may not be available on Trading 212")
            print("   or may need different ticker symbols.")
            print()
        
        print("=" * 70)
        print(f"Summary: {len(results['available'])}/{len(INSTRUMENTS_TO_CHECK)} instruments found")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

