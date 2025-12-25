-- initialization_sql.sql (SQLite)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS inputs (
    id INTEGER PRIMARY KEY,          -- auto row id
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    z INTEGER NOT NULL,
    yaw INTEGER NOT NULL,
    arm INTEGER NOT NULL CHECK (arm IN (0, 1))
);

CREATE TABLE IF NOT EXISTS outputs (
    id INTEGER PRIMARY KEY,          -- auto row id
    inputs_id INTEGER NOT NULL,      -- FK to inputs.id
    m1 INTEGER NOT NULL,
    m2 INTEGER NOT NULL,
    m3 INTEGER NOT NULL,
    m4 INTEGER NOT NULL,
    m5 INTEGER NOT NULL,
    m6 INTEGER NOT NULL,
    m7 INTEGER NOT NULL,
    m8 INTEGER NOT NULL,
    FOREIGN KEY (inputs_id) REFERENCES inputs(id) ON DELETE CASCADE
);
