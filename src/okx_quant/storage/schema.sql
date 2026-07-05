-- Initial event and ledger schema draft.

CREATE TABLE IF NOT EXISTS market_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    channel TEXT NOT NULL,
    inst_id TEXT,
    received_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candles (
    inst_id TEXT NOT NULL,
    bar TEXT NOT NULL,
    ts TEXT NOT NULL,
    open TEXT NOT NULL,
    high TEXT NOT NULL,
    low TEXT NOT NULL,
    close TEXT NOT NULL,
    volume TEXT NOT NULL,
    confirm INTEGER NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (inst_id, bar, ts)
);

CREATE TABLE IF NOT EXISTS trade_intents (
    intent_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    inst_id TEXT NOT NULL,
    side TEXT NOT NULL,
    notional_ccy TEXT NOT NULL,
    reference_price TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    client_order_id TEXT PRIMARY KEY,
    exchange_order_id TEXT,
    inst_id TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    price TEXT,
    size TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    fill_id TEXT PRIMARY KEY,
    client_order_id TEXT NOT NULL,
    exchange_order_id TEXT,
    inst_id TEXT NOT NULL,
    side TEXT NOT NULL,
    price TEXT NOT NULL,
    size TEXT NOT NULL,
    fee TEXT NOT NULL,
    fee_ccy TEXT NOT NULL,
    filled_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    taken_at TEXT NOT NULL,
    ccy TEXT NOT NULL,
    equity TEXT NOT NULL,
    available TEXT NOT NULL,
    frozen TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_events (
    event_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    inst_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reasons TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    summary TEXT NOT NULL
);

