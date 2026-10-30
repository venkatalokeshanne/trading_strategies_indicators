"""Strategy selector: for a chosen symbol-day pick the variant (strategy x tf) or abstain.
Expected $ for variant v on target day D = hierarchical shrinkage over PAST days only (day < D):
  symbol+variant+regime  ->(k)  variant+regime across symbols  ->(k)  variant overall,
where 'similar' past days are weighted by a Gaussian kernel on the 8-regime vector (soft regimes, no hard buckets).
Shrinkage: est = (n*mean + k*parent)/(n + k) with n the kernel-weighted sample and k = min_sample, so thin samples fall back to the parent.
A variant needs min_sample overall days; the best shrunk score must exceed `threshold` $ or the symbol is skipped (abstain). Every call logs how many candidates were considered."""
import numpy as np
import pandas as pd

from src.features import regimes as RG

BW = 0.6          # kernel bandwidth on the regime-vector distance


def load(cfg, gate: str, symbols, d0, d1):
    """P[day, symbol, variant] best-effort $ per day (0 on no-trade days) and R[day, symbol, regime] soft regimes (neutral .5 where unknown)."""
    from src.data import calendar
    from src.store import db
    con = db.connect(cfg, read_only=True)
    runs = con.execute("SELECT DISTINCT r.variant, r.symbol FROM runs r JOIN variants v USING (variant) WHERE r.gate = ? AND r.status='ok' AND v.status='ok'", [gate]).df()
    pnl = con.execute("SELECT variant, symbol, date AS day, pnl FROM daily_pnl WHERE gate = ?", [gate]).df()
    days = pd.DatetimeIndex(calendar.sessions(d0, d1)["day"])
    variants = sorted(runs["variant"].unique())
    syms = sorted(set(symbols) & set(runs["symbol"]))
    P = np.zeros((len(days), len(syms), len(variants)))
    di, si, vi = {d: i for i, d in enumerate(days)}, {s: i for i, s in enumerate(syms)}, {v: i for i, v in enumerate(variants)}
    pnl["day"] = pd.to_datetime(pnl["day"])
    for r in pnl[pnl["symbol"].isin(syms) & pnl["day"].isin(days)].itertuples():
        P[di[r.day], si[r.symbol], vi[r.variant]] = r.pnl
    rg = RG.regimes(cfg, syms, days)
    R = np.full((len(days), len(syms), len(RG.REGIMES)), 0.5)
    for s, g in rg.groupby("symbol"):
        R[:, si[s], :] = g.set_index("day").reindex(days)[RG.REGIMES].fillna(0.5).to_numpy()
    return days, syms, variants, P, R


def _mean(P, w):
    """Weighted mean over the first axes of P with weights w (same leading shape); returns (mean per variant, effective n)."""
    n = w.sum()
    return (np.tensordot(w, P, axes=(list(range(w.ndim)), list(range(w.ndim)))) / n if n > 0 else np.zeros(P.shape[-1])), n


def score(P, R, t: int, j: int, k: float = 20.0, bw: float = BW):
    """Shrunk expected $ per variant for symbol j on day index t from days < t only. Returns (est, n_sym, n_reg, n_all)."""
    assert t > 0
    Pp, Rp = P[:t], R[:t]                                           # strictly before the target day
    target = R[t, j]
    kern = np.exp(-((Rp - target) ** 2).sum(-1) / (2 * bw ** 2))     # [t, S]
    m3 = Pp.mean((0, 1))
    m2, n2 = _mean(Pp, kern)
    m1, n1 = _mean(Pp[:, j], kern[:, j])
    e2 = (n2 * m2 + k * m3) / (n2 + k)
    e1 = (n1 * m1 + k * e2) / (n1 + k)
    return e1, n1, n2, Pp.shape[0] * Pp.shape[1]


def select(P, R, variants, t: int, j: int, min_sample: int = 20, threshold: float = 0.0, k: float = 20.0) -> dict:
    est, n1, n2, n3 = score(P, R, t, j, k)
    ok = range(len(variants))                                                                         # every variant is a candidate
    live = [v for v in ok if (P[:t, :, v] != 0).sum() >= min_sample]                                  # min-sample rule: enough traded symbol-days overall
    if not live:
        return dict(pick="", score=np.nan, n_sym=n1, n_reg=n2, candidates=len(ok), live=0)
    best = max(live, key=lambda v: est[v])
    return dict(pick=variants[best] if est[best] > threshold else "", score=float(est[best]), n_sym=float(n1), n_reg=float(n2), candidates=len(ok), live=len(live))
