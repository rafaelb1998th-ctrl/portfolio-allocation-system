"""
AI Allocator - Portfolio CIO that converts signals + constraints into target weights.
Deterministic, auditable, T212-only with optional AI refinement.
"""

from core.utils.io import read_json, write_json
from datetime import datetime, timezone
from typing import Dict, Optional
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from infra.state_paths import PORTFOLIO, PRICES, REGIME, TARGETS_FILE

# Hard constraints
MAX_POSITION_WEIGHT = 0.10  # 10% max per position
MAX_SECTOR_WEIGHT = 0.25    # 25% max per sector
CASH_FLOOR = 0.10           # 10% cash floor
CASH_BUFFER = 0.01          # 1% unallocated buffer
WEIGHT_STEP = 0.005         # Round to 0.5% increments
AI_MAX_SHIFT = 0.05         # AI can shift max 5% per position

# Regime templates
REGIME_TEMPLATES = {
    "SLOWDOWN": {
        "CASH": 0.15,
        "XLU": 0.25,  # Utilities (defensive)
        "XLP": 0.25,  # Consumer Staples (defensive)
        "XLV": 0.15,  # Healthcare (defensive)
        "GLD": 0.15,  # Gold (real assets)
        "XLI": 0.05,  # Industrials (cyclical)
    },
    "EXPANSION": {
        "CASH": 0.05,
        "XLU": 0.05,  # Utilities (defensive)
        "XLP": 0.10,  # Consumer Staples (defensive)
        "XLV": 0.05,  # Healthcare (defensive)
        "GLD": 0.05,  # Gold (real assets)
        "XLI": 0.30,  # Industrials (cyclical)
        "XLY": 0.25,  # Consumer Discretionary (cyclical)
        "XLK": 0.15,  # Technology (cyclical)
    },
    "RECESSION": {
        "CASH": 0.25,
        "XLU": 0.30,  # Utilities (defensive)
        "XLP": 0.25,  # Consumer Staples (defensive)
        "XLV": 0.10,  # Healthcare (defensive)
        "GLD": 0.10,  # Gold (real assets)
    },
    "RECOVERY": {
        "CASH": 0.10,
        "XLU": 0.10,  # Utilities (defensive)
        "XLP": 0.10,  # Consumer Staples (defensive)
        "XLV": 0.10,  # Healthcare (defensive)
        "GLD": 0.10,  # Gold (real assets)
        "XLI": 0.25,  # Industrials (cyclical)
        "XLY": 0.20,  # Consumer Discretionary (cyclical)
        "XLK": 0.05,  # Technology (cyclical)
    }
}

# Sector mappings
SECTOR_MAP = {
    "XLU": "defensive",
    "XLP": "defensive",
    "XLV": "defensive",
    "XLI": "cyclical",
    "XLY": "cyclical",
    "XLK": "cyclical",
    "XLF": "cyclical",
    "GLD": "real_assets",
    "SGLN": "real_assets",
    "BND": "bonds",
    "TLT": "bonds",
    "VUAG": "core",
    "VUSA": "core",
    "SPY": "core",
    "VOO": "core",
}

def apply_confidence_adjustment(weights: Dict[str, float], confidence: float) -> Dict[str, float]:
    """Adjust weights based on confidence (lower confidence = more cash/defensive)."""
    if confidence < 0.35:
        # Low confidence: shift to cash and defensives
        shift = 0.10
        current_cash = weights.get("CASH", 0)
        weights["CASH"] = current_cash + shift
        
        # Reduce cyclical exposure proportionally
        cyclical_total = sum(weights.get(sym, 0) for sym in ["XLI", "XLY", "XLK", "XLF"])
        if cyclical_total > 0:
            reduction = min(shift / 2, cyclical_total)
            for sym in ["XLI", "XLY", "XLK", "XLF"]:
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

def enforce_position_limits(weights: Dict[str, float]) -> Dict[str, float]:
    """Enforce max position weight (10%)."""
    for sym, w in weights.items():
        if sym != "CASH" and w > MAX_POSITION_WEIGHT:
            excess = w - MAX_POSITION_WEIGHT
            weights[sym] = MAX_POSITION_WEIGHT
            weights["CASH"] = weights.get("CASH", 0) + excess
    return weights

def enforce_sector_limits(weights: Dict[str, float]) -> Dict[str, float]:
    """Enforce max sector weight (25%)."""
    sector_totals = {}
    for sym, w in weights.items():
        if sym != "CASH":
            sector = SECTOR_MAP.get(sym, "other")
            sector_totals[sector] = sector_totals.get(sector, 0) + w
    
    # Clip sectors that exceed limit
    for sector, total in sector_totals.items():
        if total > MAX_SECTOR_WEIGHT:
            excess = total - MAX_SECTOR_WEIGHT
            # Reduce proportionally
            for sym in weights:
                if sym != "CASH" and SECTOR_MAP.get(sym) == sector:
                    weights[sym] = weights[sym] * (MAX_SECTOR_WEIGHT / total)
            weights["CASH"] = weights.get("CASH", 0) + excess
    
    return weights

def enforce_cash_floor(weights: Dict[str, float]) -> Dict[str, float]:
    """Enforce cash floor (10%)."""
    cash = weights.get("CASH", 0)
    if cash < CASH_FLOOR:
        deficit = CASH_FLOOR - cash
        # Reduce proportionally from non-cash
        total_non_cash = sum(w for sym, w in weights.items() if sym != "CASH")
        if total_non_cash > 0:
            for sym in weights:
                if sym != "CASH":
                    weights[sym] = weights[sym] * (1 - deficit / total_non_cash)
        weights["CASH"] = CASH_FLOOR
    return weights

def round_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Round weights to 0.5% increments."""
    rounded = {}
    for sym, w in weights.items():
        rounded[sym] = round(w / WEIGHT_STEP) * WEIGHT_STEP
    return rounded

def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize weights to sum to 1.0 (including CASH)."""
    total = sum(weights.values())
    if total > 0:
        # Leave small buffer unallocated
        target_sum = 1.0 - CASH_BUFFER
        weights = {sym: w * (target_sum / total) for sym, w in weights.items()}
        weights["CASH"] = weights.get("CASH", 0) + CASH_BUFFER
    else:
        # Fallback: all cash
        weights = {"CASH": 1.0}
    return weights

def enforce_all_constraints(weights: Dict[str, float]) -> Dict[str, float]:
    """Apply all constraints in order."""
    weights = enforce_position_limits(weights)
    weights = enforce_sector_limits(weights)
    weights = enforce_cash_floor(weights)
    weights = round_weights(weights)
    weights = normalize_weights(weights)
    return weights

def call_ollama_llm(context: Dict, max_shift: float = AI_MAX_SHIFT) -> Optional[Dict[str, float]]:
    """Optional AI refinement via Ollama (bounded)."""
    try:
        import requests
        ollama_url = "http://localhost:11434/api/generate"
        
        prompt = f"""You are a portfolio allocator for T212 instruments. Output JSON only.

Context:
- Regime: {context.get('regime')}, confidence: {context.get('confidence', 0):.2f}
- Baseline weights: {json.dumps(context.get('baseline', {}), indent=2)}
- Current positions: {json.dumps(context.get('positions', {}), indent=2)}
- Constraints: max_pos=10%, max_sector=25%, cash_floor=10%

Goal: Small deviations (±{max_shift*100:.0f}%) to improve risk-adjusted return.

Output JSON:
{{"weights": {{"SYMBOL": 0.XX, ..., "CASH": 0.XX}}, "rationale": "one sentence"}}"""

        response = requests.post(
            ollama_url,
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "")
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if json_match:
                proposal = json.loads(json_match.group())
                return proposal.get("weights")
    except Exception:
        # AI failed - return None to use baseline
        pass
    return None

def merge_ai_proposal(baseline: Dict[str, float], proposal: Optional[Dict[str, float]], max_delta: float = AI_MAX_SHIFT) -> Dict[str, float]:
    """Merge AI proposal with baseline (bounded)."""
    if not proposal:
        return baseline
    
    merged = baseline.copy()
    for sym, w_prop in proposal.items():
        if sym in merged:
            w_base = merged[sym]
            delta = w_prop - w_base
            # Bound delta
            delta = max(-max_delta, min(max_delta, delta))
            merged[sym] = w_base + delta
    
    return merged

def main():
    """Main allocator process."""
    try:
        # Load inputs
        portfolio = read_json(str(PORTFOLIO))
        prices = read_json(str(PRICES))
        regime = read_json(str(REGIME))
        
        regime_label = regime.get("regime", "EXPANSION")
        confidence = regime.get("confidence", 0.5)
        
        # Get regime template
        template = REGIME_TEMPLATES.get(regime_label, REGIME_TEMPLATES["EXPANSION"])
        
        # Start with template
        weights = template.copy()
        
        # Apply confidence adjustment
        weights = apply_confidence_adjustment(weights, confidence)
        
        # Use template weights (executor will handle missing prices)
        # We don't filter here - let the executor skip symbols without prices
        filtered_weights = weights.copy()
        
        # Enforce constraints
        filtered_weights = enforce_all_constraints(filtered_weights)
        
        # Optional AI refinement (bounded)
        try:
            context = {
                "regime": regime_label,
                "confidence": confidence,
                "baseline": filtered_weights,
                "positions": {pos["symbol"]: pos.get("value", 0) for pos in portfolio.get("positions", [])}
            }
            ai_proposal = call_ollama_llm(context, max_shift=AI_MAX_SHIFT)
            if ai_proposal:
                filtered_weights = merge_ai_proposal(filtered_weights, ai_proposal, max_delta=AI_MAX_SHIFT)
                filtered_weights = enforce_all_constraints(filtered_weights)
                notes = f"AI-refined allocation under {regime_label} (conf={confidence:.2f})"
            else:
                notes = f"Rule-based allocation under {regime_label} (conf={confidence:.2f})"
        except Exception:
            # AI failed - use rule-based
            notes = f"Rule-based allocation under {regime_label} (conf={confidence:.2f})"
        
        # Final validation
        total = sum(filtered_weights.values())
        if abs(total - 1.0) > 0.01:
            # Renormalize if needed
            filtered_weights = normalize_weights(filtered_weights)
        
        # Write targets
        TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        write_json(str(TARGETS_FILE), {
            "ts": datetime.now(timezone.utc).isoformat(),
            "weights": filtered_weights,
            "notes": notes,
            "meta": {
                "regime": regime_label,
                "confidence": round(confidence, 2),
                "constraints": {
                    "max_pos": MAX_POSITION_WEIGHT,
                    "max_sector": MAX_SECTOR_WEIGHT,
                    "cash_floor": CASH_FLOOR
                },
                "source": "ai_allocator_v1"
            }
        })
        
    except Exception as e:
        # Fallback: try to keep last targets
        try:
            last_targets = read_json(str(TARGETS_FILE))
            if last_targets:
                # Keep last targets
                return
        except:
            pass
        
        # Final fallback: default allocation
        TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        write_json(str(TARGETS_FILE), {
            "ts": datetime.now(timezone.utc).isoformat(),
            "weights": {"CASH": 1.0},
            "notes": f"Fallback allocation (error: {str(e)[:50]})",
            "meta": {
                "regime": "UNKNOWN",
                "confidence": 0.0,
                "constraints": {},
                "source": "fallback"
            }
        })

if __name__ == "__main__":
    main()

