import typer

from src import config

app = typer.Typer(no_args_is_help=True, add_completion=False)
data_app = typer.Typer(no_args_is_help=True, help="Market data")
app.add_typer(data_app, name="data")
pine_app = typer.Typer(no_args_is_help=True, help="Pine strategy catalog")
app.add_typer(pine_app, name="pine")


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


if __name__ == "__main__":
    app()
