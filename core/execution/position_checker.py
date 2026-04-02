"""
Position Checker - Analyzes current positions vs targets
Main goal: Check positions and determine what needs to be traded

1. Load targets (what we want)
2. Check current positions (REAL data from T212)
3. Check available cash
4. Calculate what to buy/sell
5. Output trade list for trade_executor.py
"""

from core.broker.t212_client import T212
from core.utils.io import read_json, write_json
import logging
import yaml
import os
from dotenv import load_dotenv

from infra.state_paths import TARGETS_FILE, TRADE_LIST

load_dotenv()
logger = logging.getLogger(__name__)


def main() -> None:
    t212 = T212.from_env()
    t212.connect()
    try:
        print("=" * 80)
        print("🔍 POSITION CHECKER - Analyzing positions vs targets")
        print("=" * 80)
        print()

        print("📋 Loading targets...")
        targets = read_json(str(TARGETS_FILE))
        target_weights = targets.get("weights", {})
        print(f"   ✅ Loaded {len(target_weights)} target allocations")
        print()

        print("📊 Checking current positions (REAL T212 API data)...")
        actual_positions = t212.get_positions()
        print(f"   Found {len(actual_positions)} positions from T212 API")

        current_positions = {}
        for pos in actual_positions:
            ticker = pos.get("symbol", "") or (pos.symbol if hasattr(pos, "symbol") else "")
            value = (
                pos.get("market_value", 0)
                or pos.get("marketValue", 0)
                or (pos.market_value if hasattr(pos, "market_value") else 0)
            )
            qty = pos.get("qty", 0) or (pos.qty if hasattr(pos, "qty") else 0)
            if value > 0:
                current_positions[ticker] = {"value": value, "qty": qty}
                print(f"   📍 {ticker}: {qty:.3f} shares = £{value:.2f}")

        if not current_positions:
            print("   ✅ No positions (portfolio is empty)")
        print()

        print("💰 Checking available cash...")
        cash = t212.get_cash()
        print(f"   Available cash: £{cash:.2f}")
        print()

        nav = cash + sum(p["value"] for p in current_positions.values())
        print(
            f"📊 Portfolio NAV: £{nav:.2f} (Cash: £{cash:.2f} + Positions: £{sum(p['value'] for p in current_positions.values()):.2f})"
        )
        print()

        whitelist = {}
        whitelisted_symbols = set()
        try:
            whitelist_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "core",
                "universe",
                "whitelist.yaml",
            )
            with open(whitelist_path, "r") as f:
                whitelist = yaml.safe_load(f)
                for bucket_name, symbols in whitelist.get("buckets", {}).items():
                    for symbol in symbols:
                        whitelisted_symbols.add(symbol)
            print(f"✅ Loaded whitelist: {len(whitelisted_symbols)} approved symbols")
        except Exception as e:
            logger.warning(f"Could not load whitelist: {e}")

        symbol_map = {}
        try:
            symbol_map = read_json("brokers/symbol_map.json")
        except Exception:
            pass

        instruments = []
        try:
            instruments = read_json("brokers/filtered_instruments/all_filtered.json")
        except Exception:
            pass

        print("🔗 Mapping positions to symbols...")
        symbol_to_position = {}

        for ticker, pos_data in current_positions.items():
            symbol = None

            for sym, sym_data in symbol_map.items():
                t212_t = sym_data.get("t212", "")
                alt_tickers = sym_data.get("t212_alt", [])
                if t212_t.upper() == ticker.upper() or ticker.upper() in [
                    t.upper() for t in alt_tickers
                ]:
                    symbol = sym
                    break

            if not symbol:
                for sym in whitelisted_symbols:
                    if sym.upper() in ticker.upper() or ticker.upper().startswith(sym.upper()):
                        symbol = sym
                        break

            if symbol:
                if symbol not in symbol_to_position:
                    symbol_to_position[symbol] = {
                        "ticker": ticker,
                        "value": pos_data["value"],
                        "qty": pos_data["qty"],
                    }
                    print(f"   ✅ {ticker} → {symbol} (£{pos_data['value']:.2f})")
                else:
                    symbol_to_position[symbol]["value"] += pos_data["value"]
                    symbol_to_position[symbol]["qty"] += pos_data["qty"]
                    print(
                        f"   ✅ {ticker} → {symbol} (combined: £{symbol_to_position[symbol]['value']:.2f})"
                    )
            else:
                print(f"   ⚠️  {ticker}: Could not map to symbol")

        print()

        print("📊 Calculating trades needed...")
        print()

        trades = []

        for symbol, target_weight in target_weights.items():
            if symbol == "CASH":
                continue

            if symbol not in whitelisted_symbols:
                continue

            t212_ticker = None

            if symbol == "XLP":
                for inst in instruments:
                    ticker = inst.get("ticker", "")
                    name = inst.get("name", "").upper()
                    if "SXLPL" in ticker.upper() and "CONSUMER STAPLES" in name:
                        t212_ticker = ticker
                        print(f"   ✅ XLP → {ticker} (SPDR Consumer Staples - CORRECT)")
                        break
                    elif "XLP" in ticker.upper() and "CONSUMER STAPLES" in name and "XLPEL" not in ticker.upper():
                        if not t212_ticker:
                            t212_ticker = ticker
                            print(f"   ✅ XLP → {ticker} (Consumer Staples)")

                if not t212_ticker and symbol in symbol_map:
                    map_ticker = symbol_map[symbol].get("t212")
                    if map_ticker and "XLPEL" not in map_ticker.upper():
                        t212_ticker = map_ticker

            elif symbol in symbol_map:
                t212_ticker = symbol_map[symbol].get("t212")
                if not t212_ticker:
                    alt_tickers = symbol_map[symbol].get("t212_alt", [])
                    if alt_tickers:
                        t212_ticker = alt_tickers[0]

            if not t212_ticker:
                t212_ticker = symbol
                if symbol == "XLP":
                    print(
                        f"   ⚠️  WARNING: XLP fallback to '{t212_ticker}' - may be wrong! Should be SXLPl_EQ"
                    )

            target_value = target_weight * nav
            current_value = symbol_to_position.get(symbol, {}).get("value", 0.0)
            allocation = target_value - current_value

            if abs(allocation) > 1.0:
                trades.append(
                    {
                        "symbol": symbol,
                        "t212_ticker": t212_ticker,
                        "target_weight": target_weight,
                        "target_value": target_value,
                        "current_value": current_value,
                        "allocation": allocation,
                    }
                )

        trades.sort(key=lambda x: x["allocation"])

        print(f"📋 Generated {len(trades)} trades:")
        print()
        print(f"{'Side':<6} {'Symbol':<8} {'Ticker':<20} {'Allocation':<15}")
        print("-" * 60)

        for trade in trades:
            side = "SELL" if trade["allocation"] < 0 else "BUY"
            print(
                f"{side:<6} {trade['symbol']:<8} {trade['t212_ticker']:<20} £{trade['allocation']:>12.2f}"
            )

        print()

        trade_list = {
            "ts": targets.get("ts"),
            "nav": nav,
            "cash": cash,
            "trades": trades,
        }

        TRADE_LIST.parent.mkdir(parents=True, exist_ok=True)
        write_json(str(TRADE_LIST), trade_list)
        print(f"✅ Saved trade list to {TRADE_LIST}")
        print(f"   {len([t for t in trades if t['allocation'] < 0])} SELL orders")
        print(f"   {len([t for t in trades if t['allocation'] > 0])} BUY orders")
        print()

        print("=" * 80)
        print("✅ Position check complete!")
        print("=" * 80)
    finally:
        t212.disconnect()


if __name__ == "__main__":
    main()
