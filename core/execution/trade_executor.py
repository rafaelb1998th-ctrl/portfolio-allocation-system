"""
Trade Executor - Simple and Clean
Main goal: Execute trades from trade_list.json

1. Load trade list (from position_checker.py)
2. Execute SELL orders first
3. Execute BUY orders (scaled to fit cash)
"""

from core.broker.t212_client import T212
from core.broker.price_feed import CompositePriceFeed
from core.utils.io import read_json, append_jsonl
from datetime import datetime, timezone
import logging
import time
import sys
from dotenv import load_dotenv

from infra.state_paths import EXECUTIONS_LOG, TRADE_LIST

load_dotenv()
logger = logging.getLogger(__name__)


def main() -> int:
    t212 = T212.from_env()
    t212.connect()
    price_feed = CompositePriceFeed(t212, prefer_yahoo=True)

    print("=" * 80)
    print("🚀 TRADE EXECUTOR - Executing trades from trade_list.json")
    print("=" * 80)
    print()

    EXECUTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)

    print("📋 Loading trade list...")
    try:
        trade_list = read_json(str(TRADE_LIST))
        trades = trade_list.get("trades", [])
        nav = trade_list.get("nav", 0)
        cash = trade_list.get("cash", 0)
        print(f"   ✅ Loaded {len(trades)} trades")
        print(f"   NAV: £{nav:.2f}, Cash: £{cash:.2f}")
    except Exception as e:
        print(f"   ❌ Error loading trade_list.json: {e}")
        print("   💡 Run position_checker.py first to generate trade list")
        t212.disconnect()
        return 1

    if not trades:
        print("   ✅ No trades needed - portfolio is aligned")
        t212.disconnect()
        return 0

    print("💰 Getting fresh cash...")
    cash = t212.get_cash()
    print(f"   Available cash: £{cash:.2f}")
    print()

    total_buys = sum(t["allocation"] for t in trades if t["allocation"] > 0)
    total_sells = sum(abs(t["allocation"]) for t in trades if t["allocation"] < 0)

    print("📊 Trade summary:")
    print(f"   Total BUYS: £{total_buys:.2f}")
    print(f"   Total SELLS: £{total_sells:.2f}")
    print(f"   Available cash: £{cash:.2f}")
    print()

    if total_buys > cash + total_sells:
        print("⚠️  Insufficient cash!")
        print(f"   Need: £{total_buys:.2f}")
        print(f"   Have: £{cash + total_sells:.2f}")
        print("   Scaling down BUY orders to fit available cash...")
        scale_factor = (cash + total_sells) / total_buys if total_buys > 0 else 0

        for trade in trades:
            if trade["allocation"] > 0:
                trade["allocation"] *= scale_factor
                trade["target_value"] = trade["current_value"] + trade["allocation"]

        total_buys = sum(t["allocation"] for t in trades if t["allocation"] > 0)
        print(f"   ✅ Scaled BUYS to: £{total_buys:.2f}")
        print()

    print("🚀 Executing trades...")
    print()

    print("📤 Executing SELL orders...")
    for trade in trades:
        if trade["allocation"] >= 0:
            continue

        symbol = trade["symbol"]
        t212_ticker = trade["t212_ticker"]
        allocation = abs(trade["allocation"])

        if trade.get("current_value", 0) <= 0:
            print(
                f"   ⏭️  {symbol}: No position to sell (current_value: £{trade.get('current_value', 0):.2f}) - skipping"
            )
            continue

        price = price_feed.get_price(symbol) or price_feed.get_price(t212_ticker)
        if not price or price <= 0:
            print(f"   ⚠️  {symbol}: No price available - skipping")
            continue

        qty = allocation / price
        qty = round(qty, 3)

        if qty <= 0:
            print(f"   ⏭️  {symbol}: Quantity too small - skipping")
            continue

        print(f"   📤 SELL {symbol} ({t212_ticker}): {qty:.3f} shares = £{qty * price:.2f}")
        resp = t212.place_market_order(symbol, -qty)

        if resp.get("status") == "accepted":
            print(f"      ✅ Order placed: {resp.get('message', 'Success')}")
        else:
            print(f"      ❌ Order rejected: {resp.get('message', 'Unknown error')}")

        append_jsonl(
            str(EXECUTIONS_LOG),
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": "sell",
                "qty": qty,
                "allocation": -allocation,
                "response": resp,
            },
        )

        time.sleep(0.5)

    print()

    if any(t["allocation"] < 0 for t in trades):
        print("⏳ Waiting 2 seconds for sell orders to process...")
        time.sleep(2)

        cash = t212.get_cash()
        print(f"💰 Updated cash after sells: £{cash:.2f}")
        print()

    print("📥 Executing BUY orders...")
    for trade in trades:
        if trade["allocation"] <= 0:
            continue

        symbol = trade["symbol"]
        t212_ticker = trade["t212_ticker"]
        allocation = trade["allocation"]

        if cash < 1.0:
            print("   ⏭️  {symbol}: Insufficient cash (<£1) - skipping remaining orders".format(symbol=symbol))
            break

        price = price_feed.get_price(symbol) or price_feed.get_price(t212_ticker)
        if not price or price <= 0:
            print(f"   ⚠️  {symbol}: No price available - skipping")
            continue

        if allocation > cash:
            allocation = cash * 0.95
            print(f"   🔄 Scaling {symbol} order to fit cash: £{allocation:.2f}")

        try:
            import yfinance as yf

            gbp_usd = yf.Ticker("GBPUSD=X")
            fx_rate = gbp_usd.info.get("regularMarketPrice") or 1.27
            if price > 50:
                price_gbp = price / fx_rate
            else:
                price_gbp = price
        except Exception:
            price_gbp = price / 1.27

        qty = round(allocation / price_gbp, 3)

        if qty < 0.001:
            print(f"   ⏭️  {symbol}: Quantity too small - skipping")
            continue

        print(f"   📥 BUY {symbol} ({t212_ticker}): {qty:.3f} shares = £{allocation:.2f}")
        resp = t212.place_market_order(symbol, qty)

        if resp.get("status") == "accepted":
            print(f"      ✅ Order placed: {resp.get('message', 'Success')}")
            cash -= allocation
            time.sleep(1)
            cash = t212.get_cash()
        else:
            print(f"      ❌ Order rejected: {resp.get('message', 'Unknown error')}")

        append_jsonl(
            str(EXECUTIONS_LOG),
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "side": "buy",
                "qty": qty,
                "allocation": allocation,
                "response": resp,
            },
        )

        time.sleep(0.5)

    print()
    print("✅ Trade execution complete!")
    print()

    pending = t212.get_pending_orders()
    if pending:
        print(f"📊 {len(pending)} orders still pending")
    else:
        print("✅ No pending orders")

    t212.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
