"""
Multi-Strategy Allocator System
Each sleeve manages its own logic, horizon, and risk budget.
"""

from .core_macro import get_weights as core_macro_weights
from .tactical_shortterm import get_weights as tactical_weights
from .emerging_markets import get_weights as emerging_markets_weights
from .dividends_income import get_weights as dividends_income_weights

__all__ = [
    'core_macro_weights',
    'tactical_weights',
    'emerging_markets_weights',
    'dividends_income_weights',
]

