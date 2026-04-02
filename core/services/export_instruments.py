#!/usr/bin/env python3
"""
Export Trading 212 instruments to Excel/CSV.
Uses the T212 API to get all instruments and saves to Excel format.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from core.broker.t212_client import T212
from datetime import datetime
import json

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

def export_to_excel(instruments, output_file):
    """Export instruments to Excel using pandas."""
    if not PANDAS_AVAILABLE:
        print("⚠️  pandas not available - saving as JSON instead")
        with open(output_file.replace('.xlsx', '.json'), 'w') as f:
            json.dump(instruments, f, indent=2)
        return False
    
    # Define columns to export
    cols = [
        "ticker", "type", "isin", "currencyCode", "name", "shortName",
        "workingScheduleId", "minTradeQuantity", "maxOpenQuantity", "addedOn"
    ]
    
    # Create DataFrame
    data = []
    for inst in instruments:
        row = {}
        for col in cols:
            row[col] = inst.get(col, '')
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Sort by type and ticker
    df.sort_values(["type", "ticker"], inplace=True)
    
    # Save to Excel
    df.to_excel(output_file, index=False, engine='openpyxl')
    return True

def export_to_csv(instruments, output_file):
    """Export instruments to CSV."""
    import csv
    
    cols = [
        "ticker", "type", "isin", "currencyCode", "name", "shortName",
        "workingScheduleId", "minTradeQuantity", "maxOpenQuantity", "addedOn"
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        
        for inst in instruments:
            row = {col: inst.get(col, '') for col in cols}
            writer.writerow(row)

def main():
    print("=" * 70)
    print("TRADING 212 INSTRUMENTS EXPORT")
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
        
        # Get instruments list using the new get_instruments() method
        print("📋 Loading instruments from T212 API...")
        print("⚠️  Rate limit: 1 request per 50 seconds")
        print()
        
        # Use force_refresh to ensure we get fresh data for export
        instruments = t212.get_instruments(use_cache=False, force_refresh=True)
        
        if not instruments:
            print("❌ Failed to load instruments")
            print("   This may be due to rate limiting (1 request per 50 seconds)")
            print("   Please wait and try again later")
            return
        
        print(f"✅ Loaded {len(instruments):,} instruments")
        print()
        
        # Create output directory
        output_dir = os.path.join(project_root, "out")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export to Excel
        excel_file = os.path.join(output_dir, f"t212_instruments_{timestamp}.xlsx")
        print(f"💾 Exporting to Excel: {excel_file}")
        
        if export_to_excel(instruments, excel_file):
            print(f"✅ Saved {len(instruments):,} instruments to Excel")
        else:
            print(f"⚠️  Excel export failed - saved as JSON instead")
        
        # Also export to CSV
        csv_file = os.path.join(output_dir, f"t212_instruments_{timestamp}.csv")
        print(f"💾 Exporting to CSV: {csv_file}")
        export_to_csv(instruments, csv_file)
        print(f"✅ Saved {len(instruments):,} instruments to CSV")
        
        # Save JSON as well
        json_file = os.path.join(output_dir, f"t212_instruments_{timestamp}.json")
        with open(json_file, 'w') as f:
            json.dump(instruments, f, indent=2)
        print(f"💾 Saved JSON: {json_file}")
        
        print()
        print("=" * 70)
        print("✅ EXPORT COMPLETE")
        print("=" * 70)
        print()
        print(f"Files saved to: {output_dir}/")
        print(f"  - {os.path.basename(excel_file)}")
        print(f"  - {os.path.basename(csv_file)}")
        print(f"  - {os.path.basename(json_file)}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

