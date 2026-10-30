"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SPY Wheel Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/KKGMELzx
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (daily chart, orders at the bar's close: process_orders_on_close). 100 shares are bought on the start date; a covered-call "assignment" closes the position when the close exceeds the strike set on the previous close (1 DTE: 1.25 % above, rounded up) or, in a high-VIX regime (VIX >= 25), the same bar's strike 3 % above, and only if the strike is at or above the cost basis; the shares are bought again at once (or through a cash-secured-put limit order when all gates pass, when that mode is on). Three closes in a row under the 200 SMA trigger the emergency regime exit; the shares are bought again once the close is back above the SMA.
VIX comes from request.security("VIX", chart timeframe, close); without VIX data the engine raises (the source would give na).
`timestamp("2023-04-03")` is read as UTC midnight.
Deviations from the original: none. Option premiums are not modelled by the source either.
Not carried over: plots, background colours and the gate table.
────────────────────────────────────────────────────────────────────────
"""


from pinelib import NA, Script, na, pmath, ta


class SpyWheel(Script):
    TITLE = "SPY Wheel Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=70000, default_qty_type="fixed", default_qty_value=100, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "KKGMELzx", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/KKGMELzx"}

    def init(self):
        i = self.input
        g = "CC Settings"
        self.cc_pct_norm = i.float(1.25, "CC Strike % OTM — Normal VIX", minval=0.25, maxval=5.0, step=0.25, group=g) / 100
        self.cc_pct_vix = i.float(3.00, "CC Strike % OTM — High VIX", minval=0.50, maxval=8.0, step=0.25, group=g) / 100
        g = "Re-entry Settings"
        self.use_csp = i.bool(False, "Use CSP re-entry (uncheck = instant re-entry at open)", group=g)
        self.csp_pct = i.float(1.50, "CSP Strike % OTM (only if CSP enabled)", minval=0.25, maxval=5.0, step=0.25, group=g) / 100
        g = "Gate Settings"
        self.vix_thresh = i.float(25.0, "VIX Gate Threshold", minval=10.0, maxval=50.0, step=1.0, group=g)
        self.rsi_lo = i.float(75.0, "RSI Block Zone — Low", minval=50.0, maxval=89.0, step=1.0, group=g)
        self.rsi_hi = i.float(85.0, "RSI Block Zone — High", minval=51.0, maxval=95.0, step=1.0, group=g)
        self.sma_len = i.int(200, "Long MA Length (SMA)", minval=50, maxval=500, group=g)
        self.ema_len = i.int(20, "Short MA Length (EMA)", minval=5, maxval=100, group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=5, maxval=30, group=g)
        self.use_vwap = i.bool(False, "Gate 5: VWAP (uncheck = disabled)", group=g)
        g = "Emergency Exit"
        self.sma_days = i.int(3, "200 SMA Breach Days to Exit", minval=1, maxval=10, group=g)
        self.macro_block = i.bool(False, "Block Today — FOMC / CPI / NFP", group="Macro Filter")
        self.start_dt = i.time(self.timestamp("UTC", 2023, 4, 3), "Strategy Start Date", group="Backtest")
        self.cost_basis = NA
        self.cc_str_live = NA
        self.sma_ct = 0
        self.exited = False
        self.start_bar = NA

    def on_bar(self):
        st = self.strategy
        close, time = self.close, self.time
        h_pos, h_cc = self.H("pos"), self.H("cc")
        pos_prev, cc_prev = h_pos[1], h_cc[1]
        time_1 = time[1]
        sma200 = ta.sma(close, self.sma_len)
        ema20 = ta.ema(close, self.ema_len)
        rsi_val = ta.rsi(close, self.rsi_len)
        vwap_v = ta.vwap(self.hlc3)
        vix_val = self.security("VIX", self.timeframe.period, lambda v: float(v.close))
        hi_vix = (not na(vix_val)) and vix_val >= self.vix_thresh
        pos = st.position_size
        holding = pos >= 100
        g1 = close > sma200
        g2 = close > ema20
        g3 = self.rsi_lo > self.rsi_hi or not (rsi_val >= self.rsi_lo and rsi_val <= self.rsi_hi)
        g4 = (not na(vix_val)) and vix_val < self.vix_thresh
        g5 = (close >= vwap_v) if self.use_vwap else True
        g6 = not self.macro_block
        csp_ok = g1 and g2 and g3 and g4 and g5 and g6
        reenter_bar = False
        self.sma_ct = (self.sma_ct + 1 if close < sma200 else 0) if holding else 0
        regime_break = holding and self.sma_ct >= self.sma_days

        if time >= self.start_dt and (not na(time_1)) and time_1 < self.start_dt and pos == 0:
            st.entry("LONG", st.long, qty=100, comment="Initial buy")
            self.start_bar = self.bar_index
        if pos >= 100 and (not na(pos_prev)) and pos_prev < 100:
            if st.opentrades > 0:
                self.cost_basis = st.opentrades_entry_price(st.opentrades - 1)
        if regime_break and not self.exited:
            st.close_all(comment="REGIME EXIT")
            st.cancel_all()
            self.cost_basis = NA
            self.cc_str_live = NA
            self.exited = True
        if self.exited and not holding and close > sma200 and time >= self.start_dt:
            st.entry("LONG", st.long, qty=100, comment="Re-entry — 200 SMA reclaimed")
            self.exited = False
            reenter_bar = True
        if holding and (not regime_break) and time >= self.start_dt and not na(self.cost_basis):
            pct = self.cc_pct_vix if hi_vix else self.cc_pct_norm
            new_strike = float(pmath.ceil(close * (1.0 + pct)))
            check_strike = new_strike if hi_vix else cc_prev
            if (not na(check_strike)) and close > check_strike and check_strike >= self.cost_basis:
                st.close_all(comment="CC assigned")
                self.cc_str_live = NA
            else:
                self.cc_str_live = new_strike if new_strike >= self.cost_basis else NA
        csp_eligible = (not holding) and (not self.exited) and (not reenter_bar) and (not na(self.start_bar)) and self.bar_index > self.start_bar and time >= self.start_dt
        if csp_eligible:
            if not self.use_csp:
                st.entry("LONG", st.long, qty=100, comment="Re-entry at open")
            else:
                st.cancel("LONG")
                if csp_ok:
                    csp_strike = float(pmath.floor(self.open * (1.0 - self.csp_pct)))
                    st.entry("LONG", st.long, qty=100, limit=csp_strike, comment="CSP")
        h_pos.set(pos)
        h_cc.set(self.cc_str_live)
