"""
Core Macro Sleeve - Long-term regime following (3-12 months)
Follows economic regime with global ETFs.
"""

from typing import Dict

# Regime templates for core macro
# NOTE: Only uses whitelisted instruments from core_macro bucket:
# EQQQ, XLIS, SPY4, IDUP, VUKE, XLU, XLP, GLD, IGLT, DTLE, TRSY, XGLD
REGIME_TEMPLATES = {
    "SLOWDOWN": {
        "CASH": 0.15,
        "XLU": 0.25,  # Utilities (defensive) - whitelisted
        "XLP": 0.25,  # Consumer Staples (defensive) - whitelisted
        "GLD": 0.15,  # Gold (real assets) - whitelisted
        "IGLT": 0.05,  # UK Gilts (bonds) - whitelisted
        "DTLE": 0.05,  # US Treasury 20+yr (bonds - hedging) - whitelisted
        "XLIS": 0.10,  # S&P 500 (defensive equity) - whitelisted
    },
    "EXPANSION": {
        "CASH": 0.05,
        "XLU": 0.05,  # Utilities (defensive) - whitelisted
        "XLP": 0.10,  # Consumer Staples (defensive) - whitelisted
        "GLD": 0.05,  # Gold (real assets) - whitelisted
        "EQQQ": 0.30,  # Nasdaq 100 (growth) - whitelisted
        "SPY4": 0.25,  # S&P 400 Mid-Cap (cyclical) - whitelisted
        "IDUP": 0.15,  # Developed Markets (cyclical) - whitelisted
    },
    "RECESSION": {
        "CASH": 0.25,
        "XLU": 0.30,  # Utilities (defensive) - whitelisted
        "XLP": 0.25,  # Consumer Staples (defensive) - whitelisted
        "GLD": 0.10,  # Gold (real assets) - whitelisted
        "IGLT": 0.05,  # UK Gilts (bonds) - whitelisted
        "DTLE": 0.05,  # US Treasury 20+yr (bonds - hedging) - whitelisted
    },
    "RECOVERY": {
        "CASH": 0.10,
        "XLU": 0.10,  # Utilities (defensive) - whitelisted
        "XLP": 0.10,  # Consumer Staples (defensive) - whitelisted
        "GLD": 0.10,  # Gold (real assets) - whitelisted
        "EQQQ": 0.25,  # Nasdaq 100 (growth) - whitelisted
        "SPY4": 0.20,  # S&P 400 Mid-Cap (cyclical) - whitelisted
        "IDUP": 0.15,  # Developed Markets (cyclical) - whitelisted
    }
}

def apply_confidence_adjustment(weights: Dict[str, float], confidence: float) -> Dict[str, float]:
    """Adjust weights based on confidence (lower confidence = more cash/defensive)."""
    if confidence < 0.35:
        # Low confidence: shift to cash and defensives
        shift = 0.10
        current_cash = weights.get("CASH", 0)
        weights["CASH"] = current_cash + shift
        
        # Reduce cyclical exposure proportionally (using whitelisted instruments)
        cyclical_symbols = ["EQQQ", "SPY4", "IDUP"]  # Growth/cyclical from whitelist
        cyclical_total = sum(weights.get(sym, 0) for sym in cyclical_symbols)
        if cyclical_total > 0:
            reduction = min(shift / 2, cyclical_total)
            for sym in cyclical_symbols:
                if sym in weights and weights[sym] > 0:
                    weights[sym] = max(0, weights[sym] - (reduction * weights[sym] / cyclical_total))
        
        # Reduce cyclical exposure further if needed
        if cyclical_total == 0:
            # If no cyclical, reduce from other non-cash positions
            non_cash_total = sum(w for sym, w in weights.items() if sym != "CASH")
            if non_cash_total > 0:
                for sym in weights:
                    if sym != "CASH":
                        weights[sym] = max(0, weights[sym] - (shift / 2) * (weights[sym] / non_cash_total))
    return weights

def get_weights(regime: str, confidence: float) -> Dict[str, float]:
    """
    Get weights for core macro sleeve.
    
    Args:
        regime: Market regime (SLOWDOWN, EXPANSION, RECESSION, RECOVERY)
        confidence: Confidence level (0.0-1.0)
    
    Returns:
        Dict of symbol -> weight (within this sleeve, sums to 1.0)
    """
    # Get regime template
    template = REGIME_TEMPLATES.get(regime, REGIME_TEMPLATES["EXPANSION"])
    
    # Start with template
    weights = template.copy()
    
    # Apply confidence adjustment
    weights = apply_confidence_adjustment(weights, confidence)
    
    # Normalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        weights = {"CASH": 1.0}
    
    return weights

