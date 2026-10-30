"""Walk-forward guard: a day's pick may not depend on any PnL of that day or later."""
import numpy as np
import pandas as pd

from src.selector import ranker as R


def _raw(n_days=90, n_sym=8, seed=0):
    rng = np.random.default_rng(seed)
    rows = [dict(symbol=f"S{s}", day=pd.Timestamp("2024-01-02") + pd.tseries.offsets.BDay(d), gap_atr=rng.normal(), vol_rel=rng.uniform(0.2, 3),
                 range_atr=rng.uniform(0, 1), prior_rel_vol=rng.uniform(0.5, 2), prior_range_atr=rng.uniform(0, 1.5), y=float(rng.normal(0, 50)))
            for d in range(n_days) for s in range(n_sym)]
    f = pd.DataFrame(rows)
    return f.drop(columns="y"), f[["symbol", "day"]].assign(fomc=0, cpi=0, jobs=0, earn_reaction=0), f[["symbol", "day", "y"]]


def test_future_pnl_does_not_change_past_picks():
    feat, ev, y = _raw()
    cut = sorted(y["day"].unique())[75]
    r0 = R.walk_forward(R.design(feat, ev, y), k=2, min_days=30)
    y2 = y.copy()
    y2.loc[y2["day"] >= cut, "y"] *= 7                      # alter PnL from `cut` on
    r1 = R.walk_forward(R.design(feat, ev, y2), k=2, min_days=30)
    before = r0["day"] < cut
    # the picks (not the PnL they earn) of earlier days are unchanged: compare earned y on the unaltered days
    assert r0[before]["model"].tolist() == r1[before]["model"].tolist()
    assert r0[~before]["model"].tolist() != r1[~before]["model"].tolist()
