"""Project-wide paths and settings."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "d3soccer.db"

# Be polite to the sites we scrape.
REQUEST_DELAY_SECONDS = 1.0
USER_AGENT = "d3soccer/0.1 (+https://github.com/elijahredelman/d3-soccer)"
