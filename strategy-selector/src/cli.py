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
reg_app = typer.Typer(no_args_is_help=True, help="Soft regimes")
app.add_typer(reg_app, name="regimes")
rank_app = typer.Typer(no_args_is_help=True, help="Stock ranker")
app.add_typer(rank_app, name="rank")
sel_app = typer.Typer(no_args_is_help=True, help="Strategy selector")
app.add_typer(sel_app, name="select")
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
        if len(t):                       # symbols with no bars in the range have no day table
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
             workers: int = 0, max_minutes: float = 30.0, yes: bool = typer.Option(False, "--yes"),
             db: str = typer.Option("", help="alternative store file (relative to the project)"), cost_mult: float = 1.0):
    """Run all variants x symbols x gates into data/store.duckdb (resumable; finished jobs are skipped)."""
    import pandas as pd
    from src.selector import bulk
    cfg = config.load(db or None, cost_mult)
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


@reg_app.command("report")
def reg_report(top: int = 3, gate: str = ""):
    """Symbol-days per regime and the best variants' weighted mean daily PnL in each (needs `bulk run` data)."""
    from src.features import regimes
    typer.echo(regimes.report(config.load(), top, gate or None).to_string(index=False))


@rank_app.command("eval")
def rank_eval(checkpoint: str = "open+10", k: int = 3, min_days: int = 60, symbols: str = typer.Option("", help="default = learn=true symbols (>= min_history_days)")):
    """Walk-forward: do the top-K ranked symbols earn more (best-variant PnL, gate = checkpoint) than the baseline / random?"""
    import pandas as pd
    from src.selector import ranker
    from src.store import db
    cfg = config.load()
    con = db.connect(cfg, read_only=True)
    feat = con.execute("SELECT * FROM features WHERE checkpoint = ?", [checkpoint]).df()
    ev = con.execute("SELECT * FROM events").df()
    syms = [x.strip().upper() for x in symbols.split(",") if x.strip()] or pd.read_csv(cfg["paths"]["cache"].parent / "coverage.csv").query("learn")["symbol"].tolist()
    d = ranker.design(feat[feat["symbol"].isin(syms)], ev, ranker.target(cfg, checkpoint))
    d = d[d["symbol"].isin(syms)]
    typer.echo(f"symbols={d['symbol'].nunique()} days={d['day'].nunique()} k={k} checkpoint={checkpoint}")
    for name, feats in (("full model", None), ("in-play features only (no symbol history)", [f for f in ranker.FEATS if f != "trade_hist"])):
        res = ranker.evaluate(ranker.walk_forward(d, k, min_days, feats=feats))
        typer.echo(f"{name}: " + ", ".join(f"{a}={b}" for a, b in res.items()))


@sel_app.command("picks")
def sel_picks(checkpoint: str = "open+10", k: int = 3, days: int = 20, min_sample: int = 20, threshold: float = 0.0):
    """Walk-forward picks (ranker top K -> variant or abstain) for the last N test days, with sample sizes and the realised PnL."""
    import pandas as pd
    from src.selector import ranker, variant
    from src.store import db
    cfg = config.load()
    con = db.connect(cfg, read_only=True)
    syms = pd.read_csv(cfg["paths"]["cache"].parent / "coverage.csv").query("learn")["symbol"].tolist()
    feat = con.execute("SELECT * FROM features WHERE checkpoint = ?", [checkpoint]).df()
    d = ranker.design(feat[feat["symbol"].isin(syms)], con.execute("SELECT * FROM events").df(), ranker.target(cfg, checkpoint))
    rk = ranker.walk_forward(d, k, 60).tail(days)
    d0, d1 = con.execute("SELECT min(d0), max(d1) FROM runs").fetchone()
    dd, sy, vs, P, R = variant.load(cfg, checkpoint, syms, d0, d1)
    rows = []
    for r in rk.itertuples():
        t = int(dd.get_loc(pd.Timestamp(r.day)))
        for s in r.picks:
            j = sy.index(s)
            res = variant.select(P, R, vs, t, j, min_sample, threshold)
            pnl = P[t, j, vs.index(res["pick"])] if res["pick"] else 0.0
            rows.append(dict(day=str(r.day.date()), symbol=s, pick=res["pick"] or "ABSTAIN", score=round(res["score"], 2), n_sym=round(res["n_sym"]), n_reg=round(res["n_reg"]),
                             cand=res["candidates"], pnl=round(pnl, 1), avg_all=round(P[t, j].mean(), 1)))
    out = pd.DataFrame(rows)
    (cfg["paths"]["runs"]).mkdir(exist_ok=True)
    out.to_csv(cfg["paths"]["runs"] / "selector_picks.csv", index=False)
    typer.echo(out.to_string(index=False))
    typer.echo(f"days={out['day'].nunique()} picks={len(out)} abstain={(out['pick'] == 'ABSTAIN').sum()} realised pnl: selector {out['pnl'].sum():.0f} vs mean-of-all-variants {out['avg_all'].sum():.0f}")


@app.command("backtest")
def backtest_cmd(from_: str = typer.Option(..., "--from"), to: str = typer.Option(..., "--to"), checkpoint: str = "open+10", top_k: int = 3,
                 neutral: bool = typer.Option(False, "--neutral", help="control: QQQ + mega-caps only")):
    """Walk-forward backtest of rank -> pick variant -> trade; summary + runs/<id>/ files vs baselines."""
    from src.selector import backtest
    typer.echo(backtest.render(backtest.run(config.load(), from_, to, checkpoint, top_k, neutral)))


@app.command("robustness")
def robustness_cmd(from_: str = typer.Option(..., "--from"), to: str = typer.Option(..., "--to"), checkpoint: str = "open+10", top_k: int = 3):
    """Costs x2, neutral universe, bootstrap, shuffled-day and threshold tests -> verdict (JSON in runs/robustness.json)."""
    from src.selector import robust
    cfg = config.load()
    cfg["paths"]["runs"].mkdir(exist_ok=True)
    typer.echo(robust.render(robust.run(cfg, from_, to, checkpoint, top_k, cfg["paths"]["runs"] / "robustness.json")))


if __name__ == "__main__":
    app()
