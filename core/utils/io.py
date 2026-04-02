"""Atomic JSON read/write and JSONL append utilities."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def write_json(filepath: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically (write to .tmp then rename)."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    tmp_path = filepath.with_suffix(filepath.suffix + '.tmp')
    
    try:
        with open(tmp_path, 'w') as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(filepath)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise e


def read_json(filepath: str) -> Dict[str, Any]:
    """Read JSON file."""
    filepath = Path(filepath)
    if not filepath.exists():
        return {}
    
    with open(filepath, 'r') as f:
        return json.load(f)


def append_jsonl(filepath: str, data: Dict[str, Any]) -> None:
    """Append a JSON line to a JSONL file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'a') as f:
        f.write(json.dumps(data) + '\n')

