import sys
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)
_SOURCE_DIR = Path(__file__).resolve().parent.parent

RUNTIME_DIR = Path(sys.executable).resolve().parent if _FROZEN else _SOURCE_DIR
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS")).resolve() if _FROZEN else _SOURCE_DIR
DATA_DIR = RUNTIME_DIR / "data"
LOG_DIR = RUNTIME_DIR / "logs"
WEB_DIR = RESOURCE_DIR / "web"
CONFIG_FILE = DATA_DIR / "config.json"
LEGACY_CONFIG_FILE = RUNTIME_DIR / "config.yaml"
