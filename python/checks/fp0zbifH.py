"""Independent check — CNPS 09 EMA Cross (fp0zbifH): 15-minute bars (24h synthetic, New York clock), one position (entries reverse), trade list only. EMA7 crossing EMA50 with the SMA200 slope as trend filter (long needs SMA200 >= its previous value,
short needs <), inside 09:00 <= time < 14:30; the first bar after the window closes any position (next open). While in a position at a script run the stop / limit are 3 / 6 points around the entry price (inputs loosened from 10 / 30 on both sides), so bar i works
with bar i-1's levels if a same-side position existed at bar i-1's script run. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "fp0zbifH"


def check():
    df = bars(15000, seed=744, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mm = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ins = (mm >= 540) & (mm < 870)
    sma = np_sma(c, 200)
    sma1 = np.r_[np.nan, sma[:-1]]
    ef, es = np_ema(c, 7), np_ema(c, 50)
    with np.errstate(invalid="ignore"):
        bull, bear = sma >= sma1, sma < sma1
        ls = np_cross_over(ef, es) & bull & ins
        ss = np_cross_under(ef, es) & bear & ins
    just_ended = np.r_[False, (~ins[1:]) & ins[:-1]]
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        if just_ended[i] and pos != 0:
            out += [("close", 1), ("close", -1)]
        if ls[i]:
            out.append(("entry", 1))
        if ss[i]:
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] - 3.0 * pos

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] + 6.0 * pos

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Cắt lỗ (điểm)": 3.0, "Chốt lời (điểm)": 6.0},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
