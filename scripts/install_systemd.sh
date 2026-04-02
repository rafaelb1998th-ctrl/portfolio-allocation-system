#!/bin/bash
# Install HEDGE systemd units and enable the Pass 2 production model.
# Run: ./scripts/install_systemd.sh   (from repo clone on the target machine)

set -e
cd "$(dirname "$0")/.."
REPO="$(pwd)"

echo "=========================================="
echo "HEDGE systemd install (Pass 2 — single production path)"
echo "Repo: $REPO"
echo "=========================================="
echo ""

echo "1. Copy unit files (main services/ only — not services/deprecated/)..."
sudo cp "$REPO/services"/*.service /etc/systemd/system/
sudo cp "$REPO/services"/*.timer /etc/systemd/system/
echo "   ✅ Copied .service and .timer files"
echo ""

echo "2. daemon-reload..."
sudo systemctl daemon-reload
echo "   ✅ Reloaded"
echo ""

echo "3. Disable deprecated split pipeline + old deposit path (ignore errors if absent)..."
for u in hedge-data.timer hedge-regime.timer hedge-ai.timer hedge-trader.timer; do
  sudo systemctl disable --now "$u" 2>/dev/null || true
done
sudo systemctl disable --now hedge-deposit.path 2>/dev/null || true
sudo systemctl stop hedge-deposit.path 2>/dev/null || true
echo "   ✅ Deprecated timers/path turned off"
echo ""

echo "4. Enable daily cycle + support timers..."
# Strict live cycle: only when T212 /equity/quotes (or equivalent) works — see hedge-daily-cycle.service.
# By default on this repo we enable DRY-RUN so scheduled runs complete without orders or quote API dependency.
sudo systemctl disable --now hedge-daily-cycle.timer 2>/dev/null || true
sudo systemctl enable --now hedge-daily-cycle-dryrun.timer

sudo systemctl enable --now hedge-health.timer
sudo systemctl enable --now hedge-performance.timer
sudo systemctl enable --now hedge-reporter.timer
sudo systemctl enable --now hedge-rebalance.timer
sudo systemctl enable --now hedge-export-instruments.timer
echo "   ✅ hedge-daily-cycle + health + performance + reporter + rebalance + export"
echo ""

echo "=========================================="
echo "Done."
echo "=========================================="
echo ""
echo "Verify:"
echo "  systemctl list-timers 'hedge-*'"
echo "  systemctl status hedge-daily-cycle-dryrun.timer"
echo "  journalctl -u hedge-daily-cycle-dryrun.service -e"
echo "Strict live (only when quote API works): hedge-daily-cycle.timer / hedge-daily-cycle.service"
echo ""
echo "Docs: docs/operations/production.md"
echo "Deprecated split units still on disk for manual debugging; do not re-enable their timers."
echo ""
