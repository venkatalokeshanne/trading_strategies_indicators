"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Adaptive ATR Scalper - Instant & Lock Version
Author       : emretw11
Source URL   : https://www.tradingview.com/script/0NWRtU59-Adaptive-ATR-Scalper-Instant-Lock-Version
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. get_adaptive_trend() is called twice (a heavy and a fast multiplier pair), so it is written out as two methods with the same body
(ta call sites keep their own state per call in Pine). A Wilder-style sum of TR and of +DM / -DM gives DI and an SMA'd DX; the ATR multiplier is the
"rising" one while ADX rises under the threshold, otherwise the "falling" one (and the opposite DI side always uses the falling one). Both trends must agree to
enter; after a position closes no new entry is taken until either trend flips ("waiting for reset"). The fast trend flipping closes the trade; a stop and limit
around the average price are issued while in a position.

Deviations from the original: none.
Not carried over: plots and the reset background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, nz, pmath, ta


class AdaptiveATRScalper(Script):
    TITLE = "Adaptive ATR Scalper - Instant & Lock Version"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=0)
    SOURCE = {"id": "0NWRtU59", "author": "emretw11", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0NWRtU59-Adaptive-ATR-Scalper-Instant-Lock-Version"}

    def init(self):
        self.atr_len = self.input.int(13, "ATR Period")
        self.adx_len = self.input.int(24, "ADX Period")
        self.adx_thresh = self.input.int(43, "ADX Threshold")
        g = "Main Trend"
        self.m1_heavy = self.input.float(4.4, "Main Multiplier (ADX Rising)", step=0.1, group=g)
        self.m2_heavy = self.input.float(9.2, "Main Multiplier (ADX Falling)", step=0.1, group=g)
        g = "Fast Trigger"
        self.m1_fast = self.input.float(1.5, "Fast Multiplier (ADX Rising)", step=0.1, group=g)
        self.m2_fast = self.input.float(3.0, "Fast Multiplier (ADX Falling)", step=0.1, group=g)
        self.long_sl = self.input.float(0.5, "Long SL %", step=0.1)
        self.long_tp = self.input.float(1.2, "Long TP %", step=0.1)
        self.short_sl = self.input.float(0.5, "Short SL %", step=0.1)
        self.short_tp = self.input.float(1.2, "Short TP %", step=0.1)
        self.waiting_for_reset = False

    # shared per-call arithmetic that holds no ta state (histories are keyed by tag)
    def _dm(self, tag):
        hr = self.high - self.high[1]
        lr = -(self.low - self.low[1])
        dm_pos = pmath.max(hr, 0) if hr > lr else 0
        dm_neg = pmath.max(lr, 0) if lr > hr else 0
        s_tr = self.H(tag + "tr")
        s_p = self.H(tag + "p")
        s_n = self.H(tag + "n")
        tr = ta.tr(False)
        v_tr = nz(s_tr[1]) - div(nz(s_tr[1]), self.adx_len) + tr
        v_p = nz(s_p[1]) - div(nz(s_p[1]), self.adx_len) + dm_pos
        v_n = nz(s_n[1]) - div(nz(s_n[1]), self.adx_len) + dm_neg
        s_tr.set(v_tr)
        s_p.set(v_p)
        s_n.set(v_n)
        dip = div(v_p, v_tr) * 100
        din = div(v_n, v_tr) * 100
        dx = div(pmath.abs(dip - din), dip + din) * 100
        return dip, din, dx

    def _finish(self, tag, dip, din, adx_value, rising, atr_v, mult1, mult2):
        m = mult1 if (rising and adx_value < self.adx_thresh) else mult2
        m_up = m if dip >= din else mult2
        m_dn = m if din >= dip else mult2
        t = self.hl2
        up = t - m_up * atr_v
        dn = t + m_dn * atr_v
        h_up, h_dn, h_dir = self.H(tag + "up"), self.H(tag + "dn"), self.H(tag + "dir")
        t_up = pmath.max(up, h_up[1]) if self.close[1] > h_up[1] else up
        t_dn = pmath.min(dn, h_dn[1]) if self.close[1] < h_dn[1] else dn
        if self.close > h_dn[1]:
            d = 1
        elif self.close < h_up[1]:
            d = -1
        else:
            d = nz(h_dir[1], 1)
        h_up.set(t_up)
        h_dn.set(t_dn)
        h_dir.set(d)
        return d, (t_up if d == 1 else t_dn)

    def trend_main(self):
        dip, din, dx = self._dm("m")
        adx_value = ta.sma(dx, self.adx_len)
        atr_v = ta.atr(self.atr_len)
        rising = ta.rising(adx_value, 1)
        return self._finish("m", dip, din, adx_value, rising, atr_v, self.m1_heavy, self.m2_heavy)

    def trend_fast(self):
        dip, din, dx = self._dm("f")
        adx_value = ta.sma(dx, self.adx_len)
        atr_v = ta.atr(self.atr_len)
        rising = ta.rising(adx_value, 1)
        return self._finish("f", dip, din, adx_value, rising, atr_v, self.m1_fast, self.m2_fast)

    def on_bar(self):
        main_dir, main_stop = self.trend_main()
        fast_dir, fast_stop = self.trend_fast()
        st = self.strategy
        pos_prev = self.H("pos")[1]
        self.H("pos").set(st.position_size)
        if not na(pos_prev) and pos_prev != 0 and st.position_size == 0:
            self.waiting_for_reset = True
        main_prev = self.H("maindir")[1]
        fast_prev = self.H("fastdir")[1]
        self.H("maindir").set(main_dir)
        self.H("fastdir").set(fast_dir)
        if (not na(main_prev) and main_dir != main_prev) or (not na(fast_prev) and fast_dir != fast_prev):
            self.waiting_for_reset = False
        long_condition = main_dir == 1 and fast_dir == 1 and st.position_size == 0 and not self.waiting_for_reset
        short_condition = main_dir == -1 and fast_dir == -1 and st.position_size == 0 and not self.waiting_for_reset
        if long_condition:
            st.entry("Long", st.long, comment="Scalp L")
        if short_condition:
            st.entry("Short", st.short, comment="Scalp S")
        if st.position_size > 0 and fast_dir == -1:
            st.close("Long", comment="Exit L (Trend)")
        if st.position_size < 0 and fast_dir == 1:
            st.close("Short", comment="Exit S (Trend)")
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Exit L", "Long", stop=avg * (1 - self.long_sl / 100), limit=avg * (1 + self.long_tp / 100), comment_loss="SL", comment_profit="TP")
        if st.position_size < 0:
            st.exit("Exit S", "Short", stop=avg * (1 + self.short_sl / 100), limit=avg * (1 - self.short_tp / 100), comment_loss="SL", comment_profit="TP")
        self.plot(main_stop, "Main Trend", color=color.green if main_dir == 1 else color.red, linewidth=4)
        self.plot(fast_stop, "Fast Trigger", color=color.lime if fast_dir == 1 else color.orange, linewidth=2)
