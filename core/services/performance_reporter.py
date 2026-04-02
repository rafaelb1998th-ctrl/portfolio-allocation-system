"""
Performance Reporter - Calculates daily NAV, weekly reports, and sleeve attribution.
"""

from core.utils.io import read_json, write_json, append_jsonl
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import sys
import os
import math
import statistics

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.state_paths import (
    NAV_HISTORY,
    PORTFOLIO,
    REGIME,
    SLEEVE_ATTRIBUTION_HISTORY,
    SLEEVE_PERFORMANCE,
    TARGETS_FILE,
)

def calculate_nav(portfolio: Dict) -> float:
    """Calculate Net Asset Value from portfolio."""
    cash = portfolio.get("cash", 0)
    equity = portfolio.get("equity", 0)
    return cash + equity

def calculate_daily_return(current_nav: float, previous_nav: float) -> float:
    """Calculate daily return percentage."""
    if previous_nav <= 0:
        return 0.0
    return ((current_nav - previous_nav) / previous_nav) * 100

def calculate_sleeve_attribution(portfolio: Dict, targets: Dict) -> Dict[str, Dict]:
    """Calculate performance attribution by sleeve."""
    nav = calculate_nav(portfolio)
    if nav <= 0:
        return {}
    
    # Get sleeve metadata from targets
    meta = targets.get("meta", {})
    sleeves = meta.get("sleeves", {})
    
    attribution = {}
    
    for sleeve_name, sleeve_data in sleeves.items():
        sleeve_weights = sleeve_data.get("weights", {})
        sleeve_capital = sleeve_data.get("capital", 0)
        
        sleeve_value = 0
        sleeve_positions = []
        
        for symbol, weight in sleeve_weights.items():
            if symbol == "CASH":
                # Cash portion of this sleeve
                sleeve_value += portfolio.get("cash", 0) * weight
            else:
                # Find position value
                for pos in portfolio.get("positions", []):
                    if pos.get("symbol") == symbol:
                        pos_value = pos.get("value", 0)
                        sleeve_value += pos_value * (weight / sleeve_capital) if sleeve_capital > 0 else 0
                        sleeve_positions.append({
                            "symbol": symbol,
                            "value": pos_value * (weight / sleeve_capital) if sleeve_capital > 0 else 0,
                            "weight": weight
                        })
        
        attribution[sleeve_name] = {
            "capital_allocation": sleeve_capital,
            "value": sleeve_value,
            "weight_of_nav": sleeve_value / nav if nav > 0 else 0,
            "positions": sleeve_positions
        }
    
    return attribution

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from a list of returns.
    
    Args:
        returns: List of daily returns (as decimals, e.g., 0.01 = 1%)
        risk_free_rate: Risk-free rate (annualized, as decimal)
    
    Returns:
        Sharpe ratio (annualized)
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    # Calculate mean and std dev of returns
    mean_return = statistics.mean(returns)
    std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    if std_return == 0:
        return 0.0
    
    # Annualize (assuming daily returns, ~252 trading days)
    annualized_return = mean_return * 252
    annualized_std = std_return * math.sqrt(252)
    
    # Sharpe = (Return - RiskFree) / Volatility
    sharpe = (annualized_return - risk_free_rate) / annualized_std if annualized_std > 0 else 0.0
    
    return sharpe

def calculate_sleeve_performance(attribution_history: List[Dict]) -> Dict[str, Dict]:
    """Calculate sleeve performance metrics from historical attribution.
    
    Args:
        attribution_history: List of daily attribution snapshots
    
    Returns:
        Dict mapping sleeve name to performance metrics
    """
    if not attribution_history or len(attribution_history) < 2:
        return {}
    
    # Extract sleeve values over time
    sleeve_values = {}
    for snapshot in attribution_history:
        ts = snapshot.get("ts")
        sleeves = snapshot.get("sleeves", {})
        
        for sleeve_name, sleeve_data in sleeves.items():
            if sleeve_name not in sleeve_values:
                sleeve_values[sleeve_name] = []
            
            value = sleeve_data.get("value", 0)
            sleeve_values[sleeve_name].append({
                "ts": ts,
                "value": value
            })
    
    # Calculate returns and Sharpe ratios for each sleeve
    performance = {}
    
    for sleeve_name, values in sleeve_values.items():
        if len(values) < 2:
            continue
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(values)):
            prev_value = values[i-1]["value"]
            curr_value = values[i]["value"]
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
        
        if len(returns) < 2:
            continue
        
        # Calculate Sharpe ratios for different periods
        # 3 months ≈ 63 trading days, 6 months ≈ 126 trading days
        returns_3m = returns[-63:] if len(returns) >= 63 else returns
        returns_6m = returns[-126:] if len(returns) >= 126 else returns
        
        sharpe_3m = calculate_sharpe_ratio(returns_3m)
        sharpe_6m = calculate_sharpe_ratio(returns_6m)
        
        # Calculate total return
        if values[0]["value"] > 0:
            total_return = (values[-1]["value"] - values[0]["value"]) / values[0]["value"]
        else:
            total_return = 0.0
        
        performance[sleeve_name] = {
            "sharpe_3m": sharpe_3m,
            "sharpe_6m": sharpe_6m,
            "total_return": total_return,
            "num_days": len(returns)
        }
    
    return performance

def load_attribution_history() -> List[Dict]:
    """Load historical attribution data from JSONL file."""
    history_file = str(SLEEVE_ATTRIBUTION_HISTORY)
    history = []
    
    if os.path.exists(history_file):
        try:
            import json
            with open(history_file, 'r') as f:
                for line in f:
                    if line.strip():
                        history.append(json.loads(line.strip()))
        except:
            pass
    
    return history

def save_attribution_snapshot(attribution: Dict[str, Dict], nav: float):
    """Save current attribution snapshot to history."""
    snapshot = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "nav": nav,
        "sleeves": attribution
    }
    
    append_jsonl(str(SLEEVE_ATTRIBUTION_HISTORY), snapshot)
    
    # Keep only last 252 days (1 year of trading days)
    history_file = str(SLEEVE_ATTRIBUTION_HISTORY)
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                lines = f.readlines()
            
            # Keep last 252 snapshots
            if len(lines) > 252:
                with open(history_file, 'w') as f:
                    f.writelines(lines[-252:])
        except:
            pass

def generate_weekly_report() -> str:
    """Generate weekly performance report."""
    try:
        portfolio = read_json(str(PORTFOLIO))
        regime = read_json(str(REGIME))
        targets = read_json(str(TARGETS_FILE))
        
        nav = calculate_nav(portfolio)
        cash = portfolio.get("cash", 0)
        equity = portfolio.get("equity", 0)
        
        # Calculate attribution
        attribution = calculate_sleeve_attribution(portfolio, targets)
        
        # Build report
        report_lines = [
            "=" * 60,
            "HEDGE System - Weekly Performance Report",
            "=" * 60,
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "PORTFOLIO SUMMARY",
            "-" * 60,
            f"Net Asset Value (NAV):     £{nav:,.2f}",
            f"Cash:                      £{cash:,.2f} ({cash/nav*100:.1f}%)" if nav > 0 else f"Cash:                      £{cash:,.2f}",
            f"Equity:                    £{equity:,.2f} ({equity/nav*100:.1f}%)" if nav > 0 else f"Equity:                    £{equity:,.2f}",
            "",
            "REGIME",
            "-" * 60,
            f"Current Regime:            {regime.get('regime', 'UNKNOWN')}",
            f"Confidence:                 {regime.get('confidence', 0):.1%}",
            "",
            "TARGET ALLOCATION",
            "-" * 60,
            f"Strategy:                  {targets.get('notes', 'N/A')}",
            "",
            "POSITIONS",
            "-" * 60,
        ]
        
        # Add positions
        for pos in sorted(portfolio.get("positions", []), key=lambda x: x.get("value", 0), reverse=True):
            symbol = pos.get("symbol", "N/A")
            qty = pos.get("qty", 0)
            value = pos.get("value", 0)
            weight = (value / nav * 100) if nav > 0 else 0
            report_lines.append(f"  {symbol:20s} {qty:8.2f} shares  £{value:8.2f} ({weight:5.1f}%)")
        
        # Add sleeve attribution
        if attribution:
            report_lines.extend([
                "",
                "SLEEVE ATTRIBUTION",
                "-" * 60,
            ])
            
            for sleeve_name, sleeve_data in attribution.items():
                capital_pct = sleeve_data["capital_allocation"] * 100
                value = sleeve_data["value"]
                weight_pct = sleeve_data["weight_of_nav"] * 100
                report_lines.append(f"  {sleeve_name.upper():15s} Capital: {capital_pct:5.1f}%  Value: £{value:8.2f} ({weight_pct:5.1f}% of NAV)")
        
        report_lines.extend([
            "",
            "=" * 60,
        ])
        
        report = "\n".join(report_lines)
        return report
        
    except Exception as e:
        return f"Error generating report: {e}"

def main():
    """Main performance reporting process."""
    try:
        # Load current portfolio
        portfolio = read_json(str(PORTFOLIO))
        
        if not portfolio:
            print("⚠️  No portfolio data available")
            return
        
        # Calculate NAV
        nav = calculate_nav(portfolio)
        
        # Record daily NAV snapshot
        nav_snapshot = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "nav": nav,
            "cash": portfolio.get("cash", 0),
            "equity": portfolio.get("equity", 0),
            "num_positions": len(portfolio.get("positions", []))
        }
        
        # Append to daily NAV log
        append_jsonl(str(NAV_HISTORY), nav_snapshot)
        
        # Calculate sleeve attribution
        targets = read_json(str(TARGETS_FILE))
        attribution = calculate_sleeve_attribution(portfolio, targets)
        
        # Save attribution snapshot
        save_attribution_snapshot(attribution, nav)
        
        # Calculate sleeve performance metrics
        attribution_history = load_attribution_history()
        sleeve_performance = calculate_sleeve_performance(attribution_history)
        
        # Save sleeve performance data (for meta_allocator to use)
        performance_data = {}
        for sleeve_name, perf in sleeve_performance.items():
            # Map sleeve names to expected format
            if sleeve_name == "tactical":
                performance_data["tactical_sharpe_3m"] = perf["sharpe_3m"]
                performance_data["tactical_sharpe_6m"] = perf["sharpe_6m"]
            elif sleeve_name == "em":
                performance_data["em_sharpe_3m"] = perf["sharpe_3m"]
                performance_data["em_sharpe_6m"] = perf["sharpe_6m"]
            elif sleeve_name == "div":
                performance_data["div_sharpe_3m"] = perf["sharpe_3m"]
                performance_data["div_sharpe_6m"] = perf["sharpe_6m"]
        
        SLEEVE_PERFORMANCE.parent.mkdir(parents=True, exist_ok=True)
        write_json(str(SLEEVE_PERFORMANCE), performance_data)
        
        # Generate and print weekly report (if it's Monday or requested)
        today = datetime.now(timezone.utc)
        if today.weekday() == 0:  # Monday
            report = generate_weekly_report()
            print(report)
            
            # Save report to file
            report_file = f"out/weekly_report_{today.strftime('%Y%m%d')}.txt"
            os.makedirs("out", exist_ok=True)
            with open(report_file, "w") as f:
                f.write(report)
            print(f"\n📄 Report saved to {report_file}")
        else:
            # Daily summary
            print(f"📊 Daily NAV: £{nav:,.2f} | Cash: £{portfolio.get('cash', 0):,.2f} | Equity: £{portfolio.get('equity', 0):,.2f}")
        
    except Exception as e:
        print(f"❌ Error in performance reporter: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

