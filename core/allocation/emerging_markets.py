"""
Emerging Markets Sleeve - EM exposure (1-6 months)
Captures EM growth and yield as risk-on complement to core.
"""

from typing import Dict

def get_weights(regime: str, confidence: float) -> Dict[str, float]:
    """
    Get weights for emerging markets sleeve.
    
    Args:
        regime: Market regime (SLOWDOWN, EXPANSION, RECESSION, RECOVERY)
        confidence: Confidence level (0.0-1.0)
    
    Returns:
        Dict of symbol -> weight (within this sleeve, sums to 1.0)
    """
    # EM sleeve: only active in risk-on regimes
    if regime in ("EXPANSION", "RECOVERY"):
        # Risk-on: hold EM ETFs
        weights = {
            "CASH": 0.20,
            "EEM": 0.40,  # iShares Emerging Markets
            "VWO": 0.30,  # Vanguard FTSE Emerging Markets
            "EWZ": 0.10,  # Brazil (if available)
        }
        
        # Adjust for confidence
        if confidence < 0.5:
            # Lower confidence: reduce EM exposure
            shift = 0.10
            weights["CASH"] = min(1.0, weights.get("CASH", 0) + shift)
            # Reduce proportionally from EM
            total_em = sum(w for sym, w in weights.items() if sym != "CASH")
            if total_em > 0:
                for sym in weights:
                    if sym != "CASH":
                        weights[sym] = weights[sym] * (1 - shift / total_em)
    else:
        # Risk-off: hold cash
        weights = {"CASH": 1.0}
    
    # Normalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        weights = {"CASH": 1.0}
    
    return weights

