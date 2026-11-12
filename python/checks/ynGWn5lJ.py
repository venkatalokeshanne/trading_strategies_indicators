"""Independent check — SMC MentorFX Pro Max (ynGWn5lJ): 5-min bars. Kill zones 09:00-12:00 and 13:00-17:00 in UTC+3 (pandas fixed-offset zone). Close crossing
the PREVIOUS bar's 15-bar high/low, with a 30-bar-extreme break ("IDM") of the previous bar's 30-bar high/low, enters (reversing). strategy.exit has no
from_entry: loss 100 ticks and profit 250 ticks (0.01 tick) from the entry price, issued every bar and so already working on the fill bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ynGWn5lJ"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(20000, seed=155, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Etc/GMT-3")      # UTC+3
    m = (t.dt.hour * 60 + t.dt.minute).to_numpy()
    kz = ((m >= 540) & (m < 720)) | ((m >= 780) & (m < 1020))
    h30, l30 = roll(h, 30, np.max), roll(l, 30, np.min)
    h15, l15 = roll(h, 15, np.max), roll(l, 15, np.min)
    h30p, l30p = np.r_[np.nan, h30[:-1]], np.r_[np.nan, l30[:-1]]
    h15p, l15p = np.r_[np.nan, h15[:-1]], np.r_[np.nan, l15[:-1]]
    pc = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        idm = (h > h30p) | (l < l30p)
        lc = (c > h15p) & (pc <= np.r_[np.nan, h15p[:-1]])
        sc = (c < l15p) & (pc >= np.r_[np.nan, l15p[:-1]])
        lg, sg = kz & idm & lc, kz & idm & sc
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sg[i] else []),
                   stop=lambda i, pos, ep, eb: ep - pos * 100 * 0.01, target=lambda i, pos, ep, eb: ep + pos * 250 * 0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
