"""
Check Portfolio Status - Verify current positions and pending orders
"""

from core.broker.t212_client import T212
from core.utils.io import read_json
from dotenv import load_dotenv
import os

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

# Initialize
t212 = T212.from_env()
t212.connect()

print("=" * 80)
print("📊 CURRENT PORTFOLIO STATUS")
print("=" * 80)
print()

# 1. Check current positions
print("📈 CURRENT POSITIONS:")
print("-" * 80)
positions = t212.get_positions()

if not positions:
    print("   No positions found")
else:
    total_value = 0
    for pos in positions:
        ticker = pos.get("symbol", "") or (pos.symbol if hasattr(pos, 'symbol') else "")
        qty = pos.get("qty", 0) or (pos.qty if hasattr(pos, 'qty') else 0)
        value = pos.get("market_value", 0) or (pos.market_value if hasattr(pos, 'market_value') else 0)
        name = pos.get("name", "") or (pos.name if hasattr(pos, 'name') else "")
        
        if value > 0:
            total_value += value
            print(f"   {ticker:<20} {qty:>10.3f} shares = £{value:>10.2f}")
            if name:
                print(f"   {'':<20} Name: {name}")
            
            # Check for problematic tickers
            if "XLPEL" in ticker.upper() or ("LPX" in ticker.upper() and "XLP" not in ticker.upper()):
                print(f"   {'':<20} ⚠️  WARNING: This is LPX Private Equity, NOT XLP Consumer Staples!")
            elif "SXLPL" in ticker.upper():
                print(f"   {'':<20} ✅ CORRECT: SPDR Consumer Staples")
            print()
    
    print(f"   Total positions value: £{total_value:.2f}")

print()

# 2. Check pending orders
print("⏳ PENDING ORDERS:")
print("-" * 80)
pending = t212.get_pending_orders()

if not pending:
    print("   No pending orders")
else:
    print(f"   Found {len(pending)} pending orders")
    print()
    
    # Check for XLP-related orders
    xlp_orders = []
    other_orders = []
    
    for order in pending:
        # Try to get ticker from various fields
        ticker = (order.get("symbol") or 
                 order.get("ticker") or 
                 order.get("instrument") or
                 (order.symbol if hasattr(order, 'symbol') else "") or
                 (order.ticker if hasattr(order, 'ticker') else "") or
                 "")
        
        side = (order.get("side") or 
               order.get("orderSide") or
               (order.side if hasattr(order, 'side') else "") or
               "")
        
        qty = (order.get("quantity") or 
              order.get("qty") or
              order.get("size") or
              (order.quantity if hasattr(order, 'quantity') else 0) or
              (order.qty if hasattr(order, 'qty') else 0) or
              0)
        
        status = (order.get("status") or 
                 order.get("orderStatus") or
                 (order.status if hasattr(order, 'status') else "") or
                 "UNKNOWN")
        
        # Determine side from quantity if not explicit
        if isinstance(qty, (int, float)):
            side_str = "BUY" if qty > 0 else "SELL"
        else:
            side_str = side.upper() if side else "UNKNOWN"
        
        order_info = {
            "ticker": ticker,
            "side": side_str,
            "qty": abs(float(qty)) if qty else 0,
            "status": status,
            "raw": order
        }
        
        # Check if XLP related
        if "XLP" in str(ticker).upper() or "LPX" in str(ticker).upper():
            xlp_orders.append(order_info)
        else:
            other_orders.append(order_info)
    
    # Show XLP orders first (most important)
    if xlp_orders:
        print("   ⚠️  XLP/LPX RELATED ORDERS:")
        for order in xlp_orders:
            ticker_str = order["ticker"] if order["ticker"] else "UNKNOWN_TICKER"
            print(f"   {order['side']:<4} {ticker_str:<20} {order['qty']:>10.3f} shares - Status: {order['status']}")
            
            # Check for problematic tickers
            if "XLPEL" in ticker_str.upper() or ("LPX" in ticker_str.upper() and "XLP" not in ticker_str.upper()):
                print(f"   {'':<25} ❌ WRONG: This is LPX Private Equity, NOT XLP Consumer Staples!")
            elif "SXLPL" in ticker_str.upper():
                print(f"   {'':<25} ✅ CORRECT: SPDR Consumer Staples")
            print()
    
    # Show all other orders
    if other_orders:
        print(f"   All pending orders ({len(other_orders)}):")
        for order in other_orders:
            ticker_str = order["ticker"] if order["ticker"] else "UNKNOWN_TICKER"
            print(f"   {order['side']:<4} {ticker_str:<20} {order['qty']:>10.3f} shares - Status: {order['status']}")
        print()

print()

# 3. Check cash
cash = t212.get_cash()
print(f"💰 Available cash: £{cash:.2f}")
print()

# 4. Verify against symbol_map
print("🔍 VERIFICATION AGAINST SYMBOL MAP:")
print("-" * 80)
try:
    symbol_map = read_json("brokers/symbol_map.json")
    
    for pos in positions:
        ticker = pos.get("symbol", "") or (pos.symbol if hasattr(pos, 'symbol') else "")
        value = pos.get("market_value", 0) or (pos.market_value if hasattr(pos, 'market_value') else 0)
        
        if value > 0:
            # Check if this ticker matches any symbol in symbol_map
            found_symbol = None
            for symbol, data in symbol_map.items():
                map_ticker = data.get("t212", "")
                alt_tickers = data.get("t212_alt", [])
                
                if ticker.upper() == map_ticker.upper() or ticker.upper() in [alt.upper() for alt in alt_tickers]:
                    found_symbol = symbol
                    break
            
            if found_symbol:
                print(f"   {ticker:<20} → {found_symbol:<8} ✅ Mapped correctly")
            else:
                print(f"   {ticker:<20} → {'?':<8} ⚠️  Not in symbol_map")
except Exception as e:
    print(f"   ⚠️  Could not load symbol_map: {e}")

print()
print("=" * 80)
print("✅ Status check complete!")
print("=" * 80)

t212.disconnect()

