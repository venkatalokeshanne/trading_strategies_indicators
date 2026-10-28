import typer

from src import config

app = typer.Typer(no_args_is_help=True, add_completion=False)
data_app = typer.Typer(no_args_is_help=True, help="Market data")
app.add_typer(data_app, name="data")


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


if __name__ == "__main__":
    app()
