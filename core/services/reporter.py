import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.utils.io import read_json
from infra.state_paths import PORTFOLIO, REGIME, TARGETS_FILE

# Simple text report (can be enhanced to HTML/PDF later)
portfolio = read_json(str(PORTFOLIO))
regime = read_json(str(REGIME))
targets = read_json(str(TARGETS_FILE))

report = f"""
HEDGE System Report
===================
Generated: {datetime.now(timezone.utc).isoformat()}

Portfolio:
  NAV: £{portfolio.get('nav', 0):.2f}
  Cash: £{portfolio.get('cash', 0):.2f}
  Equity: £{portfolio.get('equity', 0):.2f}
  
Regime:
  Current: {regime.get('regime', 'UNKNOWN')}
  Confidence: {regime.get('confidence', 0):.2f}
  
Targets:
  {targets.get('notes', 'No notes')}
"""

print(report)
