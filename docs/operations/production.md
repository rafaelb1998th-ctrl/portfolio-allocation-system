# Production operations (Pass 2)

## Official execution path

Exactly **one** automated trading pipeline should be active:

```text
hedge-daily-cycle.timer
  → hedge-daily-cycle.service
  → python -m app.run_daily_cycle
      → core.data.collector_t212 → state/raw/{prices,portfolio}.json
      → validate raw
      → core.signals.regime_from_market → state/signals/regime.json
      → core.allocation.meta_allocator → state/targets/targets.json
      → target sum gate + core.risk.policy_engine (max_pos, etc.)
      → core.execution.position_checker → state/trades/trade_list.json
      → core.risk.pretrade_checks
      → core.execution.trade_executor → state/trades/executions.log.jsonl (unless --dry-run)
      → audit (state/ops/cycle_audit.jsonl)
```

Legacy flat files under `state/*.json` are no longer the write targets for the daily cycle; use nested paths above.

Anything that runs **allocator** or **executor** alone is **deprecated** for production (see `services/README.md`).

### Systemd: production vs dry-run (two timers)

Use **exactly one** daily-cycle timer:

| Timer | Service | Use |
|-------|---------|-----|
| `hedge-daily-cycle.timer` | `hedge-daily-cycle.service` | **Strict live** — real quotes required; may place orders. |
| `hedge-daily-cycle-dryrun.timer` | `hedge-daily-cycle-dryrun.service` | **Safe** — `app.run_daily_cycle --dry-run`; no orders; quote fallback allowed in collect. |

`./scripts/install_systemd.sh` enables **`hedge-daily-cycle-dryrun.timer`** and leaves the strict timer **disabled** so hosts without `/equity/quotes` do not fail every schedule.

Switch to strict live when validated:

```bash
sudo systemctl disable --now hedge-daily-cycle-dryrun.timer
sudo systemctl enable --now hedge-daily-cycle.timer
```

## Commands

From repo root, with `venv` and `.env` configured:

```bash
# Safe: builds targets + trade list, no orders
python -m app.run_daily_cycle --dry-run

# Live: full cycle including broker orders
python -m app.run_daily_cycle
```

Environment:

- `HEDGE_FRESHNESS_MINUTES` — max age for mirrored raw `prices` / `portfolio` (default 180).
- `HEDGE_ALLOW_CACHED_QUOTES=1` — **non-production only**: if live `/equity/quotes` fails, fill missing regime symbols from `state/raw/cached_quotes.json`, then from committed `tests/fixtures/regime_quotes.json`. Live systemd cycles should **not** set this.

## Quote data source (live vs fallback)

`state/raw/prices.json` includes `quote_data_source`: `live` (all regime symbols from the broker), `cached` (none from quotes; filled from files), or `mixed` (some live, some file). When files are used, `quote_fallback_paths` lists which JSON was read.

- **Production** (`python -m app.run_daily_cycle` without `--dry-run`, without `HEDGE_ALLOW_CACHED_QUOTES`): regime symbols must come from the API; the cycle fails fast if quotes are missing.
- **Dry-run** (`--dry-run`): after attempting live quotes, missing regime symbols may be filled from `state/raw/cached_quotes.json` (if present), then the fixture. `cycle_audit.jsonl` records the source.
- **Sandbox / restricted keys**: set `HEDGE_ALLOW_CACHED_QUOTES=1` so the same file chain applies without `--dry-run` — use only when you explicitly accept non-live prices.

Template for a local cache copy: `state/raw/cached_quotes.example.json` → save as `state/raw/cached_quotes.json` (gitignored).

## Audit and locks

| Artifact | Purpose |
|----------|---------|
| `state/ops/cycle_audit.jsonl` | Append-only JSON lines per cycle / stage |
| `state/ops/run.lock` | Prevents overlapping cycles (`FileLock`) |

If a run crashes, a stale lock may remain; confirm no `run_daily_cycle` process is running, then remove `state/ops/run.lock` only when safe.

## systemd

Install or refresh units:

```bash
./scripts/install_systemd.sh
```

After install:

- **Enabled:** `hedge-daily-cycle`, `hedge-health`, `hedge-performance`, `hedge-reporter`, `hedge-rebalance`, `hedge-export-instruments`
- **Disabled:** `hedge-data`, `hedge-regime`, `hedge-ai`, `hedge-trader` timers; legacy `hedge-deposit.path`

**Monthly rebalance:** `hedge-rebalance.service` runs `rebalance_manager`. On drift or regime change it runs `sudo systemctl start hedge-daily-cycle.service`. The `teckz` user needs **passwordless sudo for that command** (or equivalent) for unattended runs — same operational requirement as the previous `hedge-ai` / `hedge-trader` triggers.

## Rollback / recovery

1. Inspect last audit lines: `tail -50 state/ops/cycle_audit.jsonl`
2. Inspect journal: `journalctl -u hedge-daily-cycle.service -e`
3. Fix state or config, then re-run `--dry-run` before a live run.

## Deprecated (manual debug only)

- `systemctl start hedge-data.service` / `hedge-regime` / `hedge-ai` / `hedge-trader` — split steps; easy to leave `trade_list.json` stale if you only run trader.
- `services/deprecated/` — historical `hedge-deposit.path` pattern (trader-only on portfolio change).

## Next (Pass 3)

Move Python modules into `core/data`, `core/signals`, `core/execution`, etc., and eventually drop `out/` / `backups/` symlinks in favor of canonical paths in code.
