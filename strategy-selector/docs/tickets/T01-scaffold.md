# T01 Scaffold
- pyproject.toml, config/default.yaml (costs tiers, checkpoints, EOD cutoff, max entries/day, min-sample, min-history, timeframes [5,10,15], paths), src/config.py (loads default + watchlists → universe), src/cli.py typer skeleton
- `pip install -e $PINE_REPO_PATH/python`; smoke test: run one converted strategy from `python/strategies/` on synthetic or cached bars via `pinelib.runner.run`, print trade count + net profit
Accept: `--help` works; universe count ≈69; smoke run prints numbers.
