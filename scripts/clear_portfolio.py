#!/usr/bin/env python3
"""
Clear the current portfolio by selling all positions.
This will convert all holdings to cash so you can start fresh with the filtered instruments.
"""

import sys
import os
import time
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env if it exists
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
load_dotenv()

from core.broker.t212_client import T212
from core.utils.io import read_json, write_json

def main():
    print("=" * 80)
    print("CLEAR PORTFOLIO - SELL ALL POSITIONS")
    print("=" * 80)
    print()
    print("⚠️  WARNING: This will sell ALL current positions!")
    print("   Make sure you want to do this before proceeding.")
    print()
    
    # Connect to T212
    print("🔌 Connecting to Trading 212...")
    try:
        t212 = T212.from_env()
    except ValueError as e:
        # If API mode fails, try automation mode
        print(f"⚠️  API mode not available: {e}")
        print("🔄 Trying automation mode instead...")
        t212 = T212(mode="automation")
    
    if not t212.connect():
        print("❌ Failed to connect to Trading 212")
        print("   Make sure you have:")
        print("   - T212_API_KEY and T212_API_SECRET set (for API mode)")
        print("   - Or T212_PROFILE_DIR set (for automation mode)")
        return
    print("✅ Connected to Trading 212")
    print()
    
    # Get cash first
    print("💰 Getting cash balance...")
    cash = t212.get_cash()
    print(f"   Cash: £{cash:.2f}")
    print()
    
    # Get account summary (this is the source of truth)
    print("📊 Getting account summary...")
    account_summary = t212.get_account_summary()
    
    if account_summary:
        total_nav = account_summary.get('total', 0)
        invested = account_summary.get('invested', 0)
        print(f"✅ Account Summary:")
        print(f"   Total NAV: £{total_nav:.2f}")
        print(f"   Invested: £{invested:.2f}")
        print(f"   Cash: £{cash:.2f}")
        print()
    else:
        total_nav = cash
        invested = 0
        print("⚠️  Could not get account summary, using cash only")
        print()
    
    # Get current positions
    print("📊 Getting current positions...")
    positions = t212.get_positions()
    
    if not positions:
        print("✅ No positions found - portfolio is already clear!")
        return
    
    print(f"📋 Found {len(positions)} positions:")
    print()
    print(f"{'Symbol':<30} {'Quantity':<15} {'Currency':<10}")
    print("-" * 55)
    
    for pos in positions:
        symbol = pos.get('symbol', 'N/A')
        qty = pos.get('qty', 0)
        currency = pos.get('currency', 'N/A')
        
        print(f"{symbol:<30} {qty:<15.3f} {currency:<10}")
    
    print("-" * 55)
    print()
    print(f"💼 Total NAV (from account summary): £{total_nav:.2f}")
    print(f"📊 Equity (invested): £{invested:.2f}")
    print(f"💰 Cash: £{cash:.2f}")
    print()
    
    # Confirm before proceeding
    print("⚠️  Are you sure you want to sell ALL these positions?")
    print("   Type 'YES' to confirm, or anything else to cancel:")
    confirmation = input("> ").strip().upper()
    
    if confirmation != 'YES':
        print("❌ Cancelled - no positions were sold")
        return
    
    print()
    print("🔄 Selling all positions...")
    print()
    
    # Sell each position
    sold_count = 0
    failed_count = 0
    total_sold_value = 0
    
    for pos in positions:
        symbol = pos.get('symbol', '')
        # Use the actual owned quantity from the position data
        # The API returns the correct owned quantity
        qty = pos.get('qty', 0)
        currency = pos.get('currency', 'N/A')
        
        if qty <= 0:
            print(f"⚠️  Skipping {symbol}: invalid quantity ({qty})")
            continue
        
        # Get fresh position data to ensure we have the correct owned quantity
        # The position data should already have the correct qty, but let's be safe
        print(f"📤 Selling {symbol}: {qty:.3f} shares ({currency})...")
        
        try:
            # Place sell order - use the exact quantity we own
            result = t212.place_order(
                symbol=symbol,
                side="sell",
                qty=qty,  # Use the exact owned quantity
                order_type="market"
            )
            
            if result.get('status') in ['accepted', 'filled', 'pending']:
                order_id = result.get('id', 'N/A')
                filled_qty = result.get('filled_qty', qty)
                avg_price = result.get('avg_fill_price', 0)
                status = result.get('status', 'unknown')
                
                print(f"   ✅ Order {status}: {filled_qty:.3f} shares @ {avg_price:.2f} {currency}")
                print(f"   ℹ️  Order ID: {order_id}")
                
                sold_count += 1
            else:
                message = result.get('message', 'Unknown error')
                print(f"   ❌ Order rejected: {message}")
                
                # Try to extract actual owned quantity from error message
                # Error format: "Selling more equities than owned, owned: 0.026"
                if 'owned:' in message.lower():
                    try:
                        owned_qty_str = message.split('owned:')[1].strip().split()[0]
                        owned_qty = float(owned_qty_str)
                        if owned_qty > 0 and owned_qty < qty:
                            print(f"   🔄 Retrying with actual owned quantity: {owned_qty:.3f} shares...")
                            # Retry with actual owned quantity
                            retry_result = t212.place_order(
                                symbol=symbol,
                                side="sell",
                                qty=owned_qty,
                                order_type="market"
                            )
                            if retry_result.get('status') in ['accepted', 'filled', 'pending']:
                                print(f"   ✅ Retry successful: {owned_qty:.3f} shares")
                                sold_count += 1
                            else:
                                print(f"   ❌ Retry also failed: {retry_result.get('message', 'Unknown error')}")
                                failed_count += 1
                        else:
                            failed_count += 1
                    except:
                        failed_count += 1
                else:
                    failed_count += 1
            
            # Rate limiting: wait between orders
            if len(positions) > 1:
                print("   ⏳ Waiting 2 seconds before next order...")
                time.sleep(2)
            
        except Exception as e:
            print(f"   ❌ Error selling {symbol}: {e}")
            failed_count += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"✅ Successfully sold: {sold_count}/{len(positions)} positions")
    if failed_count > 0:
        print(f"❌ Failed to sell: {failed_count} positions")
    print()
    
    # Wait a bit for orders to settle
    if sold_count > 0:
        print("⏳ Waiting 5 seconds for orders to settle...")
        time.sleep(5)
        
        # Check final positions
        print()
        print("🔍 Checking remaining positions...")
        remaining_positions = t212.get_positions()
        
        if remaining_positions:
            print(f"⚠️  Still have {len(remaining_positions)} positions:")
            for pos in remaining_positions:
                symbol = pos.get('symbol', 'N/A')
                qty = pos.get('qty', 0)
                print(f"   - {symbol}: {qty:.3f} shares")
            print()
            print("   Some positions may still be settling. Check again in a few minutes.")
        else:
            print("✅ All positions cleared!")
    
    # Update portfolio.json
    print()
    print("💾 Updating portfolio.json...")
    portfolio_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "state", "portfolio.json"
    )
    
    # Get fresh cash and positions
    cash = t212.get_cash()
    final_positions = t212.get_positions()
    equity = sum(pos.get('market_value', 0) or pos.get('value', 0) for pos in final_positions)
    nav = cash + equity
    
    portfolio = {
        "cash": cash,
        "equity": equity,
        "positions": [
            {
                "symbol": pos.get('symbol', ''),
                "qty": pos.get('qty', 0),
                "avg_cost": pos.get('avg_price', 0),
                "value": pos.get('market_value', 0) or pos.get('value', 0)
            }
            for pos in final_positions
        ],
        "nav": nav,
        "ts": datetime.now(timezone.utc).isoformat()
    }
    
    write_json(portfolio_path, portfolio)
    print(f"✅ Updated portfolio.json")
    print(f"   Cash: £{cash:.2f}")
    print(f"   Equity: £{equity:.2f}")
    print(f"   NAV: £{nav:.2f}")
    print()
    
    print("=" * 80)
    print("✅ DONE")
    print("=" * 80)
    print()
    print("📝 Next steps:")
    print("   1. Wait a few minutes for all orders to settle")
    print("   2. Run the allocator to set new target allocations")
    print("   3. Run the trade executor to buy the new instruments")
    print()

if __name__ == "__main__":
    main()

