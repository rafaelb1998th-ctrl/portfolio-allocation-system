# Deprecated systemd snippets

Do **not** copy these to `/etc/systemd/system/` unless you understand the risk.

See **`hedge-deposit.path.example`** for the old pattern (documented only).

## `hedge-deposit.path` (historical)

- Watched `state/portfolio.json` and started **`hedge-trader.service`** only.
- **Problem:** `trade_list.json` was not regenerated → execution could be wrong or stale.
- **Replacement:** rely on **`hedge-daily-cycle.service`**, or run `python -m app.run_daily_cycle` manually after deposits.

If you really want path-based automation later, point a new path unit at **`hedge-daily-cycle.service`** (not `hedge-trader`) and add debouncing / lock awareness to avoid storms.
