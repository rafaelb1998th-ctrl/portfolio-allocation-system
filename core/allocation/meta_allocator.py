"""
Meta Allocator - Institutional-grade allocation combining sleeves.
Implements: Fixed 60% Core Macro + Dynamic 40% satellite sleeves.
"""

from core.allocation import (
    core_macro_weights,
    tactical_weights,
    emerging_markets_weights,
    dividends_income_weights
)
from core.allocation.momentum_stock_sleeve import (
    build_momentum_individual_stocks_sleeve,
)
from core.utils.io import read_json, write_json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import yaml
import os
import math

from infra.state_paths import (
    PORTFOLIO,
    REGIME,
    SLEEVE_PERFORMANCE,
    TARGETS_FILE,
    PREV_SLEEVE_SCORES,
)

def load_policy() -> Dict:
    """Load policy configuration."""
    try:
        policy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policy.yaml")
        if os.path.exists(policy_path):
            with open(policy_path, 'r') as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"⚠️  Could not load policy.yaml: {e}")
    return {}

def load_whitelist() -> Dict:
    """Load whitelist configuration."""
    try:
        whitelist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "universe", "whitelist.yaml")
        if os.path.exists(whitelist_path):
            with open(whitelist_path, 'r') as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"⚠️  Could not load whitelist.yaml: {e}")
    return {}

def get_sleeve_scores(performance_data: Optional[Dict]) -> Dict[str, float]:
    """Calculate sleeve performance scores from attribution data.
    
    Returns scores for tactical, emerging, dividends sleeves.
    Uses Sharpe ratios with EWMA smoothing.
    """
    policy = load_policy()
    sleeve_config = policy.get("sleeves", {})
    sharpe_weights = sleeve_config.get("sharpe_weights", {"sharpe_3m": 0.6, "sharpe_6m": 0.4})
    score_floor = sleeve_config.get("score_floor", 0.01)
    score_half_life = sleeve_config.get("score_half_life_days", 10)
    
    # EWMA smoothing factor (alpha = 1 - exp(-ln(2) / half_life))
    import math
    alpha = 1 - math.exp(-math.log(2) / score_half_life) if score_half_life > 0 else 0.2
    
    # Load previous scores for EWMA smoothing
    prev_scores_file = str(PREV_SLEEVE_SCORES)
    prev_scores = {}
    try:
        if os.path.exists(prev_scores_file):
            prev_scores = read_json(prev_scores_file)
    except:
        pass
    
    # Default scores (if no performance data available)
    default_scores = {
        "tactical": 0.33,
        "em": 0.33,
        "div": 0.34
    }
    
    if not performance_data:
        return default_scores
    
    scores = {}
    
    # Try to get Sharpe ratios from performance data
    for sleeve in ["tactical", "em", "div"]:
        sharpe_3m = performance_data.get(f"{sleeve}_sharpe_3m", 0.0)
        sharpe_6m = performance_data.get(f"{sleeve}_sharpe_6m", 0.0)
        
        # Weighted Sharpe score
        raw_score = (sharpe_weights["sharpe_3m"] * sharpe_3m + 
                     sharpe_weights["sharpe_6m"] * sharpe_6m)
        
        # Apply score floor
        raw_score = max(score_floor, raw_score)
        
        # EWMA smoothing: blend with previous score
        prev_score = prev_scores.get(sleeve, raw_score)
        smoothed_score = alpha * raw_score + (1 - alpha) * prev_score
        
        # Apply floor again after smoothing
        scores[sleeve] = max(score_floor, smoothed_score)
    
    # Save current scores for next iteration
    try:
        write_json(prev_scores_file, scores)
    except:
        pass
    
    # If no scores calculated, use defaults
    if not scores:
        return default_scores
    
    return scores

def calculate_dynamic_sleeve_caps(
    non_core: float,
    scores: Dict[str, float],
    confidence: float,
    policy: Dict
) -> Dict[str, float]:
    """Calculate dynamic sleeve caps for non-core allocation.
    
    Args:
        non_core: Non-core allocation (typically 0.40)
        scores: Performance scores per sleeve
        confidence: Regime confidence
        policy: Policy configuration
    
    Returns:
        Dict mapping sleeve name to cap (% of NAV)
    """
    sleeve_config = policy.get("sleeves", {})
    confidence_threshold = policy.get("rebalancing", {}).get("confidence_threshold", 0.35)
    
    # Get min/max caps
    caps_minmax = {
        "tactical": (sleeve_config.get("tactical", {}).get("min", 0.05),
                    sleeve_config.get("tactical", {}).get("max", 0.20)),
        "em": (sleeve_config.get("emerging", {}).get("min", 0.05),
               sleeve_config.get("emerging", {}).get("max", 0.20)),
        "div": (sleeve_config.get("dividends", {}).get("min", 0.10),
                sleeve_config.get("dividends", {}).get("max", 0.25))
    }
    
    # Calculate proportional caps based on scores
    total_score = sum(scores.values())
    if total_score <= 0:
        # Equal weights if no scores
        caps = {k: non_core / 3.0 for k in scores.keys()}
    else:
        caps = {k: non_core * v / total_score for k, v in scores.items()}
    
    # Apply min/max clamps
    for sleeve in caps:
        min_cap, max_cap = caps_minmax.get(sleeve, (0.05, 0.25))
        caps[sleeve] = min(max(caps[sleeve], min_cap), max_cap)
    
    # Confidence gating: reduce tactical if confidence is low
    if confidence < confidence_threshold:
        cut = max(0, caps["tactical"] - 0.10)
        caps["tactical"] -= cut
        caps["div"] += cut  # Shift to dividends (defensive)
    
    # Renormalize to non_core
    total_caps = sum(caps.values())
    if total_caps > 0:
        scale = non_core / total_caps
        caps = {k: v * scale for k, v in caps.items()}
    
    return caps

def blend_saa_taa(
    taa_weights: Dict[str, float],
    saa_weights: Dict[str, float],
    blend_ratio: float
) -> Dict[str, float]:
    """Blend Tactical Asset Allocation with Strategic Asset Allocation.
    
    Args:
        taa_weights: Tactical weights from regime-based allocation
        saa_weights: Strategic baseline weights
        blend_ratio: TAA weight (e.g., 0.7 = 70% TAA, 30% SAA)
    
    Returns:
        Blended weights
    """
    all_symbols = set(taa_weights.keys()) | set(saa_weights.keys())
    blended = {}
    
    for symbol in all_symbols:
        taa_w = taa_weights.get(symbol, 0)
        saa_w = saa_weights.get(symbol, 0)
        blended[symbol] = blend_ratio * taa_w + (1 - blend_ratio) * saa_w
    
    return blended

def filter_by_whitelist(weights: Dict[str, float], whitelist: Dict, sleeve_name: str) -> Dict[str, float]:
    """Filter weights to only include whitelisted instruments for a sleeve."""
    buckets = whitelist.get("buckets", {})
    allowed_symbols = set(buckets.get(sleeve_name, []))
    
    if not allowed_symbols:
        return weights
    
    filtered = {k: v for k, v in weights.items() if k in allowed_symbols or k == "CASH"}
    return filtered

def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Normalize weights to sum to 1.0."""
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    else:
        weights = {"CASH": 1.0}
    return weights

def round_weights(weights: Dict[str, float], step: float = 0.005) -> Dict[str, float]:
    """Round weights to 0.5% increments."""
    rounded = {}
    for sym, w in weights.items():
        rounded[sym] = round(w / step) * step
    return rounded

def enforce_policy_limits(weights: Dict[str, float], policy: Dict) -> Dict[str, float]:
    """Enforce policy limits: max_pos, max_sector, cash_floor."""
    risk_config = policy.get("risk", {})
    max_pos = risk_config.get("max_pos", 0.10)
    cash_floor = risk_config.get("cash_floor", 0.05)
    
    # Clip positions to max_pos
    clipped = {}
    excess = 0.0
    
    for symbol, weight in weights.items():
        if symbol == "CASH":
            clipped[symbol] = weight
        else:
            if weight > max_pos:
                excess += weight - max_pos
                clipped[symbol] = max_pos
            else:
                clipped[symbol] = weight
    
    # Redistribute excess to cash
    if excess > 0:
        clipped["CASH"] = clipped.get("CASH", 0) + excess
    
    # Enforce cash floor
    cash = clipped.get("CASH", 0)
    if cash < cash_floor:
        # Need to reduce other positions to meet cash floor
        deficit = cash_floor - cash
        total_non_cash = sum(v for k, v in clipped.items() if k != "CASH")
        
        if total_non_cash > 0:
            # Reduce all non-cash positions proportionally
            scale = (total_non_cash - deficit) / total_non_cash
            for symbol in clipped:
                if symbol != "CASH":
                    clipped[symbol] *= scale
            clipped["CASH"] = cash_floor
    
    # Renormalize
    return normalize_weights(clipped)

def main():
    """Main meta-allocator process."""
    try:
        # Load inputs
        policy = load_policy()
        whitelist = load_whitelist()
        regime_data = read_json(str(REGIME))
        portfolio = read_json(str(PORTFOLIO))
        
        # Try to load performance data for sleeve scoring
        performance_data = None
        try:
            # Performance reporter should write this
            performance_file = str(SLEEVE_PERFORMANCE)
            if os.path.exists(performance_file):
                performance_data = read_json(performance_file)
        except:
            pass
        
        regime = regime_data.get("regime", "EXPANSION")
        confidence = regime_data.get("confidence", 0.5)
        
        # Get core_fixed from policy (default 0.60)
        core_fixed = policy.get("allocation", {}).get("core_fixed", 0.60)
        non_core = 1.0 - core_fixed  # 0.40
        
        # ============================================================
        # STEP 1: Core Macro Sleeve (60% fixed)
        # ============================================================
        
        # Get TAA weights from core_macro
        core_taa_weights = core_macro_weights(regime, confidence)
        
        # Get SAA weights from policy
        saa_weights = policy.get("saa_weights", {})
        taa_blend = policy.get("allocation", {}).get("taa_blend", 0.70)
        
        # Blend SAA + TAA within Core Macro
        core_weights = blend_saa_taa(core_taa_weights, saa_weights, taa_blend)
        
        # Filter by whitelist
        core_weights = filter_by_whitelist(core_weights, whitelist, "core_macro")
        
        # Normalize core weights to 100% of core allocation
        core_total = sum(core_weights.values())
        if core_total > 0:
            core_weights = {k: v / core_total for k, v in core_weights.items()}
        
        # Scale to core_fixed (60% of NAV)
        core_weights = {k: v * core_fixed for k, v in core_weights.items()}
        
        # ============================================================
        # STEP 2: Dynamic Sleeve Caps (40% non-core)
        # ============================================================
        
        # Get sleeve performance scores
        scores = get_sleeve_scores(performance_data)
        
        # Dynamic caps for tactical / EM / div (67% of non-core); stock sleeve uses stocks_cap separately
        etf_non_core = non_core * 0.67
        
        dynamic_caps = calculate_dynamic_sleeve_caps(etf_non_core, scores, confidence, policy)
        
        # Pilot: individual stock sleeve fixed at 10% NAV (momentum + holding manager)
        research = policy.get("research") or {}
        stocks_cap = float(research.get("stocks_cap_nav", 0.10))
        stocks_cap = min(max(stocks_cap, 0.0), 0.10)
        if stocks_cap <= 0:
            stocks_cap = 0.10
        
        # ============================================================
        # STEP 3: Get weights from each dynamic sleeve
        # ============================================================
        
        sleeve_stock_weights, stock_momentum_meta = build_momentum_individual_stocks_sleeve(
            portfolio=portfolio,
            regime=regime,
            confidence=confidence,
            policy=policy,
            whitelist=whitelist,
        )

        sleeves = {
            "tactical": tactical_weights(regime, confidence),
            "em": emerging_markets_weights(regime, confidence),
            "div": dividends_income_weights(regime, confidence),
            "individual_stocks": sleeve_stock_weights,
        }
        
        # Filter each sleeve by whitelist
        for sleeve_name in sleeves:
            if sleeve_name == "individual_stocks":
                # Individual stocks use their own bucket
                sleeves[sleeve_name] = filter_by_whitelist(
                    sleeves[sleeve_name], 
                    whitelist, 
                    "individual_stocks"
                )
            else:
                sleeves[sleeve_name] = filter_by_whitelist(
                    sleeves[sleeve_name], 
                    whitelist, 
                    sleeve_name
                )
            # Normalize within sleeve
            sleeve_total = sum(sleeves[sleeve_name].values())
            if sleeve_total > 0:
                sleeves[sleeve_name] = {k: v / sleeve_total for k, v in sleeves[sleeve_name].items()}
        
        # ============================================================
        # STEP 4: Merge all sleeves
        # ============================================================
        
        merged = core_weights.copy()
        
        # Add dynamic sleeves scaled by their caps
        for sleeve_name, sleeve_weights in sleeves.items():
            if sleeve_name == "individual_stocks":
                # Individual stocks use separate cap
                cap = stocks_cap
            else:
                cap = dynamic_caps.get(sleeve_name, 0)
            
            for symbol, weight in sleeve_weights.items():
                merged[symbol] = merged.get(symbol, 0) + cap * weight
        
        # ============================================================
        # STEP 5: Enforce policy limits
        # ============================================================
        
        merged = enforce_policy_limits(merged, policy)
        
        # ============================================================
        # STEP 6: Round and finalize
        # ============================================================
        
        merged = round_weights(merged)
        merged = normalize_weights(merged)  # Renormalize after rounding
        
        # ============================================================
        # STEP 7: Build metadata and write targets
        # ============================================================
        
        notes = f"{regime} (conf={confidence:.2f}) institutional: "
        notes += f"Core {core_fixed*100:.0f}% fixed, "
        notes += f"Individual Stocks {stocks_cap*100:.1f}%, "
        notes += f"Tactical {dynamic_caps.get('tactical', 0)*100:.1f}%, "
        notes += f"EM {dynamic_caps.get('em', 0)*100:.1f}%, "
        notes += f"Dividends {dynamic_caps.get('div', 0)*100:.1f}%"
        
        TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        write_json(str(TARGETS_FILE), {
            "ts": datetime.now(timezone.utc).isoformat(),
            "weights": merged,
            "notes": notes,
            "meta": {
                "regime": regime,
                "confidence": round(confidence, 2),
                "core_fixed": core_fixed,
                "dynamic_caps": {k: round(v, 3) for k, v in dynamic_caps.items()},
                "stocks_cap": round(stocks_cap, 3),
                "sleeve_scores": scores,
                "sleeves": {
                    "core": {
                        "capital": core_fixed,
                        "weights": {k: v / core_fixed for k, v in core_weights.items() if k != "CASH" or core_fixed > 0}
                    },
                    "individual_stocks": {
                        "capital": round(stocks_cap, 3),
                        "weights": sleeves["individual_stocks"],
                        "momentum": stock_momentum_meta,
                    },
                    "tactical": {
                        "capital": round(dynamic_caps.get("tactical", 0), 3),
                        "weights": sleeves["tactical"]
                    },
                    "em": {
                        "capital": round(dynamic_caps.get("em", 0), 3),
                        "weights": sleeves["em"]
                    },
                    "div": {
                        "capital": round(dynamic_caps.get("div", 0), 3),
                        "weights": sleeves["div"]
                    }
                },
                "source": "meta_allocator_v2_institutional"
            }
        })
        
        print(f"✅ Allocation complete: Core {core_fixed*100:.0f}% + Dynamic {non_core*100:.0f}%")
        print(f"   Individual Stocks: {stocks_cap*100:.1f}% (hedge fund style)")
        print(f"   ETF Sleeves: Tactical {dynamic_caps.get('tactical', 0)*100:.1f}%, "
              f"EM {dynamic_caps.get('em', 0)*100:.1f}%, "
              f"Dividends {dynamic_caps.get('div', 0)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Error in meta_allocator: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: try to keep last targets
        try:
            last_targets = read_json(str(TARGETS_FILE))
            if last_targets:
                print("⚠️  Keeping last targets due to error")
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
                "sleeves": {},
                "source": "fallback"
            }
        })

if __name__ == "__main__":
    main()
