"""Deprecated entrypoint: prefer ``python -m core.data.collector_t212``."""

from core.data.collector_t212 import main

if __name__ == "__main__":
    main(dry_run=False)
