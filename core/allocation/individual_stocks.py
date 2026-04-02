"""
Individual Stocks Allocator - Alpha Generation Sleeve
Decides when to use individual stocks vs ETFs, like hedge funds do.

Hedge Fund Logic:
- ETFs: For diversification, broad market exposure, defensive positioning
- Individual Stocks: For alpha generation, specific winners, high conviction
- Decision factors:
  - Market regime (expansion = more stocks, recession = more ETFs)
  - Confidence levels (high confidence = more stocks)
  - Performance attribution (stocks outperforming = increase allocation)
  - Risk management (volatility = reduce stocks)
"""

from typing import Dict
from core.utils.io import read_json

def get_weights(regime: str, confidence: float) -> Dict[str, float]:
    """
    Get weights for individual stocks sleeve.
    
    Hedge Fund Decision Logic:
    - EXPANSION + High Confidence: 30-40% in individual stocks (alpha generation)
    - EXPANSION + Low Confidence: 20-25% in individual stocks
    - RECOVERY: 25-30% in individual stocks
    - SLOWDOWN: 15-20% in individual stocks (defensive, quality names)
    - RECESSION: 10-15% in individual stocks (only highest quality)
    
    Args:
        regime: Market regime (SLOWDOWN, EXPANSION, RECESSION, RECOVERY)
        confidence: Confidence level (0.0-1.0)
    
    Returns:
        Dict of symbol -> weight (within this sleeve, sums to 1.0)
    """
    
    # Base allocation by regime (like hedge funds)
    if regime == "EXPANSION":
        # Expansion: High conviction on individual stocks
        # Focus on growth, tech, AI winners
        if confidence >= 0.6:
            # High confidence: Aggressive stock picking
            weights = {
                # AI/Tech Leaders (40% of sleeve)
                "NVDA": 0.08,   # NVIDIA (AI leader)
                "TSLA": 0.06,   # Tesla (EV/AI)
                "AAPL": 0.05,   # Apple
                "MSFT": 0.05,   # Microsoft
                "GOOGL": 0.04,  # Alphabet
                "META": 0.04,   # Meta
                "AMZN": 0.04,   # Amazon
                "AMD": 0.04,    # AMD
                # Finance (20% of sleeve)
                "JPM": 0.04,    # JPMorgan
                "BAC": 0.03,    # Bank of America
                "GS": 0.03,     # Goldman Sachs
                "V": 0.03,      # Visa
                "MA": 0.03,     # Mastercard
                # Healthcare (15% of sleeve)
                "UNH": 0.03,    # UnitedHealth
                "JNJ": 0.03,    # Johnson & Johnson
                "LLY": 0.03,    # Eli Lilly
                "TMO": 0.03,    # Thermo Fisher
                "ABT": 0.03,    # Abbott
                # Consumer (10% of sleeve)
                "WMT": 0.02,    # Walmart
                "HD": 0.02,     # Home Depot
                "COST": 0.02,   # Costco
                "NKE": 0.02,    # Nike
                "SBUX": 0.02,   # Starbucks
                # Industrial (8% of sleeve)
                "BA": 0.02,     # Boeing
                "CAT": 0.02,    # Caterpillar
                "RTX": 0.02,    # Raytheon
                "HON": 0.02,    # Honeywell
                # Energy (5% of sleeve)
                "XOM": 0.02,    # Exxon Mobil
                "CVX": 0.03,    # Chevron
                # Other (2% of sleeve)
                "VZ": 0.01,     # Verizon
                "NEE": 0.01,    # NextEra Energy
            }
        elif confidence >= 0.4:
            # Medium confidence: Balanced stock picking
            weights = {
                # AI/Tech Leaders (35% of sleeve)
                "NVDA": 0.07,
                "TSLA": 0.05,
                "AAPL": 0.04,
                "MSFT": 0.04,
                "GOOGL": 0.03,
                "META": 0.03,
                "AMZN": 0.03,
                "AMD": 0.03,
                "AVGO": 0.03,
                # Finance (25% of sleeve)
                "JPM": 0.05,
                "BAC": 0.04,
                "GS": 0.03,
                "V": 0.04,
                "MA": 0.04,
                "BLK": 0.03,
                "MS": 0.02,
                # Healthcare (20% of sleeve)
                "UNH": 0.04,
                "JNJ": 0.04,
                "PFE": 0.03,
                "ABT": 0.03,
                "TMO": 0.03,
                "LLY": 0.03,
                # Consumer (12% of sleeve)
                "WMT": 0.03,
                "HD": 0.03,
                "COST": 0.02,
                "NKE": 0.02,
                "SBUX": 0.02,
                # Industrial (5% of sleeve)
                "BA": 0.02,
                "CAT": 0.02,
                "RTX": 0.01,
                # Energy (3% of sleeve)
                "XOM": 0.02,
                "CVX": 0.01,
            }
        else:
            # Low confidence: Defensive stock picking
            weights = {
                # Tech (30% of sleeve) - only quality names
                "AAPL": 0.06,
                "MSFT": 0.06,
                "GOOGL": 0.05,
                "NVDA": 0.05,
                "AMZN": 0.04,
                "META": 0.04,
                # Finance (25% of sleeve) - quality banks
                "JPM": 0.06,
                "BAC": 0.05,
                "V": 0.05,
                "MA": 0.05,
                "GS": 0.04,
                # Healthcare (25% of sleeve) - defensive
                "UNH": 0.06,
                "JNJ": 0.06,
                "PFE": 0.05,
                "ABT": 0.04,
                "TMO": 0.04,
                # Consumer (15% of sleeve) - defensive
                "WMT": 0.05,
                "HD": 0.04,
                "COST": 0.03,
                "NKE": 0.03,
                # Industrial (5% of sleeve)
                "CAT": 0.03,
                "HON": 0.02,
            }
    
    elif regime == "RECOVERY":
        # Recovery: Moderate stock picking, focus on quality
        weights = {
            # Tech (35% of sleeve)
            "AAPL": 0.06,
            "MSFT": 0.06,
            "NVDA": 0.05,
            "GOOGL": 0.05,
            "AMZN": 0.04,
            "META": 0.04,
            "AMD": 0.03,
            "AVGO": 0.02,
            # Finance (25% of sleeve)
            "JPM": 0.06,
            "BAC": 0.05,
            "V": 0.05,
            "MA": 0.04,
            "GS": 0.03,
            "MS": 0.02,
            # Healthcare (20% of sleeve)
            "UNH": 0.05,
            "JNJ": 0.05,
            "LLY": 0.04,
            "TMO": 0.03,
            "ABT": 0.03,
            # Consumer (12% of sleeve)
            "WMT": 0.04,
            "HD": 0.04,
            "COST": 0.02,
            "NKE": 0.02,
            # Industrial (5% of sleeve)
            "BA": 0.02,
            "CAT": 0.02,
            "RTX": 0.01,
            # Energy (3% of sleeve)
            "XOM": 0.02,
            "CVX": 0.01,
        }
    
    elif regime == "SLOWDOWN":
        # Slowdown: Defensive stock picking, quality names only
        weights = {
            # Tech (25% of sleeve) - only mega caps
            "AAPL": 0.08,
            "MSFT": 0.08,
            "GOOGL": 0.05,
            "AMZN": 0.04,
            # Finance (30% of sleeve) - quality banks
            "JPM": 0.08,
            "BAC": 0.07,
            "V": 0.06,
            "MA": 0.05,
            "GS": 0.04,
            # Healthcare (30% of sleeve) - defensive
            "UNH": 0.08,
            "JNJ": 0.08,
            "PFE": 0.06,
            "ABT": 0.05,
            "TMO": 0.03,
            # Consumer (10% of sleeve) - defensive
            "WMT": 0.05,
            "HD": 0.03,
            "COST": 0.02,
            # Industrial (5% of sleeve) - only quality
            "CAT": 0.03,
            "HON": 0.02,
        }
    
    else:  # RECESSION
        # Recession: Minimal stock picking, only highest quality
        weights = {
            # Tech (20% of sleeve) - only mega caps
            "AAPL": 0.08,
            "MSFT": 0.08,
            "GOOGL": 0.04,
            # Finance (30% of sleeve) - quality banks
            "JPM": 0.10,
            "BAC": 0.08,
            "V": 0.07,
            "MA": 0.05,
            # Healthcare (35% of sleeve) - defensive
            "UNH": 0.12,
            "JNJ": 0.12,
            "PFE": 0.06,
            "ABT": 0.05,
            # Consumer (10% of sleeve) - defensive
            "WMT": 0.06,
            "HD": 0.04,
            # Industrial (5% of sleeve) - only quality
            "CAT": 0.05,
        }
    
    # Adjust for confidence: lower confidence = reduce risky stocks, increase defensive
    if confidence < 0.4:
        # Reduce tech/AI exposure, increase defensive (finance, healthcare, consumer)
        tech_reduction = 0.10
        tech_total = sum(w for sym, w in weights.items() if sym in ["NVDA", "TSLA", "AMD", "AVGO", "META"])
        if tech_total > 0:
            for sym in ["NVDA", "TSLA", "AMD", "AVGO", "META"]:
                if sym in weights:
                    weights[sym] = max(0, weights[sym] * (1 - tech_reduction))
            
            # Redistribute to defensive
            defensive_total = sum(w for sym, w in weights.items() if sym in ["JPM", "BAC", "UNH", "JNJ", "WMT", "HD"])
            if defensive_total > 0:
                for sym in ["JPM", "BAC", "UNH", "JNJ", "WMT", "HD"]:
                    if sym in weights:
                        weights[sym] = weights[sym] * (1 + tech_reduction * 0.5)
    
    # Normalize to sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        # Fallback: equal weight top 10 defensive names
        weights = {
            "AAPL": 0.10,
            "MSFT": 0.10,
            "JPM": 0.10,
            "BAC": 0.10,
            "UNH": 0.10,
            "JNJ": 0.10,
            "WMT": 0.10,
            "HD": 0.10,
            "V": 0.10,
            "MA": 0.10,
        }
        # Normalize fallback
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
    
    return weights

