"""
Tactical Short-Term Sleeve - Short-term momentum/mean reversion (days-weeks)
Exploits short-term trends and mean reversion in broad ETFs.
"""

from typing import Dict
from core.utils.io import read_json

def get_weights(regime: str, confidence: float) -> Dict[str, float]:
    """
    Get weights for tactical short-term sleeve.
    
    Args:
        regime: Market regime (SLOWDOWN, EXPANSION, RECESSION, RECOVERY)
        confidence: Confidence level (0.0-1.0)
    
    Returns:
        Dict of symbol -> weight (within this sleeve, sums to 1.0)
    """
    # Tactical sleeve: simple momentum/mean reversion
    # In risk-off regimes, hold more cash
    # In risk-on regimes, hold broad market ETFs
    
    if regime in ("SLOWDOWN", "RECESSION"):
        # Risk-off: hold cash and defensive ETFs
        weights = {
            "CASH": 0.40,
            "SPY": 0.30,  # Broad market (for mean reversion)
            "GLD": 0.20,  # Gold (safe haven)
            "XLU": 0.10,  # Utilities (defensive)
        }
    else:
        # Risk-on: hold broad market ETFs
        weights = {
            "CASH": 0.20,
            "SPY": 0.50,  # Broad market (momentum)
            "GLD": 0.15,  # Gold (diversification)
            "XLK": 0.15,  # Technology (momentum)
        }
    
    # Adjust for confidence: lower confidence = more cash
    if confidence < 0.35:
        shift = 0.15
        weights["CASH"] = min(1.0, weights.get("CASH", 0) + shift)
        # Reduce proportionally from non-cash
        total_non_cash = sum(w for sym, w in weights.items() if sym != "CASH")
        if total_non_cash > 0:
            for sym in weights:
                if sym != "CASH":
                    weights[sym] = weights[sym] * (1 - shift / total_non_cash)
    
    # Normalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        weights = {"CASH": 1.0}
    
    return weights

