"""Project-wide paths, resolved from the repo root so commands work from any directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "snapshots"
WEB_DIR = PROJECT_ROOT / "web"
APP_DATA_JS = WEB_DIR / "app_data.js"
# Hand-pasted NCAA NPI table (see the file's header comment); overrides the NPI feed.
NPI_PASTE = PROJECT_ROOT / "data" / "npi.txt"
