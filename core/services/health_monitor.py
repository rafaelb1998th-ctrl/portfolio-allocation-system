"""
Health Monitor - Verifies services are alive, handles nightly backup of state and logs.
"""

import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.state_paths import HEALTH_STATUS

# Service names to check
SERVICES = [
    "hedge-data.timer",
    "hedge-regime.timer",
    "hedge-ai.timer",
    "hedge-trader.timer",
    "hedge-reporter.timer",
    "hedge-rebalance.timer",
    "hedge-deposit.path",
]

BACKUP_DIR = Path("backups")
STATE_DIR = Path("state")
LOGS_DIR = Path("logs")

def check_service_health(service_name: str) -> tuple[bool, str]:
    """Check if a systemd service/timer is active and enabled."""
    try:
        # Check if enabled
        result = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        enabled = result.returncode == 0 and result.stdout.strip() == "enabled"
        
        # Check if active (for timers, check if timer is active)
        if service_name.endswith(".timer"):
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            active = result.returncode == 0
        elif service_name.endswith(".path"):
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            active = result.returncode == 0
        else:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            active = result.returncode == 0
        
        status = "✅" if (enabled and active) else "⚠️"
        return enabled and active, status
    except Exception as e:
        return False, f"❌ ({str(e)[:30]})"

def backup_directory(source: Path, backup_root: Path, timestamp: str) -> bool:
    """Backup a directory to timestamped location."""
    try:
        if not source.exists():
            return False
        
        backup_path = backup_root / timestamp / source.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        if backup_path.exists():
            shutil.rmtree(backup_path)
        
        shutil.copytree(source, backup_path)
        return True
    except Exception as e:
        print(f"⚠️  Backup failed for {source}: {e}")
        return False

def backup_file(source: Path, backup_root: Path, timestamp: str) -> bool:
    """Backup a file to timestamped location."""
    try:
        if not source.exists():
            return False
        
        backup_path = backup_root / timestamp / source.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source, backup_path)
        return True
    except Exception as e:
        print(f"⚠️  Backup failed for {source}: {e}")
        return False

def perform_backup():
    """Perform nightly backup of state and logs."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_root = BACKUP_DIR / "nightly"
    
    print(f"💾 Starting backup at {datetime.now(timezone.utc).isoformat()}")
    
    # Backup state directory
    if STATE_DIR.exists():
        if backup_directory(STATE_DIR, backup_root, timestamp):
            print(f"✅ Backed up {STATE_DIR} to {backup_root / timestamp / STATE_DIR.name}")
        else:
            print(f"⚠️  Failed to backup {STATE_DIR}")
    
    # Backup logs directory
    if LOGS_DIR.exists():
        if backup_directory(LOGS_DIR, backup_root, timestamp):
            print(f"✅ Backed up {LOGS_DIR} to {backup_root / timestamp / LOGS_DIR.name}")
        else:
            print(f"⚠️  Failed to backup {LOGS_DIR}")
    
    # Clean up old backups (keep last 7 days)
    try:
        backup_dirs = sorted([d for d in (backup_root).iterdir() if d.is_dir()], reverse=True)
        if len(backup_dirs) > 7:
            for old_backup in backup_dirs[7:]:
                shutil.rmtree(old_backup)
                print(f"🗑️  Removed old backup: {old_backup.name}")
    except Exception as e:
        print(f"⚠️  Failed to clean old backups: {e}")

def main():
    """Main health monitoring process."""
    try:
        print("🏥 HEDGE Health Monitor")
        print("=" * 60)
        print(f"Time: {datetime.now(timezone.utc).isoformat()}")
        print()
        
        # Check service health
        print("SERVICE STATUS")
        print("-" * 60)
        all_healthy = True
        
        for service in SERVICES:
            healthy, status = check_service_health(service)
            if not healthy:
                all_healthy = False
            print(f"{status} {service}")
        
        print()
        
        # Perform backup
        print("BACKUP STATUS")
        print("-" * 60)
        perform_backup()
        
        # Overall health status
        print()
        print("=" * 60)
        if all_healthy:
            print("✅ All systems operational")
        else:
            print("⚠️  Some services need attention")
        
        # Write health status to file
        health_status = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "all_healthy": all_healthy,
            "services": {
                service: check_service_health(service)[0] for service in SERVICES
            }
        }
        
        health_file = HEALTH_STATUS
        health_file.parent.mkdir(parents=True, exist_ok=True)
        with open(health_file, "w") as f:
            json.dump(health_status, f, indent=2)
        
    except Exception as e:
        print(f"❌ Error in health monitor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

