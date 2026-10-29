import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("CORTEXORA_DB", ROOT / "data" / "processed" / "cortexora.db"))
RAW_DIR, SAMPLE_DIR = ROOT / "data" / "raw", ROOT / "data" / "sample"
