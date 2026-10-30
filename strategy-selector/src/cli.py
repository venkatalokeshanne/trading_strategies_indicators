import typer

from src import config

app = typer.Typer(no_args_is_help=True, add_completion=False)
data_app = typer.Typer(no_args_is_help=True, help="Market data")
app.add_typer(data_app, name="data")
pine_app = typer.Typer(no_args_is_help=True, help="Pine strategy catalog")
app.add_typer(pine_app, name="pine")
feat_app = typer.Typer(no_args_is_help=True, help="Day features per checkpoint")
app.add_typer(feat_app, name="features")
ev_app = typer.Typer(no_args_is_help=True, help="Event flags")
app.add_typer(ev_app, name="events")
bulk_app = typer.Typer(no_args_is_help=True, help="Bulk runner + DuckDB store")
app.add_typer(bulk_app, name="bulk")


@app.command()
def smoke():
    """Run one converted strategy through pinelib on synthetic bars."""
    from src import smoke as s
    n, pnl = s.run()
    typer.echo(f"universe={len(config.load()['universe'])} trades={n} net_profit={pnl:.2f}")


@data_app.command("fetch")
def fetch(universe: bool = typer.Option(False, "--universe"),
          symbols: str = typer.Option("", "--symbols", help="comma list"),
          start: str = typer.Option(..., "--start"), end: str = typer.Option(..., "--end")):
    """Fetch 1-min bars into the parquet cache (only missing ranges)."""
    from src.data import twelvedata
    cfg = config.load()
    syms = cfg["universe"] if universe else [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        raise typer.BadParameter("give --universe or --symbols")
    twelvedata.fetch_many(cfg, syms, start, end)


@data_app.command("check")
def check(universe: bool = typer.Option(False, "--universe"),
          symbols: str = typer.Option("", "--symbols", help="comma list")):
    """Data quality + coverage table; bad days -> data/bad_days.csv, learn flag in data/coverage.csv."""
    import pandas as pd
    from src.data import quality
    cfg = config.load()
    syms = cfg["universe"] if universe else [x.strip().upper() for x in symbols.split(",") if x.strip()]
    days, rows = [], []
    for sym in syms:
        t, s = quality.check_symbol(cfg, sym)
        rows.append(s)
        days.append(t[t["bad"]])
    cov = pd.DataFrame(rows)
    out = cfg["paths"]["cache"].parent
    pd.concat(days).to_csv(out / "bad_days.csv", index=False)
    cov.to_csv(out / "coverage.csv", index=False)
    typer.echo(cov.to_string(index=False))


@app.command("run")
def run_cmd(strategies: str = typer.Option(..., help="script file names/paths in the TV repo python/strategies, comma list"),
            symbols: str = typer.Option(...), tf: str = "5", gate: str = "open",
            start: str = typer.Option(...), end: str = typer.Option(...)):
    """Day-trade each strategy x symbol x tf x gate; per-day PnL table (cached)."""
    import pandas as pd
    from src.adapter import daytrade
    cfg = config.load()
    sdir = config.pine_repo() / "python/strategies"
    scripts = [str(next(sdir.glob(x.strip() + "*"))) for x in strategies.split(",")]
    res = daytrade.run_many(cfg, scripts, [x.strip().upper() for x in symbols.split(",")],
                            [int(x) for x in tf.split(",")], gate.split(","), start, end)
    rows = []
    for (script, sym, t, g, *_), tr, cached in res:
        rows.append(dict(strategy=script.split("/")[-1][:24], symbol=sym, tf=t, gate=g, trades=len(tr),
                         days=tr["day"].nunique(), pnl=round(tr["pnl"].sum(), 2), cached=cached))
        tr.assign(strategy=script.split("/")[-1][:24], symbol=sym, tf=t, gate=g)
    typer.echo(pd.DataFrame(rows).to_string(index=False))
    daily = pd.concat([tr.assign(strategy=r["strategy"], symbol=r["symbol"]) for r, (_, tr, _) in zip(rows, res)])
    out = cfg["paths"]["runs"] / "adapter_daily.csv"
    out.parent.mkdir(exist_ok=True)
    daily.groupby(["strategy", "symbol", "day"])["pnl"].sum().round(2).to_csv(out)
    typer.echo(f"per-day PnL -> {out}")


@pine_app.command("triage")
def triage(top: int = 30):
    """Scan all Pine strategies -> data/catalog.json; summary + top list."""
    import pandas as pd
    from src.pine import triage as tr
    cfg = config.load()
    df = tr.build(cfg)
    cfg["paths"]["catalog"].parent.mkdir(exist_ok=True)
    cfg["paths"]["catalog"].write_text(df.reset_index().to_json(orient="records", indent=0))
    pend = df[df["status"] == "pending"]
    cfg["paths"]["runs"].mkdir(exist_ok=True)
    pend[pend["priority"] > 0].head(100)[["title", "convertibility", "priority", "tf_hint", "direction", "lines", "dup_of"]].to_csv(cfg["paths"]["runs"] / "triage_top100.csv")
    typer.echo(f"strategies={len(df)}  status: {df['status'].value_counts().to_dict()}")
    typer.echo("pending by convertibility: " + str(pend["convertibility"].value_counts().to_dict()) + f"  dups={int((pend['dup_of'] != '').sum())}")
    typer.echo(pend[pend["priority"] > 0].head(top)[["title", "convertibility", "priority"]].to_string(max_colwidth=60))


@bulk_app.command("run")
def bulk_run(start: str = typer.Option(...), end: str = typer.Option(...),
             symbols: str = typer.Option("", help="comma list; default = every learn=true symbol of data/coverage.csv"),
             strategies: str = typer.Option("", help="ids, comma list; default = every converted FULL strategy"),
             gates: str = typer.Option("", help="comma list; default = config gates"),
             workers: int = 0, max_minutes: float = 30.0, yes: bool = typer.Option(False, "--yes")):
    """Run all variants x symbols x gates into data/store.duckdb (resumable; finished jobs are skipped)."""
    import pandas as pd
    from src.selector import bulk
    cfg = config.load()
    syms = [x.strip().upper() for x in symbols.split(",") if x.strip()]
    if not syms:
        cov = pd.read_csv(cfg["paths"]["cache"].parent / "coverage.csv")
        syms = cov[cov["learn"]]["symbol"].tolist()
    bulk.run(cfg, [x.strip() for x in strategies.split(",") if x.strip()] or None, syms,
             [x.strip() for x in gates.split(",") if x.strip()] or cfg["gates"], start, end, workers or None, max_minutes, yes, typer.echo)


@bulk_app.command("top")
def bulk_top(day: str = typer.Option(...), n: int = 5, gate: str = ""):
    """Best and worst variants on one day."""
    from src.selector import bulk
    top, bot = bulk.top_bottom(config.load(), day, n, gate or None)
    typer.echo("TOP\n" + top.to_string(index=False) + "\nBOTTOM\n" + bot.to_string(index=False))


@feat_app.command("build")
def feat_build(symbols: str = typer.Option("", help="comma list; default = every symbol with cached bars"),
               checkpoints: str = typer.Option("", help="default = config checkpoints")):
    """Compute features for every symbol-day-checkpoint into the DuckDB `features` table."""
    from src.data.twelvedata import _dir
    from src.features import day
    from src.store import db
    cfg = config.load()
    syms = [x.strip().upper() for x in symbols.split(",") if x.strip()] or [s for s in cfg["universe"] if (_dir(cfg, s) / "coverage.json").exists()]
    f = day.build(cfg, syms, [x.strip() for x in checkpoints.split(",") if x.strip()] or None)
    con = db.connect(cfg)
    con.register("f_", f)
    con.execute("CREATE OR REPLACE TABLE features AS SELECT * FROM f_")
    typer.echo(f"features: {len(f)} rows, {f['symbol'].nunique()} symbols, {f['day'].nunique()} days, checkpoints {sorted(f['checkpoint'].unique())}")


@ev_app.command("refresh-fomc")
def ev_fomc():
    """Download FOMC decision days from federalreserve.gov into config/events.yaml."""
    from src.features import events
    d = events.refresh_fomc()
    typer.echo(f"fomc: {len(d)} decision days {d[0]}..{d[-1]}")


@ev_app.command("build")
def ev_build(start: str = typer.Option(...), end: str = typer.Option(...), symbols: str = typer.Option("", help="default = cached symbols")):
    """Event flags per symbol-day -> DuckDB `events` (earnings NaN where no source has the symbol)."""
    import pandas as pd
    from src.data import calendar
    from src.data.twelvedata import _dir
    from src.features import events
    from src.store import db
    cfg = config.load()
    syms = [x.strip().upper() for x in symbols.split(",") if x.strip()] or [s for s in cfg["universe"] if (_dir(cfg, s) / "coverage.json").exists()]
    f = events.build(cfg, syms, pd.DatetimeIndex(calendar.sessions(start, end)["day"]))
    con = db.connect(cfg)
    con.register("f_", f)
    con.execute("CREATE OR REPLACE TABLE events AS SELECT * FROM f_")
    known = f.groupby("symbol")["earn_day"].apply(lambda x: x.notna().any())
    typer.echo(f"events: {len(f)} rows; earnings known for {int(known.sum())}/{len(known)} symbols (rest NaN: add them to config/earnings.csv)")


if __name__ == "__main__":
    app()
