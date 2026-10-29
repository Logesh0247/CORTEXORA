"""Idempotent ETL: sample/raw CSV -> validate -> SQLite warehouse. Raw is never modified."""
import logging, sqlite3
import pandas as pd
from cortexora.config import DB_PATH, ROOT, SAMPLE_DIR
from cortexora.monitoring.quality import run_all
log = logging.getLogger("cortexora.etl")
TABLES = ["customers","products","orders","order_items","inventory_snapshots","marketing_spend"]

def run(source_dir=SAMPLE_DIR, db_path=DB_PATH) -> pd.DataFrame:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    frames = {t: pd.read_csv(source_dir / f"{t}.csv") for t in TABLES}
    report = run_all(frames)
    if (report.status == "FAIL").any():
        raise ValueError("Data-quality FAIL — aborting load:\n" + report[report.status=="FAIL"].to_string())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = (ROOT / "database" / "schema.sql").read_text()
    with sqlite3.connect(db_path) as con:
        con.executescript("DROP TABLE IF EXISTS " + "; DROP TABLE IF EXISTS ".join(TABLES + ["decisions"]) + ";")
        con.executescript(schema)
        for t, df in frames.items(): df.to_sql(t, con, if_exists="append", index=False)
    log.info("loaded %s", {t: len(f) for t, f in frames.items()})
    return report

def load_table(name: str, db_path=DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con: return pd.read_sql(f"SELECT * FROM {name}", con)  # name from internal allowlist only
