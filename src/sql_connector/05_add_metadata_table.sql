-- etl_runs
DROP TABLE IF EXISTS etl_runs;

CREATE TABLE IF NOT EXISTS etl_runs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    last_sql_script_executed INTEGER NOT NULL,
    last_zenodo_harvest_at DATETIME NOT NULL,
    last_version_on_zenodo TEXT NOT NULL
);

INSERT INTO etl_runs (last_sql_script_executed, last_zenodo_harvest_at, last_version_on_zenodo) VALUES (4, "2025-06-01", "v1.2.3");