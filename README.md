# HEDGE

Institutional-style automated portfolio system using **Trading 212** as the execution and data source.

**Documentation:** see [docs/README.md](docs/README.md).

## Repository layout (root)

```
HEDGE/
├── app/           # Orchestration entrypoints (e.g. daily cycle)
├── core/          # Domain logic (broker, services, allocator, risk, monitoring)
├── infra/         # Paths, locks, shared plumbing
├── brokers/       # Symbol map, instrument dumps, filtered lists
├── state/         # Live machine state (JSON / JSONL)
├── services/      # systemd unit + timer files
├── scripts/       # Maintenance helpers (e.g. install_systemd.sh)
├── docs/          # Human-facing documentation
├── tests/
├── logs/
├── out/             # Symlink → archive/out (weekly reports)
├── backups/         # Symlink → archive/backups (nightly state snapshots)
├── archive/         # Canonical storage for backups, exports, large dumps (see archive/README.md)
├── .env.template  # Copy to `.env` — never commit secrets
└── README.md
```

Policy and universe files currently live under **`core/`** (`core/policy.yaml`, `core/universe/whitelist.yaml`); migrating them to top-level `config/` is a follow-up pass.

## Daily cycle (recommended)

End-to-end production run (collect → regime → allocate → trade list → execute):

```bash
cd /path/to/HEDGE
source venv/bin/activate
python -m app.run_daily_cycle --dry-run   # no orders
python -m app.run_daily_cycle
```

Structured mirrors of state are written under `state/raw/`, `state/signals/`, etc., while legacy flat `state/*.json` remains the source of truth for unmigrated modules.

## Environment

```bash
cp .env.template .env
# Edit .env: T212_API_KEY, T212_API_SECRET, T212_MODE=api
```

## systemd

From repo root:

```bash
./scripts/install_systemd.sh
```

**Pass 2:** the installer enables **`hedge-daily-cycle.timer`** as the only production trading schedule and disables the old split timers. Details: [docs/operations/production.md](docs/operations/production.md) and [services/README.md](services/README.md).

## State

- **Flat legacy:** `state/prices.json`, `portfolio.json`, `regime.json`, `targets.json`, `trade_list.json`, …
- **Ops audit:** `state/ops/cycle_audit.jsonl`

## Safety

- Atomic JSON writes (`core/utils/io.py`)
- Run lock: `state/ops/run.lock`
- Whitelist enforcement in the position checker

## Single-source rule

Broker integration is centered on `core/broker/t212_client.py`; keep execution data authority clear in docs as you evolve feeds.
