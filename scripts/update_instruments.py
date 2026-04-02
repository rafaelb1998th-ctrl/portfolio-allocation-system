#!/usr/bin/env python3
"""
Update all instrument files with fresh data from Trading 212 API.
Deletes old files and saves new ones.
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.broker.t212_client import T212

def main():
    print("=" * 70)
    print("UPDATING TRADING 212 INSTRUMENTS")
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
        
        # Fetch fresh instruments
        print("📋 Fetching fresh instruments from Trading 212 API...")
        print("⚠️  Rate limit: 1 request per 50 seconds")
        print()
        
        instruments = t212.get_instruments(use_cache=False, force_refresh=True)
        
        if not instruments:
            print("❌ Failed to fetch instruments")
            return
        
        print(f"✅ Successfully fetched {len(instruments):,} instruments")
        print()
        
        # Delete old files
        print("🗑️  Deleting old instrument files...")
        old_files = [
            os.path.join(project_root, "t212_all_instruments.json"),
            os.path.join(project_root, "brokers", "t212_instruments.json"),
        ]
        
        # Also delete old files in out/ directory
        out_dir = os.path.join(project_root, "out")
        if os.path.exists(out_dir):
            for file in os.listdir(out_dir):
                if file.startswith("t212_instruments_") and file.endswith((".json", ".csv", ".xlsx")):
                    old_files.append(os.path.join(out_dir, file))
        
        deleted_count = 0
        for file_path in old_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"   ✅ Deleted: {os.path.basename(file_path)}")
                    deleted_count += 1
                except Exception as e:
                    print(f"   ⚠️  Could not delete {os.path.basename(file_path)}: {e}")
        
        print(f"   ✅ Deleted {deleted_count} old file(s)")
        print()
        
        # Save new files
        print("💾 Saving new instrument files...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Save to root: t212_all_instruments.json
        root_file = os.path.join(project_root, "t212_all_instruments.json")
        with open(root_file, 'w') as f:
            json.dump(instruments, f, indent=2)
        print(f"   ✅ Saved: t212_all_instruments.json ({len(instruments):,} instruments)")
        
        # 2. Save to brokers/t212_instruments.json
        brokers_dir = os.path.join(project_root, "brokers")
        os.makedirs(brokers_dir, exist_ok=True)
        brokers_file = os.path.join(brokers_dir, "t212_instruments.json")
        with open(brokers_file, 'w') as f:
            json.dump(instruments, f, indent=2)
        print(f"   ✅ Saved: brokers/t212_instruments.json ({len(instruments):,} instruments)")
        
        # 3. Save to out/ with timestamp
        out_dir = os.path.join(project_root, "out")
        os.makedirs(out_dir, exist_ok=True)
        
        # JSON
        out_json = os.path.join(out_dir, f"t212_instruments_{timestamp}.json")
        with open(out_json, 'w') as f:
            json.dump(instruments, f, indent=2)
        print(f"   ✅ Saved: out/t212_instruments_{timestamp}.json")
        
        # CSV
        try:
            import csv
            out_csv = os.path.join(out_dir, f"t212_instruments_{timestamp}.csv")
            cols = [
                "ticker", "type", "isin", "currencyCode", "name", "shortName",
                "workingScheduleId", "minTradeQuantity", "maxOpenQuantity", "addedOn"
            ]
            with open(out_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                for inst in instruments:
                    row = {col: inst.get(col, '') for col in cols}
                    writer.writerow(row)
            print(f"   ✅ Saved: out/t212_instruments_{timestamp}.csv")
        except Exception as e:
            print(f"   ⚠️  Could not save CSV: {e}")
        
        # Excel
        try:
            import pandas as pd
            out_xlsx = os.path.join(out_dir, f"t212_instruments_{timestamp}.xlsx")
            cols = [
                "ticker", "type", "isin", "currencyCode", "name", "shortName",
                "workingScheduleId", "minTradeQuantity", "maxOpenQuantity", "addedOn"
            ]
            data = []
            for inst in instruments:
                row = {col: inst.get(col, '') for col in cols}
                data.append(row)
            df = pd.DataFrame(data)
            df.sort_values(["type", "ticker"], inplace=True)
            df.to_excel(out_xlsx, index=False, engine='openpyxl')
            print(f"   ✅ Saved: out/t212_instruments_{timestamp}.xlsx")
        except Exception as e:
            print(f"   ⚠️  Could not save Excel: {e}")
        
        print()
        print("=" * 70)
        print("✅ UPDATE COMPLETE")
        print("=" * 70)
        print()
        print(f"Total instruments: {len(instruments):,}")
        print()
        print("Files saved:")
        print(f"  - t212_all_instruments.json")
        print(f"  - brokers/t212_instruments.json")
        print(f"  - out/t212_instruments_{timestamp}.json")
        if os.path.exists(out_csv):
            print(f"  - out/t212_instruments_{timestamp}.csv")
        if os.path.exists(out_xlsx):
            print(f"  - out/t212_instruments_{timestamp}.xlsx")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

