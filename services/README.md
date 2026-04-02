# systemd units (HEDGE)

## Official production path (Pass 2)

| Unit | Role |
|------|------|
| **`hedge-daily-cycle-dryrun.timer`** → **`hedge-daily-cycle-dryrun.service`** | **Default / safe:** `python -m app.run_daily_cycle --dry-run` — full pipeline, **no orders**, quote fallback allowed in collect. |
| **`hedge-daily-cycle.timer`** → **`hedge-daily-cycle.service`** | **Strict live:** `python -m app.run_daily_cycle` — no fallback; may place orders. Use only when `/equity/quotes` (or trusted pricing) works. |

Install enables **dry-run** by default; enable **one** daily-cycle timer at a time.

The only automated trading path for real money is the **strict** timer + service once validated.

## Support timers (non-trading loop)

| Timer | Role |
|------|------|
| `hedge-health.timer` | Health / backups (nightly) |
| `hedge-performance.timer` | Performance / NAV / sleeve metrics |
| `hedge-reporter.timer` | Weekly text report |
| `hedge-export-instruments.timer` | Optional instrument catalog export |
| `hedge-rebalance.timer` | Monthly drift check; if triggered, starts **`hedge-daily-cycle.service`** (strict live full cycle — ensure that is what you want, or trigger dry-run manually) |

## Deprecated (do not enable for production)

Split pipelines and unsafe entry points are **deprecated** — they can run allocator or executor **without** a fresh trade list or full gate sequence.

- `hedge-data.timer` / `hedge-regime.timer` / `hedge-ai.timer` / `hedge-trader.timer` (and their `.service` files)  
- Manual use only for debugging; see unit `Description=` lines.

**Removed from repo install set:** **`hedge-deposit.path`** (was: portfolio change → trader only → stale `trade_list`). See **`deprecated/hedge-deposit.path.example`** for history only — do not install without a safety review.

## Install

From repo root:

```bash
./scripts/install_systemd.sh
```

Uses **`.env`** in the repo root (`EnvironmentFile=` in oneshot services). Do not commit `.env`.

## Docs

[operations/production.md](../docs/operations/production.md) — dry-run, audit log, rollback notes.
