"""Idempotent ETL: sample/raw CSV -> validate -> SQLite warehouse. Raw is never modified."""
import logging, sqlite3
import pandas as pd
from cortexora.config import DB_PATH, ROOT, SAMPLE_DIR
from cortexora.monitoring.quality import run_all
log = logging.getLogger("cortexora.etl")
TABLES = ["customers","products","orders","order_items","inventory_snapshots","marketing_spend"]

def run(source_dir=SAMPLE_DIR, db_path=DB_PATH) -> pd.DataFrame:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    started = pd.Timestamp.now()
    frames = {t: pd.read_csv(source_dir / f"{t}.csv") for t in TABLES}
    report = run_all(frames)
    fails = int((report.status == "FAIL").sum())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = (ROOT / "database" / "schema.sql").read_text()
    def _log_run(status):
        with sqlite3.connect(db_path) as con:
            con.executescript(schema)  # ensures pipeline_runs exists even on failure
            con.execute("INSERT INTO pipeline_runs(started_at,finished_at,status,source,rows_loaded,quality_fails) VALUES (?,?,?,?,?,?)",
                        (started.isoformat(), pd.Timestamp.now().isoformat(), status, str(source_dir),
                         str({t: len(f) for t, f in frames.items()}), fails))
    if fails:
        _log_run("failed_quality_gate")
        raise ValueError("Data-quality FAIL — aborting load:\n" + report[report.status=="FAIL"].to_string())
    with sqlite3.connect(db_path) as con:
        # NOTE: decisions / pipeline_runs are deliberately NOT dropped — the audit
        # history and run log must survive a warehouse reload (Phase 7/8).
        con.executescript("DROP TABLE IF EXISTS " + "; DROP TABLE IF EXISTS ".join(TABLES) + ";")
        con.executescript(schema)
        for t, df in frames.items(): df.to_sql(t, con, if_exists="append", index=False)
    _log_run("success")
    log.info("loaded %s", {t: len(f) for t, f in frames.items()})
    return report

def load_table(name: str, db_path=DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con: return pd.read_sql(f"SELECT * FROM {name}", con)  # name from internal allowlist only
