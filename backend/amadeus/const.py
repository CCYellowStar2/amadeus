from pathlib import Path
import os


ASSET_ID = os.environ.get("CH_CODE", "aoi")
SEND_PORT = os.environ.get("SEND_PORT", 3000)

if os.name == "posix" and os.uname().sysname == "Darwin":
    CACHE_DIR = Path.home() / "Library" / "Caches" / "amadeus"
    DATA_DIR = Path.home() / "Library" / "Application Support" / "amadeus"
elif os.name == "nt":
    CACHE_DIR = Path.home() / "AppData" / "Local" / "amadeus"
    DATA_DIR = Path.home() / "AppData" / "Roaming" / "amadeus"
else:
    CACHE_DIR = Path.home() / ".cache" / "amadeus"
    DATA_DIR = Path.home() / ".local" / "share" / "amadeus"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
