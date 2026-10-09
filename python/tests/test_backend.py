"""Backend logic: calculators against closed forms, the quality gate, scoring bounds, and an
end-to-end API run on a temporary database built from synthetic bars."""

from __future__ import annotations

import math

import pytest

from tradesearch import calculators as C
from tradesearch import scoring


def test_calculators_closed_forms():
    assert C.loss_recovery(50)["gainNeededPercent"] == pytest.approx(100.0)
    assert C.risk_reward(100, 95, 110)["riskReward"] == pytest.approx(2.0)
    assert C.risk_reward(100, 95, 110)["breakevenWinRate"] == pytest.approx(100 / 3)
    assert C.kelly_criterion(55, 1.5, trades=10, runs=5)["kellyPercent"] == pytest.approx(25.0)
    assert C.profit_factor(win_rate=50, reward_risk=2)["profitFactor"] == pytest.approx(2.0)
    assert C.trading_expectancy(40, 300, 100)["expectancyPerTrade"] == pytest.approx(60.0)
    # P(at least one run of 6 losses in 100 fair coin flips) ≈ 0.546
    assert C.losing_streak(50, 100, 6)["probabilityPercent"] == pytest.approx(54.61, abs=0.01)
    assert C.trading_compounding(1000, 10, 2)["finalEquity"] == pytest.approx(1210.0)
    assert C.lot_size(10_000, 1, 50, 1)["positionSize"] == pytest.approx(2.0)
    sim = C.prop_firm_challenge(10, 10, 5, 50, 2, 1, runs=200)
    assert 0 <= sim["passProbabilityPercent"] <= 100
    card = C.strategy_performance_metrics([100, -50, 120, -40, 80, -60, 150])
    assert card["profitFactor"] == pytest.approx(450 / 150) and card["grade"] in "ABCDF"


def _m(**kw):
    base = {"totalTrades": 120, "netProfit": 5000.0, "netProfitPercent": 50.0, "profitFactor": 1.6,
            "maxDrawdownPercent": 15.0, "latestTradeTime": 1_700_000_000_000, "periodFrom": 1_600_000_000_000,
            "periodTo": 1_700_000_000_000, "sharpeRatio": 0.5, "pValue": 0.01, "positiveMonthsPercent": 60.0,
            "monthsTested": 36, "buyHoldReturnPercent": 40.0, "tradesPerMonth": 4, "avgTradePercent": 0.3}
    base.update(kw)
    return base


def test_quality_gate():
    ok, reasons = scoring.quality_gate(_m(), repainting=False, bars=5000)
    assert ok and not reasons
    for bad, why in ((dict(totalTrades=5), "fewer than"), (dict(netProfitPercent=0.2), "net profit"),
                     (dict(profitFactor=0.9), "profit factor"), (dict(maxDrawdownPercent=95), "drawdown"),
                     (dict(latestTradeTime=1_620_000_000_000), "no trade")):
        ok, reasons = scoring.quality_gate(_m(**bad), repainting=False, bars=5000)
        assert not ok and any(why in r for r in reasons), (bad, reasons)
    ok, reasons = scoring.quality_gate(_m(), repainting=True, bars=5000)
    assert not ok and "repainting" in reasons[0]


def test_robust_score_bounds_and_monotonic_edge():
    eq = [100 * (1.001 ** k) for k in range(500)]
    trades = [{"profit": 10.0 if k % 3 else -5.0} for k in range(120)]
    a = scoring.robust_score(_m(), eq, trades, breadth=0.7)
    b = scoring.robust_score(_m(sharpeRatio=1.2, profitFactor=2.5, pValue=0.0001), eq, trades, breadth=0.7)
    for s in (a, b):
        assert 0 <= s["robustnessScore"] <= 100
        assert all(0 <= s[k] <= 100 for k in ("consistency", "backtests", "edge", "practicality"))
    assert b["edge"] > a["edge"] and b["robustnessScore"] >= a["robustnessScore"]


def test_api_end_to_end(tmp_path, monkeypatch):
    from conftest import make_bars
    from fastapi.testclient import TestClient

    from tradesearch import api, catalog, data, pipeline

    monkeypatch.setenv("TRADESEARCH_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(data, "CACHE_DIR", tmp_path / "cache")
    ref = data.SymbolRef("TEST:SYNTH", "crypto", "binance", "SYNTH", "Synthetic")
    data.save_cache(ref, "D", make_bars(n=1500))
    monkeypatch.setattr(data, "find_symbol", lambda q, u=None: ref if "SYNTH" in q.upper() else None)
    url = f"sqlite:///{tmp_path / 't.db'}"
    ents = catalog.discover("strategies")
    results = [pipeline.job((str(e.path), ref.__dict__, "D", None, 1500, True,
                             str(e.pine_path) if e.pine_path else None)) for e in ents]
    assert all(r["ok"] for r in results), [r.get("error") for r in results if not r["ok"]]
    pipeline.store(ents, results, url)
    monkeypatch.setattr(api, "_ENGINE", api.db.engine(url))
    c = TestClient(api.app)
    assert c.get("/api/stats/platform").json()["analyzed"] == len(ents)
    s = c.get("/api/agent/search-backtests?eligibleOnly=false&sort=roi&limit=50").json()
    assert len(s["data"]) == len(ents) and s["account"]["tier"] == "self-hosted"
    bid = s["data"][0]["id"]
    d = c.get(f"/api/agent/backtests/{bid}?includeTrades=true&includeEquityCurve=true").json()["data"]
    assert {"trades", "equityCurve", "drawdownCurve", "buyHoldCurve", "metrics"} <= set(d)
    st = c.get(f"/api/agent/strategies/{ents[0].tv_id}").json()["data"]
    assert st["repainting"]["totalChecks"] == 8
    assert c.post("/api/tools/loss-recovery-calculator", json={"loss_percent": 50}).json()["data"]["gainNeededPercent"] == 100
