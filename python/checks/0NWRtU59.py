"""Independent check — Adaptive ATR Scalper (0NWRtU59): daily bars, long/short, one position. For each of two (rising, falling) multiplier pairs a plain-loop reference of get_adaptive_trend: TR (na on bar 0),
+DM/-DM, Wilder-style running sums s = nz(s[1]) - nz(s[1])/24 + x, DI = s/sTR*100, DX = |DIP-DIN|/(DIP+DIN)*100, ADX = SMA24(DX); ATR13 (RMA of TR with bar 0 = high-low);
m = rising mult if ADX rose and ADX < 43 else falling mult; up/dn bands off hl2; TUp/TDown ratchet on close[1]; direction by close vs the previous bands, carrying nz(prev,1).
Entry when both trends agree, flat and not waiting; waiting turns on when a position closes and off when either direction changes; the fast trend flipping closes the trade; 0.5% stop / 1.2% limit around the entry price
issued while in a position (work from the next bar). Position size 5% of equity on the pinelib side; margin and slippage off."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0NWRtU59"


def trend(o, h, l, c, m1, m2, adx_len=24, atr_len=13, thr=43):
    n = len(c)
    tr = np.full(n, np.nan)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = np_atr(h, l, c, atr_len)
    nz = lambda x, d=0.0: d if np.isnan(x) else x
    sT = sP = sN = np.nan
    dx = np.full(n, np.nan)
    dip = np.full(n, np.nan)
    din = np.full(n, np.nan)
    for i in range(n):
        if i == 0:
            hr = lr = np.nan
        else:
            hr, lr = h[i] - h[i - 1], -(l[i] - l[i - 1])
        dmp = max(hr, 0) if (hr > lr) else 0
        dmn = max(lr, 0) if (lr > hr) else 0
        sT = nz(sT) - nz(sT) / adx_len + tr[i]
        sP = nz(sP) - nz(sP) / adx_len + dmp
        sN = nz(sN) - nz(sN) / adx_len + dmn
        with np.errstate(invalid="ignore", divide="ignore"):
            dip[i], din[i] = sP / sT * 100, sN / sT * 100
            dx[i] = abs(dip[i] - din[i]) / (dip[i] + din[i]) * 100
    adx = np.full(n, np.nan)
    for i in range(adx_len - 1, n):
        w = dx[i - adx_len + 1:i + 1]
        if not np.isnan(w).any():
            adx[i] = w.mean()
    tup = tdn = np.nan
    d = np.full(n, 0.0)
    prev_d = np.nan
    for i in range(n):
        rising = i > 0 and adx[i] > adx[i - 1]
        m = m1 if (rising and adx[i] < thr) else m2
        mup = m if dip[i] >= din[i] else m2
        mdn = m if din[i] >= dip[i] else m2
        t = (h[i] + l[i]) / 2
        up, dn = t - mup * atr[i], t + mdn * atr[i]
        pc = c[i - 1] if i > 0 else np.nan
        ptup, ptdn = tup, tdn
        tup = max(up, ptup) if (pc > ptup) else up
        tdn = min(dn, ptdn) if (pc < ptdn) else dn
        if c[i] > ptdn:
            d[i] = 1
        elif c[i] < ptup:
            d[i] = -1
        else:
            d[i] = 1 if np.isnan(prev_d) else prev_d
        prev_d = d[i]
    return d


def check():
    df = bars(5000, seed=317)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    md = trend(o, h, l, c, 4.4, 9.2)
    fd = trend(o, h, l, c, 1.5, 3.0)
    st = {"wait": False, "pp": None}
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        if st["pp"] is not None and st["pp"] != 0 and pos == 0:
            st["wait"] = True
        st["pp"] = pos
        if i > 0 and (md[i] != md[i - 1] or fd[i] != fd[i - 1]):
            st["wait"] = False
        out = []
        if pos == 0 and not st["wait"]:
            if md[i] == 1 and fd[i] == 1:
                out.append(("entry", 1))
            if md[i] == -1 and fd[i] == -1:
                out.append(("entry", -1))
        if pos > 0 and fd[i] == -1:
            out.append(("close", 1))
        if pos < 0 and fd[i] == 1:
            out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * (1 - 0.005) if pos > 0 else ep * (1 + 0.005)

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * (1 + 0.012) if pos > 0 else ep * (1 - 0.012)

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
