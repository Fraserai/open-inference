import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
COST_PER_TASK_DIR = ROOT / "inputs" / "cost_per_task"

TIMEZONE = "Australia/Sydney"


def load_env(path=ROOT / ".env"):
    """Read KEY=VALUE lines from .env into os.environ. Real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if value:
            os.environ.setdefault(key.strip(), value)


def load_json(name):
    return json.loads((CONFIG_DIR / name).read_text())
