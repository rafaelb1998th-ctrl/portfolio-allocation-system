# Use only T212-tradable proxies: XLP/XLU vs XLY/XLI, GLD vs SPY, short-duration vs long-duration ETF if available.
# Enhanced with more sector signals
from core.utils.io import read_json, write_json
from datetime import datetime, timezone

from infra.state_paths import PRICES, REGIME


def main() -> None:
    prices_data = read_json(str(PRICES))
    p = prices_data.get("prices", {})

    def ratio(a: str, b: str) -> float:
        return (p.get(a, 0) / p.get(b, 1)) if p.get(b) else 0

    defensive_ratio = 0.5 * ratio("XLP", "XLY") + 0.5 * ratio("XLU", "XLI")
    healthcare_tech = ratio("XLV", "XLK") if "XLV" in p and "XLK" in p else 0
    hard_assets = ratio("GLD", "SPY") if "SPY" in p else 0
    financials_utilities = ratio("XLF", "XLU") if "XLF" in p and "XLU" in p else 0

    defensive_signal = (
        (defensive_ratio + healthcare_tech) / 2 if healthcare_tech > 0 else defensive_ratio
    )

    defensive_normalized = min(max((defensive_signal - 0.8) / 0.4, 0), 1)
    hard_assets_normalized = min(max(hard_assets / 0.5, 0), 1)
    conf = (
        0.4 * defensive_normalized
        + 0.3 * hard_assets_normalized
        + 0.3 * (1 - min(financials_utilities, 1))
    )

    regime = (
        "SLOWDOWN"
        if defensive_signal > 1.0 or hard_assets > 0.85 or defensive_normalized > 0.6
        else "EXPANSION"
    )

    REGIME.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        str(REGIME),
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "regime": regime,
            "confidence": round(conf, 2),
            "signals": {
                "defensive_over_cyclical": round(defensive_ratio, 2),
                "healthcare_tech": round(healthcare_tech, 2) if healthcare_tech > 0 else None,
                "gold_proxy": round(hard_assets, 2),
                "financials_utilities": round(financials_utilities, 2)
                if financials_utilities > 0
                else None,
            },
        },
    )


if __name__ == "__main__":
    main()
