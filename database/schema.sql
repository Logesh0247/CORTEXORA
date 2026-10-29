CREATE TABLE IF NOT EXISTS customers(customer_id INTEGER PRIMARY KEY, segment TEXT, region TEXT, signup_date TEXT);
CREATE TABLE IF NOT EXISTS products(product_id INTEGER PRIMARY KEY, product_name TEXT, category TEXT, unit_cost REAL, list_price REAL);
CREATE TABLE IF NOT EXISTS orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers, order_date TEXT, region TEXT, channel TEXT);
CREATE TABLE IF NOT EXISTS order_items(order_id INTEGER REFERENCES orders, product_id INTEGER REFERENCES products, qty INTEGER, unit_price REAL, discount REAL, unit_cost REAL, PRIMARY KEY(order_id,product_id));
CREATE TABLE IF NOT EXISTS inventory_snapshots(product_id INTEGER REFERENCES products, snapshot_date TEXT, stock_on_hand INTEGER, lead_time_days INTEGER, PRIMARY KEY(product_id,snapshot_date));
CREATE TABLE IF NOT EXISTS marketing_spend(spend_date TEXT, channel TEXT, spend REAL, clicks INTEGER, conversions INTEGER, PRIMARY KEY(spend_date,channel));
CREATE TABLE IF NOT EXISTS decisions(recommendation_id TEXT PRIMARY KEY, created_at TEXT, area TEXT, problem TEXT, action TEXT, evidence TEXT, expected_impact REAL, priority REAL, status TEXT DEFAULT 'pending', decided_at TEXT, actual_outcome REAL, owner TEXT, measurement_period_days INTEGER, outcome_note TEXT, outcome_recorded_at TEXT);
CREATE TABLE IF NOT EXISTS pipeline_runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT, status TEXT, source TEXT, rows_loaded TEXT, quality_fails INTEGER);
