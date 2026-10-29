"""Independent check — Mean Reversion Range (1FgHp6Cv): daily bars, process_orders_on_close, one position, 1 unit. Ranging = ADX14 < 20 (loosened to 30 on both sides so enough trades occur; the abort buffer stays 8, so the regime
limit is 38). Long: close <= lower BB(20, 2), RSI14 <= 30, flat (short: close >= upper, RSI >= 70), entered at the close with stop = band -/+ 1 ATR14 fixed at the signal. While in a position at a script run a stop (that fixed level) and a limit at
the CURRENT SMA20 basis are issued, so bar i works with bar i-1's basis, only if a same-side position existed at bar i-1's script run; ADX above the regime limit closes the trade at the close. Margin and slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "1FgHp6Cv"
ADX_MAX = 30.0


def check():
    df = bars(8000, seed=435)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    rsi = np_rsi(c, 14)
    _, _, adx = np_dmi(h, l, c, 14)
    atr = np_atr(h, l, c, 14)
    S = dict(ls=np.nan, ss=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        with np.errstate(invalid="ignore"):
            rg = adx[i] < ADX_MAX
            if rg and c[i] <= lo[i] and rsi[i] <= 30 and pos == 0:
                out.append(("entry", 1))
                S["ls"] = lo[i] - atr[i]
            if rg and c[i] >= up[i] and rsi[i] >= 70 and pos == 0:
                out.append(("entry", -1))
                S["ss"] = up[i] + atr[i]
            if pos != 0:
                stop_arr[i] = S["ls"] if pos > 0 else S["ss"]
                if adx[i] > ADX_MAX + 8.0:
                    out.append(("close", pos))
        if pos == 0:
            S["ls"] = S["ss"] = np.nan
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(basis[i - 1]):
            return None
        return basis[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Max ADX to call it 'ranging'": ADX_MAX},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
