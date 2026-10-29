import sqlite3
import pandas as pd, pytest
from cortexora.decision_engine.engine import (persist, set_status, record_outcome,
                                              load_decisions, outcome_summary, ensure_decision_schema)

REC = dict(recommendation_id="REC-TEST1", area="Inventory", problem="p", action="Reorder 10 units",
           evidence="stock=5", expected_impact=100.0, priority=7.5)

@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.db"
    with sqlite3.connect(path) as con:
        con.executescript(open("database/schema.sql").read())
    persist([REC], path)
    return path

def test_persist_sets_measurement_period(db):
    d = load_decisions(db); assert d.measurement_period_days.iloc[0] == 30 and d.status.iloc[0] == "pending"

def test_outcome_requires_approval(db):
    with pytest.raises(ValueError, match="not 'approved'"): record_outcome("REC-TEST1", 90, "n", db)
    with pytest.raises(ValueError, match="Unknown"): record_outcome("REC-NOPE", 90, "n", db)

def test_full_lifecycle_and_summary(db):
    set_status("REC-TEST1", "approved", db, owner="Logesh")
    record_outcome("REC-TEST1", 80.0, "supplier delay, partial fill", db)
    d = load_decisions(db); r = d.iloc[0]
    assert r.status == "measured" and r.actual_outcome == 80.0 and r.owner == "Logesh" and "supplier" in r.outcome_note
    s = outcome_summary(d)
    assert s["measured"] == 1 and s["mean_variance_pct"] == pytest.approx(-20.0) and s["within_20pct"] == 1.0
    # measured is terminal for outcome purposes
    with pytest.raises(ValueError): record_outcome("REC-TEST1", 10, "again", db)

def test_summary_empty_safe():
    assert outcome_summary(pd.DataFrame()) == {"measured": 0}

def test_migration_adds_columns_to_old_table(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE decisions(recommendation_id TEXT PRIMARY KEY, status TEXT, expected_impact REAL, priority REAL)")
        con.execute("INSERT INTO decisions VALUES ('REC-OLD','pending',10,1)")
    ensure_decision_schema(path)
    d = load_decisions(path)
    assert {"owner", "measurement_period_days", "outcome_note", "outcome_recorded_at", "actual_outcome"} <= set(d.columns)
