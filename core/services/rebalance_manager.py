"""
Rebalance Manager - Checks for weight drift and triggers rebalancing.
Runs monthly to check if positions have drifted >5% from targets.
"""

from core.utils.io import read_json
from datetime import datetime, timezone
import subprocess
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.state_paths import (
    LAST_DRIFT_STATE,
    LAST_REGIME,
    PORTFOLIO,
    REGIME,
    TARGETS_FILE,
)

def load_policy():
    """Load policy configuration."""
    try:
        import yaml
        policy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core", "policy.yaml")
        if os.path.exists(policy_path):
            with open(policy_path, 'r') as f:
                return yaml.safe_load(f) or {}
    except:
        pass
    return {}

def _start_production_cycle() -> None:
    """Single official pipeline: collect → signals → allocate → trade list → execute."""
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "hedge-daily-cycle.service"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            print("✅ hedge-daily-cycle.service started (full production path)")
        else:
            print(f"⚠️  Failed to start hedge-daily-cycle.service: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout starting hedge-daily-cycle.service (may still be running)")
    except Exception as e:
        print(f"⚠️  Error starting hedge-daily-cycle.service: {e}")


def check_regime_change() -> bool:
    """Check if regime has changed since last check."""
    try:
        regime_data = read_json(str(REGIME))
        last_regime_file = str(LAST_REGIME)
        
        current_regime = regime_data.get("regime", "UNKNOWN")
        
        if os.path.exists(last_regime_file):
            last_regime_data = read_json(last_regime_file)
            last_regime = last_regime_data.get("regime", "UNKNOWN")
            
            if current_regime != last_regime:
                # Save current regime
                from core.utils.io import write_json
                write_json(last_regime_file, regime_data)
                return True
        
        # Save current regime if first time
        from core.utils.io import write_json
        write_json(last_regime_file, regime_data)
        return False
    except:
        return False

def main():
    """Check for drift and trigger rebalance if needed.
    
    Institutional-style rebalancing:
    - Core holdings (persistent): Only rebalance on large drift (>10%) or quarterly
    - Satellite holdings (tactical/EM/dividends): Rebalance on normal drift (>5%) or monthly
    - Individual stocks: Rebalance on normal drift (>5%) or monthly
    """
    try:
        policy = load_policy()
        drift_threshold = policy.get("rebalancing", {}).get("drift_threshold", 0.05)
        persistent_holdings = policy.get("rebalancing", {}).get("persistent_core_holdings", [])
        persistent_drift_threshold = policy.get("rebalancing", {}).get("persistent_drift_threshold", 0.10)
        
        # Check for regime change first
        regime_changed = check_regime_change()
        if regime_changed:
            print(f"🔄 Regime change detected at {datetime.now(timezone.utc).isoformat()}")
            print("   Starting full production cycle (hedge-daily-cycle.service)...")
            print("   (Regime change overrides persistent holdings logic)")
            _start_production_cycle()
            return
        
        # Load current portfolio and targets
        portfolio = read_json(str(PORTFOLIO))
        targets_data = read_json(str(TARGETS_FILE))
        
        if not portfolio or not targets_data:
            print("⚠️  Missing portfolio or targets data")
            return
        
        targets = targets_data.get("weights", {})
        nav = portfolio.get("nav", 0)
        
        if nav <= 0:
            print("⚠️  Invalid NAV")
            return
        
        # Calculate current weights
        current = {}
        
        # Add position weights
        for pos in portfolio.get("positions", []):
            symbol = pos.get("symbol", "")
            value = pos.get("value", 0)
            if symbol and value > 0:
                current[symbol] = value / nav
        
        # Add cash weight
        cash = portfolio.get("cash", 0)
        if cash > 0:
            current["CASH"] = cash / nav
        
        # Calculate drift for each target
        drift = {}
        for symbol, target_weight in targets.items():
            current_weight = current.get(symbol, 0)
            drift[symbol] = current_weight - target_weight
        
        # Load hysteresis bands from policy
        hysteresis = policy.get("rebalancing", {}).get("hysteresis", {})
        core_enter = hysteresis.get("core_enter", persistent_drift_threshold)
        core_exit = hysteresis.get("core_exit", persistent_drift_threshold * 0.7)
        sat_enter = hysteresis.get("sat_enter", drift_threshold)
        sat_exit = hysteresis.get("sat_exit", drift_threshold * 0.6)
        
        # Load last drift state (for hysteresis)
        last_drift_file = str(LAST_DRIFT_STATE)
        last_drift_state = {}
        try:
            if os.path.exists(last_drift_file):
                last_drift_state = read_json(last_drift_file)
        except:
            pass
        
        # Separate persistent core holdings from satellite holdings
        persistent_drifts = {}
        satellite_drifts = {}
        
        # Load per-asset overrides
        persistent_overrides = policy.get("rebalancing", {}).get("persistent_overrides", {})
        
        for symbol, drift_val in drift.items():
            abs_drift = abs(drift_val)
            
            if symbol in persistent_holdings:
                # Get asset-specific drift threshold (or use default)
                asset_drift_threshold = persistent_drift_threshold
                if symbol in persistent_overrides:
                    asset_drift_threshold = persistent_overrides[symbol].get("drift", persistent_drift_threshold)
                
                # Hysteresis: check if we're entering or exiting
                last_abs_drift = abs(last_drift_state.get(symbol, 0))
                was_rebalancing = last_abs_drift > asset_drift_threshold
                
                if was_rebalancing:
                    # Was rebalancing: exit if drift < exit threshold
                    if abs_drift > core_exit:
                        persistent_drifts[symbol] = drift_val
                else:
                    # Was not rebalancing: enter if drift > enter threshold
                    if abs_drift > core_enter:
                        persistent_drifts[symbol] = drift_val
            else:
                # Satellite holdings: use hysteresis
                last_abs_drift = abs(last_drift_state.get(symbol, 0))
                was_rebalancing = last_abs_drift > drift_threshold
                
                if was_rebalancing:
                    # Was rebalancing: exit if drift < exit threshold
                    if abs_drift > sat_exit:
                        satellite_drifts[symbol] = drift_val
                else:
                    # Was not rebalancing: enter if drift > enter threshold
                    if abs_drift > sat_enter:
                        satellite_drifts[symbol] = drift_val
        
        # Check if we need to rebalance
        needs_rebalance = False
        rebalance_reason = []
        
        if persistent_drifts:
            needs_rebalance = True
            rebalance_reason.append(f"Persistent core holdings drift >{persistent_drift_threshold*100:.0f}%")
        
        if satellite_drifts:
            needs_rebalance = True
            rebalance_reason.append(f"Satellite holdings drift >{drift_threshold*100:.0f}%")
        
        if needs_rebalance:
            print(f"🔄 Rebalance triggered at {datetime.now(timezone.utc).isoformat()}")
            print(f"   Reason: {', '.join(rebalance_reason)}")
            print()
            
            if persistent_drifts:
                print(f"   📌 Persistent Core Holdings (drift >{persistent_drift_threshold*100:.0f}%):")
                for symbol, drift_val in sorted(persistent_drifts.items(), key=lambda x: abs(x[1]), reverse=True):
                    current_w = current.get(symbol, 0) * 100
                    target_w = targets.get(symbol, 0) * 100
                    print(f"      - {symbol}: {current_w:.1f}% → {target_w:.1f}% (drift: {drift_val*100:+.1f}%)")
                print()
            
            if satellite_drifts:
                print(f"   🛰️  Satellite Holdings (drift >{drift_threshold*100:.0f}%):")
                for symbol, drift_val in sorted(satellite_drifts.items(), key=lambda x: abs(x[1]), reverse=True):
                    current_w = current.get(symbol, 0) * 100
                    target_w = targets.get(symbol, 0) * 100
                    print(f"      - {symbol}: {current_w:.1f}% → {target_w:.1f}% (drift: {drift_val*100:+.1f}%)")
                print()
            
            print("   Starting full production cycle (hedge-daily-cycle.service)...")
            _start_production_cycle()
        else:
            print(f"✅ No rebalance needed at {datetime.now(timezone.utc).isoformat()}")
            print(f"   All positions within thresholds:")
            print(f"   - Persistent core holdings: <{core_enter*100:.0f}% drift (enter), <{core_exit*100:.0f}% drift (exit)")
            print(f"   - Satellite holdings: <{sat_enter*100:.0f}% drift (enter), <{sat_exit*100:.0f}% drift (exit)")
        
        # Save current drift state for hysteresis
        try:
            from core.utils.io import write_json
            write_json(last_drift_file, drift)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error in rebalance manager: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

