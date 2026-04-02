from datetime import datetime, timezone
from typing import Any, Dict, List

from core.broker.t212_client import T212
from core.services.quote_fallback import (
    REQUIRED_REGIME_PRICE_SYMBOLS,
    ensure_regime_prices_or_raise,
)
from core.utils.io import write_json
from infra.state_paths import (
    CACHED_QUOTES,
    PORTFOLIO,
    PRICES,
    REGIME_QUOTES_FIXTURE,
)


def main(*, dry_run: bool = False) -> Dict[str, Any]:
    """Collect T212 prices and portfolio. Returns metadata for cycle audit (quote source)."""
    t212 = T212.from_env()
    t212.connect()
    try:
        prices = t212.get_market_prices()
        snap_live = {s: prices.get(s) for s in REQUIRED_REGIME_PRICE_SYMBOLS}
        fallback_chain: List = [CACHED_QUOTES, REGIME_QUOTES_FIXTURE]
        quote_data_source, fallback_paths = ensure_regime_prices_or_raise(
            prices=prices,
            snap_after_live=snap_live,
            dry_run=dry_run,
            fallback_paths=fallback_chain,
        )

        portfolio = t212.get_portfolio_summary()
        now = datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "ts": now,
            "prices": prices,
            "quote_data_source": quote_data_source,
        }
        if fallback_paths:
            payload["quote_fallback_paths"] = fallback_paths
        PRICES.parent.mkdir(parents=True, exist_ok=True)
        write_json(str(PRICES), payload)
        portfolio["ts"] = now
        portfolio["quote_data_source"] = quote_data_source
        write_json(str(PORTFOLIO), portfolio)
        return {
            "quote_data_source": quote_data_source,
            "quote_fallback_paths": fallback_paths,
        }
    finally:
        t212.disconnect()


if __name__ == "__main__":
    meta = main(dry_run=False)
    print(meta)
