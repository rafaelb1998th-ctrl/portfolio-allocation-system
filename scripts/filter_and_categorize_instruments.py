#!/usr/bin/env python3
"""
Filter and categorize T212 instruments based on whitelist criteria.
Removes irrelevant instruments and divides them by type (ETFs, Stocks, Bonds, Treasury, etc.)
"""

import sys
import os
import json
import yaml  # pyright: ignore[reportMissingModuleSource]
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_whitelist():
    """Load whitelist configuration."""
    whitelist_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "core", "universe", "whitelist.yaml"
    )
    with open(whitelist_path, 'r') as f:
        return yaml.safe_load(f)

def get_issuer_from_name(name, short_name):
    """Extract issuer from instrument name."""
    name_upper = name.upper()
    short_upper = short_name.upper()
    
    # Check for approved issuers
    issuers_map = {
        'ISHARES': 'iShares',
        'VANGUARD': 'Vanguard',
        'SPDR': 'SPDR',
        'XTRACKERS': 'Xtrackers',
        'INVESCO': 'Invesco',
        'WISDOMTREE': 'WisdomTree',
    }
    
    for key, value in issuers_map.items():
        if key in name_upper or key in short_upper:
            return value
    
    return None

def get_domicile_from_isin(isin):
    """Extract domicile country from ISIN (first 2 characters after country code)."""
    if not isin or len(isin) < 2:
        return None
    
    # ISIN format: CCXXXXXXXXXX where CC is country code
    country_code = isin[:2]
    
    # Map country codes to countries
    country_map = {
        'IE': 'IE',  # Ireland
        'LU': 'LU',  # Luxembourg
        'GB': 'UK',  # United Kingdom (GB is the ISIN code for UK)
        'US': 'US',  # United States
        'CA': 'CA',  # Canada
        'SE': 'SE',  # Sweden
        'DE': 'DE',  # Germany
        'FR': 'FR',  # France
        'NL': 'NL',  # Netherlands
        'CH': 'CH',  # Switzerland
    }
    
    return country_map.get(country_code, country_code)

def is_ucits_compliant(domicile):
    """Check if domicile is UCITS-compliant."""
    ucits_domiciles = ['IE', 'LU', 'UK']
    return domicile in ucits_domiciles

def days_since_added(added_on_str):
    """Calculate days since instrument was added."""
    if not added_on_str:
        return 0
    
    try:
        # Parse date string (format: "2023-11-02T16:28:13.000+02:00")
        dt = datetime.fromisoformat(added_on_str.replace('+', '+').replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt
        return delta.days
    except:
        return 0

def categorize_instrument(inst):
    """Categorize instrument by type."""
    ticker = inst.get('ticker', '').upper()
    name = inst.get('name', '').upper()
    short_name = inst.get('shortName', '').upper()
    inst_type = inst.get('type', '').upper()
    
    # First, check the explicit type field from T212
    # This is the most reliable indicator
    if inst_type == 'STOCK':
        # Check for REIT first (more specific)
        if 'REIT' in name or 'REIT' in short_name:
            return 'REIT'
        # Otherwise, it's a regular stock
        return 'Stock'
    
    if inst_type == 'ETF':
        return 'ETF'
    
    # If type is not set, use heuristics
    # Check for REIT first (more specific)
    if 'REIT' in name or 'REIT' in short_name:
        return 'REIT'
    
    # Check for Treasury (government bonds)
    if any(x in name or x in short_name for x in ['TREASURY', 'GILT', 'GOVERNMENT BOND', 'GOVT']):
        return 'Treasury'
    
    # Check for bond/fixed income (but not treasury)
    if any(x in name or x in short_name for x in ['BOND', 'CORPORATE BOND', 'FIXED INCOME', 'CREDIT']):
        return 'Bond'
    
    # Check for commodity
    if any(x in name or x in short_name for x in ['GOLD', 'SILVER', 'OIL', 'COMMODITY', 'ETC']):
        return 'Commodity'
    
    # Check for ETF indicators in name (only if type wasn't set)
    if any(x in name or x in short_name for x in ['ETF', 'EXCHANGE TRADED FUND', 'ETP']):
        return 'ETF'
    
    # Note: _EQ suffix is used for both stocks and ETFs on T212, so we don't use it
    # Default to stock if we can't determine
    return 'Stock'

def filter_instrument(inst, whitelist):
    """Filter instrument based on whitelist criteria."""
    name = inst.get('name', '')
    short_name = inst.get('shortName', '')
    isin = inst.get('isin', '')
    currency = inst.get('currencyCode', '')
    added_on = inst.get('addedOn', '')
    
    # Get issuer
    issuer = get_issuer_from_name(name, short_name)
    
    # Get domicile
    domicile = get_domicile_from_isin(isin)
    
    # Categorize instrument
    inst_type = inst.get('type', '').upper()
    category = categorize_instrument(inst)
    
    # For ETFs, must have approved issuer and be UCITS-compliant
    if category == 'ETF' or inst_type == 'ETF':
        if not issuer:
            return False, "ETF without approved issuer"
        if issuer not in whitelist['issuers_allow']:
            return False, f"ETF issuer not approved: {issuer}"
        
        # Check UCITS compliance for ETFs
        if whitelist['rules']['ucits_only']:
            if not is_ucits_compliant(domicile):
                return False, f"ETF not UCITS-compliant (domicile: {domicile})"
    
    # For Bonds and Treasury, prefer approved issuers but not required
    # (Some bonds may be from other issuers but still relevant)
    if category in ['Bond', 'Treasury']:
        # Prefer approved issuers, but allow others if they meet other criteria
        pass
    
    # For Stocks, REITs, and Commodities, we're more lenient
    # They don't need approved issuers, but should meet other criteria
    
    # Check currency (prefer GBP or USD, but allow others)
    currency_prefer = whitelist['rules'].get('currency_prefer', [])
    # We'll keep all currencies but prefer GBP/USD
    
    # Check minimum history (apply to all instrument types)
    # For stocks, use a more lenient requirement (180 days) to include S&P 500
    # For ETFs and other instruments, use the stricter requirement (365 days)
    if category == 'Stock':
        min_history = 180  # More lenient for stocks to include S&P 500
    else:
        min_history = whitelist['rules'].get('min_history_days', 365)
    
    days = days_since_added(added_on)
    if days < min_history:
        return False, f"Insufficient history: {days} days < {min_history} days"
    
    # Additional filters for stocks: prefer major exchanges and liquid stocks
    if category == 'Stock':
        # For stocks, be more lenient - only filter out very illiquid ones
        max_open_qty = inst.get('maxOpenQuantity', 0)
        if max_open_qty and max_open_qty < 10:  # Very low threshold for stocks
            return False, f"Stock with very low maxOpenQuantity: {max_open_qty}"
        
        # Prefer USD stocks for S&P 500, but allow others
        # Currency filtering is already handled above
    
    return True, "Passed"

def main():
    print("=" * 80)
    print("FILTER AND CATEGORIZE T212 INSTRUMENTS")
    print("=" * 80)
    print()
    
    # Load whitelist
    print("📋 Loading whitelist configuration...")
    whitelist = load_whitelist()
    print("✅ Whitelist loaded")
    print()
    
    # Load instruments - try original file first, then fallback
    instruments_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "brokers", "t212_instruments.json"
    )
    
    # Fallback to root directory file if brokers file doesn't exist
    if not os.path.exists(instruments_file):
        instruments_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "t212_all_instruments.json"
        )
    
    print(f"📋 Loading instruments from {instruments_file}...")
    with open(instruments_file, 'r') as f:
        all_instruments = json.load(f)
    print(f"✅ Loaded {len(all_instruments):,} instruments")
    print()
    
    # Filter and categorize
    print("🔍 Filtering and categorizing instruments...")
    print()
    
    filtered_by_category = defaultdict(list)
    rejected = []
    
    for inst in all_instruments:
        # Categorize
        category = categorize_instrument(inst)
        
        # Filter
        passed, reason = filter_instrument(inst, whitelist)
        
        if passed:
            filtered_by_category[category].append(inst)
        else:
            rejected.append({
                'instrument': inst,
                'category': category,
                'reason': reason
            })
    
    # Print statistics
    print("=" * 80)
    print("FILTERING RESULTS")
    print("=" * 80)
    print()
    
    total_filtered = sum(len(instruments) for instruments in filtered_by_category.values())
    print(f"Total instruments: {len(all_instruments):,}")
    print(f"Filtered (kept): {total_filtered:,}")
    print(f"Rejected: {len(rejected):,}")
    print()
    
    print("FILTERED INSTRUMENTS BY CATEGORY:")
    print("-" * 80)
    for category in sorted(filtered_by_category.keys()):
        count = len(filtered_by_category[category])
        print(f"  {category:15} {count:6,} instruments")
    print()
    
    # Create output directory
    output_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "brokers" / "filtered_instruments"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save categorized instruments
    print("💾 Saving categorized instruments...")
    print()
    
    for category, instruments in filtered_by_category.items():
        filename = output_dir / f"{category.lower()}.json"
        with open(filename, 'w') as f:
            json.dump(instruments, f, indent=2)
        print(f"  ✅ {category}: {len(instruments):,} instruments → {filename}")
    
    # Save all filtered instruments in one file
    all_filtered = []
    for instruments in filtered_by_category.values():
        all_filtered.extend(instruments)
    
    all_filtered_file = output_dir / "all_filtered.json"
    with open(all_filtered_file, 'w') as f:
        json.dump(all_filtered, f, indent=2)
    print(f"  ✅ All filtered: {len(all_filtered):,} instruments → {all_filtered_file}")
    
    # Replace original file with filtered version
    original_file = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "t212_all_instruments.json"
    backup_file = original_file.with_suffix('.json.backup')
    
    # Create backup of original file
    if original_file.exists():
        import shutil
        shutil.copy2(original_file, backup_file)
        print(f"  ✅ Backup created: {backup_file}")
    
    # Replace original with filtered version
    with open(original_file, 'w') as f:
        json.dump(all_filtered, f, indent=2)
    print(f"  ✅ Original file updated: {original_file} (replaced with {len(all_filtered):,} filtered instruments)")
    
    # Save summary statistics
    summary = {
        'total_instruments': len(all_instruments),
        'filtered_count': total_filtered,
        'rejected_count': len(rejected),
        'by_category': {
            category: len(instruments) 
            for category, instruments in filtered_by_category.items()
        },
        'filter_date': datetime.now(timezone.utc).isoformat(),
        'whitelist_criteria': {
            'approved_issuers': whitelist['issuers_allow'],
            'ucits_only': whitelist['rules']['ucits_only'],
            'allowed_domiciles': whitelist['rules']['domiciles_allow'],
            'preferred_currencies': whitelist['rules']['currency_prefer'],
            'min_history_days': whitelist['rules']['min_history_days'],
        }
    }
    
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✅ Summary → {summary_file}")
    print()
    
    # Show sample of each category
    print("=" * 80)
    print("SAMPLE INSTRUMENTS BY CATEGORY")
    print("=" * 80)
    print()
    
    for category in sorted(filtered_by_category.keys()):
        instruments = filtered_by_category[category]
        print(f"{category} ({len(instruments):,} instruments):")
        print("-" * 80)
        
        # Show first 5
        for inst in instruments[:5]:
            ticker = inst.get('ticker', 'N/A')
            short_name = inst.get('shortName', 'N/A')
            name = inst.get('name', 'N/A')[:50]
            currency = inst.get('currencyCode', 'N/A')
            issuer = get_issuer_from_name(inst.get('name', ''), inst.get('shortName', ''))
            print(f"  {ticker:20} {short_name:10} {currency:5} {issuer or 'N/A':15} {name}")
        
        if len(instruments) > 5:
            print(f"  ... and {len(instruments) - 5} more")
        print()
    
    print("=" * 80)
    print("✅ DONE")
    print("=" * 80)

if __name__ == "__main__":
    main()

