"""DuckDB store: runs (one row per job, the resume key), trades, daily_pnl, variants."""
import duckdb

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(key VARCHAR PRIMARY KEY, variant VARCHAR, symbol VARCHAR, gate VARCHAR, d0 DATE, d1 DATE,
                                status VARCHAR, n_trades INTEGER, secs DOUBLE, err VARCHAR);
CREATE TABLE IF NOT EXISTS trades(variant VARCHAR, symbol VARCHAR, gate VARCHAR, day DATE, entry_time TIMESTAMPTZ, exit_time TIMESTAMPTZ,
                                  dir VARCHAR, qty DOUBLE, entry_price DOUBLE, exit_price DOUBLE, pnl DOUBLE, commission DOUBLE);
CREATE TABLE IF NOT EXISTS daily_pnl(variant VARCHAR, symbol VARCHAR, date DATE, gate VARCHAR, pnl DOUBLE, n_trades INTEGER);
CREATE TABLE IF NOT EXISTS variants(variant VARCHAR PRIMARY KEY, strategy VARCHAR, tf INTEGER, params VARCHAR, status VARCHAR, reason VARCHAR);
"""


def connect(cfg, read_only: bool = False):
    cfg["paths"]["db"].parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(cfg["paths"]["db"]), read_only=read_only)
    if not read_only:
        con.execute(SCHEMA)
    return con


def save_job(con, key, variant, symbol, gate, d0, d1, status, trades, secs, err=""):
    """One job's rows in a single transaction, so an interrupted run leaves no half-written job."""
    con.execute("BEGIN")
    try:
        n = 0 if trades is None else len(trades)
        if n:
            t = trades.assign(variant=variant, symbol=symbol, gate=gate)
            con.register("t_", t)
            con.execute("INSERT INTO trades SELECT variant, symbol, gate, day, entry_time, exit_time, dir, qty, entry_price, exit_price, pnl, commission FROM t_")
            con.execute("INSERT INTO daily_pnl SELECT variant, symbol, day, gate, sum(pnl), count(*) FROM t_ GROUP BY variant, symbol, day, gate")
            con.unregister("t_")
        con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)", [key, variant, symbol, gate, d0, d1, status, n, secs, err[:300]])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
