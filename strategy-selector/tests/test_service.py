"""Each service function is called once against the stored data (skipped when the store is absent)."""
import pytest

from src import config, service

pytestmark = pytest.mark.skipif(not config.load()["paths"]["db"].exists(), reason="no store")


def test_service_functions():
    s = service.run_backtest("2024-06-03", "2024-06-28")
    assert {"selector", "baselines", "out"} <= s.keys()
    runs = service.list_runs()
    assert s["out"].endswith(runs["run_id"].iloc[-1]) or len(runs) > 0
    r = service.get_run("latest")
    assert not r["picks"].empty and not r["daily"].empty
    v = service.get_variant_stats()
    assert len(v) > 0 and {"net", "trades"} <= set(v.columns)
    assert len(service.get_regime_table("2024-06-14")) > 10
    assert "regime" in service.get_regime_table(gate="open+10").columns
