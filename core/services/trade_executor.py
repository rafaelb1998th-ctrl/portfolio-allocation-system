"""Deprecated entrypoint: prefer ``python -m core.execution.trade_executor``."""

import sys

from core.execution.trade_executor import main

if __name__ == "__main__":
    sys.exit(main())
