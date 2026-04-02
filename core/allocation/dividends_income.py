"""
Dividends / Income Sleeve - Long-term income generation (6+ months)
Generates cash yield through dividend and infrastructure ETFs.
"""

from typing import Dict

def get_weights(regime: str, confidence: float) -> Dict[str, float]:
    """
    Get weights for dividends/income sleeve.
    
    Args:
        regime: Market regime (SLOWDOWN, EXPANSION, RECESSION, RECOVERY)
        confidence: Confidence level (0.0-1.0)
    
    Returns:
        Dict of symbol -> weight (within this sleeve, sums to 1.0)
    """
    # Base allocation: dividend and income ETFs
    base = {
        "CASH": 0.10,
        "VIG": 0.40,  # Vanguard Dividend Appreciation (if available)
        "XLU": 0.30,  # Utilities (high yield, defensive)
        "XLP": 0.20,  # Consumer Staples (dividend yield)
    }
    
    # Adjust for regime
    if regime == "RECESSION":
        # Recession: raise cash and utilities
        base["CASH"] += 0.05
        base["XLU"] += 0.05
        base["VIG"] = max(0, base["VIG"] - 0.10)
    elif regime == "SLOWDOWN":
        # Slowdown: slightly more defensive
        base["CASH"] += 0.03
        base["XLU"] += 0.02
        base["VIG"] = max(0, base["VIG"] - 0.05)
    
    # Adjust for confidence: lower confidence = more cash
    if confidence < 0.35:
        shift = 0.10
        base["CASH"] = min(1.0, base.get("CASH", 0) + shift)
        # Reduce proportionally from non-cash
        total_non_cash = sum(w for sym, w in base.items() if sym != "CASH")
        if total_non_cash > 0:
            for sym in base:
                if sym != "CASH":
                    base[sym] = base[sym] * (1 - shift / total_non_cash)
    
    # Normalize to sum to 1.0
    total = sum(base.values())
    if total > 0:
        weights = {k: v / total for k, v in base.items()}
    else:
        weights = {"CASH": 1.0}
    
    return weights

