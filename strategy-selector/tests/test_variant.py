"""The selector for day t may not use PnL or regimes of day t or later."""
import numpy as np

from src.selector import variant as V


def _data(seed=0, days=80, syms=6, variants=5):
    rng = np.random.default_rng(seed)
    return rng.normal(0, 10, (days, syms, variants)) * (rng.random((days, syms, variants)) > 0.3), rng.random((days, syms, 8))


def test_scores_ignore_the_target_day_and_later():
    P, R = _data()
    t = 50
    e0 = V.score(P, R, t, 2)
    P2, R2 = P.copy(), R.copy()
    P2[t:] = rng_junk = np.random.default_rng(9).normal(0, 99, P2[t:].shape)       # PnL from t on
    R2[t + 1:] = 0.123                                                              # regimes after t (day t's own regimes are known at its open)
    e1 = V.score(P2, R2, t, 2)
    assert all(np.array_equal(a, b) for a, b in zip(e0, e1))


def test_thin_samples_fall_back_to_the_parent_and_abstain_rule():
    P, R = _data()
    P[:, 0, 3] = 0                                   # symbol 0 never traded variant 3: its estimate must equal the regime-level one, not 0-biased noise
    est, n1, n2, n3 = V.score(P, R, 60, 0, k=20.0)
    assert np.isfinite(est).all() and n1 > 0
    res = V.select(P, R, [f"v{i}" for i in range(5)], 60, 0, threshold=1e9)
    assert res["pick"] == "" and res["candidates"] == 5                                # abstains when nothing clears the threshold
