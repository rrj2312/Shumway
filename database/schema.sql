CREATE TABLE IF NOT EXISTS raw_financials(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    quarter TEXT NOT NULL,
    stmt_type TEXT NOT NULL, -- 'income', 'balance', 'cashflow'
    line_item TEXT NOT NULL,
    value REAL,
    fetched_at TOMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, quarter, stmt_type, line_item)
);
CREATE TABLE IF NOT EXISTS price_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      TEXT    NOT NULL,
    date            DATE    NOT NULL,
    close           REAL,
    volume          INTEGER,
    market_cap      REAL,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, date)
);

CREATE TABLE IF NOT EXISTS nifty500_history (
    date        DATE PRIMARY KEY,
    close       REAL,
    fetched_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS features (
    company_id          TEXT    NOT NULL,
    quarter             TEXT    NOT NULL,
    interest_coverage   REAL,
    leverage            REAL,
    profitability       REAL,
    cf_divergence       REAL,
    current_ratio       REAL,
    roe                 REAL,
    gross_margin        REAL,
    debt_growth         REAL,
    revenue_growth      REAL,
    rel_size            REAL,
    excess_return       REAL,
    return_volatility   REAL,
    repo_rate           REAL,
    computed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, quarter)
);

CREATE TABLE IF NOT EXISTS scores (
    company_id          TEXT    NOT NULL,
    quarter             TEXT    NOT NULL,
    hazard_probability  REAL,
    risk_tier           TEXT,
    score_delta         REAL,
    red_signal_count    INTEGER,
    scored_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, quarter)
);

CREATE TABLE IF NOT EXISTS distress_labels (
    company_id      TEXT    NOT NULL,
    quarter         TEXT    NOT NULL,
    distress        INTEGER NOT NULL DEFAULT 0,  -- 0 or 1
    event_type      TEXT,   -- 'PCA', 'rating_downgrade', 'default', 'moratorium'
    source_note     TEXT,
    PRIMARY KEY (company_id, quarter)
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  TEXT    NOT NULL,
    signal      TEXT    NOT NULL,
    severity    TEXT    NOT NULL,   -- 'warning', 'critical'
    message     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);