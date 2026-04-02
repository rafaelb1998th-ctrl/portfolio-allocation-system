# Public snapshot

Sanitized copy of a portfolio automation project: **Python logic and docs**, not personal data dumps.

**Omitted from git (by design):** `.env`, `state/`, `archive/`, `logs/`, `venv/`, backups, and **large broker JSON** (`t212_instruments.json`, full `symbol_map`, filtered instrument lists). The repo ships **minimal stubs** (`{}` / `[]`) so imports resolve; you add real files locally and keep them out of commits (see `brokers/README.md`).

**Before running locally:** copy `.env.template` to `.env` with your own keys. Never commit `.env`.
