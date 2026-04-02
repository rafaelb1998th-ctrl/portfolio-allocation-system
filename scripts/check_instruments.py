#!/usr/bin/env python3
"""
Check instruments used in the system against symbol map.
Provides a summary of what instruments are configured.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.allocation.core_macro import REGIME_TEMPLATES
from core.allocation.tactical_shortterm import get_weights as tactical_weights
from core.allocation.emerging_markets import get_weights as em_weights
from core.allocation.dividends_income import get_weights as div_weights

def get_all_instruments():
    """Get all instruments used across all sleeves."""
    instruments = set()
    
    # From core macro templates
    for regime, weights in REGIME_TEMPLATES.items():
        instruments.update(weights.keys())
    
    # From tactical sleeve (test with sample regimes)
    for regime in ["SLOWDOWN", "EXPANSION"]:
        try:
            weights = tactical_weights(regime, 0.5)
            instruments.update(weights.keys())
        except:
            pass
    
    # From EM sleeve
    for regime in ["SLOWDOWN", "EXPANSION"]:
        try:
            weights = em_weights(regime, 0.5)
            instruments.update(weights.keys())
        except:
            pass
    
    # From dividends sleeve
    for regime in ["SLOWDOWN", "EXPANSION"]:
        try:
            weights = div_weights(regime, 0.5)
            instruments.update(weights.keys())
        except:
            pass
    
    return sorted(instruments)

def main():
    print("=" * 70)
    print("INSTRUMENTS USED IN HEDGE SYSTEM")
    print("=" * 70)
    print()
    
    # Get all instruments
    all_instruments = get_all_instruments()
    
    # Load symbol map
    try:
        with open('brokers/symbol_map.json', 'r') as f:
            symbol_map = json.load(f)
    except:
        symbol_map = {}
    
    # Also try core/broker/symbol_map.json
    try:
        with open('core/broker/symbol_map.json', 'r') as f:
            symbol_map.update(json.load(f))
    except:
        pass
    
    print(f"📋 Total instruments used: {len(all_instruments)}")
    print()
    
    # Categorize instruments
    spdr = []
    vanguard = []
    ishares = []
    other = []
    cash = []
    
    for symbol in all_instruments:
        if symbol == "CASH":
            cash.append(symbol)
            continue
        
        info = symbol_map.get(symbol, {})
        provider = info.get("provider", "").lower()
        
        if "spdr" in provider or symbol in ["XLU", "XLP", "XLV", "XLI", "XLY", "XLK", "XLF", "GLD", "SPY"]:
            spdr.append(symbol)
        elif "vanguard" in provider or symbol.startswith("V"):
            vanguard.append(symbol)
        elif "ishares" in provider or symbol in ["EEM", "EWZ", "SGLN", "IVV"]:
            ishares.append(symbol)
        else:
            other.append(symbol)
    
    print("📊 INSTRUMENTS BY PROVIDER:")
    print()
    
    if spdr:
        print(f"  SPDR ({len(spdr)}):")
        for sym in sorted(spdr):
            info = symbol_map.get(sym, {})
            t212_ticker = info.get("t212", sym)
            note = info.get("note", "")
            print(f"    {sym:6} → {t212_ticker:20} {note}")
        print()
    
    if vanguard:
        print(f"  Vanguard ({len(vanguard)}):")
        for sym in sorted(vanguard):
            info = symbol_map.get(sym, {})
            t212_ticker = info.get("t212", sym)
            note = info.get("note", "")
            print(f"    {sym:6} → {t212_ticker:20} {note}")
        print()
    
    if ishares:
        print(f"  iShares ({len(ishares)}):")
        for sym in sorted(ishares):
            info = symbol_map.get(sym, {})
            t212_ticker = info.get("t212", sym)
            note = info.get("note", "")
            print(f"    {sym:6} → {t212_ticker:20} {note}")
        print()
    
    if other:
        print(f"  Other ({len(other)}):")
        for sym in sorted(other):
            info = symbol_map.get(sym, {})
            t212_ticker = info.get("t212", sym)
            note = info.get("note", "")
            print(f"    {sym:6} → {t212_ticker:20} {note}")
        print()
    
    if cash:
        print(f"  Cash ({len(cash)}):")
        for sym in cash:
            print(f"    {sym}")
        print()
    
    # Check for missing mappings
    missing = []
    for symbol in all_instruments:
        if symbol != "CASH" and symbol not in symbol_map:
            missing.append(symbol)
    
    if missing:
        print("⚠️  INSTRUMENTS WITHOUT SYMBOL MAPPING:")
        for sym in missing:
            print(f"    {sym}")
        print()
        print("   These instruments are used but not in symbol_map.json")
        print("   They may need to be added or verified on Trading 212.")
        print()
    
    print("=" * 70)
    print("VERIFICATION RECOMMENDATION:")
    print("=" * 70)
    print()
    print("To verify these instruments are available on Trading 212:")
    print("  1. Visit: https://www.trading212.com/trading-instruments/invest")
    print("  2. Search for each ticker in the T212 column above")
    print("  3. Or use the T212 app search bar")
    print()
    print("Note: Some instruments may have different tickers on T212")
    print("      (e.g., VUAG vs VUSA, or USD vs GBP versions)")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()

