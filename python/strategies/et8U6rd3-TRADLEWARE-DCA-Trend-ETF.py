"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TRADLEWARE-DCA+Trend ETF
Author       : not stated
Source URL   : https://www.tradingview.com/script/et8U6rd3
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, pyramiding 500, quantities are dollar amounts divided by the close).
A regime flag turns bullish above SMA(200) x (1 + 2 %) and bearish below SMA(200) x (1 - 2 %), holding in between. Inside the date
window: the first bar of every month buys 300 dollars ("dca", also in the bear regime by default); when the regime flips to
bearish the whole position is closed ("crash") and its mark-to-market value is remembered; while bearish after a crash, three
dip-ladder rungs (15 / 20 / 30 % under the running high close) each buy an equal share of 95 % of that value; on the first
bullish bar the remaining lump budget is bought ("lump"). The position is closed on the last historical bar (that order never
fills, so the final position stays open) or after the end date.
Deviations from the original: none.
Not carried over: labels and plots (display only), the pending-close-reason bookkeeping used for the labels.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


class TradlewareDcaTrend(Script):
    TITLE = "TRADLEWARE-DCA+Trend ETF"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=20000, currency="USD", commission_type="percent", commission_value=0.0, slippage=1,
                    pyramiding=500, process_orders_on_close=False)
    SOURCE = {"id": "et8U6rd3", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/et8U6rd3"}

    def init(self):
        i = self.input
        self.start_year = i.int(2020, "Start year", minval=2000, maxval=2099, group="Date Range")
        self.start_month = i.int(1, "Start month", minval=1, maxval=12, group="Date Range")
        self.start_day = i.int(1, "Start day", minval=1, maxval=31, group="Date Range")
        self.end_year = i.int(2099, "End year", minval=2000, maxval=2099, group="Date Range")
        self.end_month = i.int(12, "End month", minval=1, maxval=12, group="Date Range")
        self.end_day = i.int(31, "End day", minval=1, maxval=31, group="Date Range")
        self.sma_len = i.int(200, "SMA Period", minval=20, maxval=500, group="Strategy")
        self.hysteresis_pct = i.float(0.02, "SMA Hysteresis Band (%)", minval=0.0, maxval=0.10, step=0.01, group="Strategy")
        self.dca_amount = i.float(300.0, "Monthly DCA ($)", minval=1.0, group="Strategy")
        self.use_whole_share = i.bool(False, "Whole-Share DCA (bank remainder)", group="Strategy")
        self.lump_pct = i.float(0.95, "Lump Re-entry (%)", minval=0.0, maxval=1.0, step=0.01, group="Strategy")
        self.use_death_cross = i.bool(False, "Death Cross Confirmation", group="Strategy")
        self.dca_always = i.bool(True, "DCA During Bear Regime", group="Strategy")
        self.use_dip_ladder = i.bool(True, "Dip-Ladder Re-entry", group="Dip Ladder")
        self.rung1_pct = i.float(0.15, "Rung 1 (% below ATH)", minval=0.0, maxval=0.9, step=0.05, group="Dip Ladder")
        self.rung2_pct = i.float(0.20, "Rung 2 (% below ATH)", minval=0.0, maxval=0.9, step=0.05, group="Dip Ladder")
        self.rung3_pct = i.float(0.30, "Rung 3 (% below ATH)", minval=0.0, maxval=0.9, step=0.05, group="Dip Ladder")
        # var state
        self.base_regime = False
        self.was_crash = False
        self.lump_fired = False
        self.exited_value = 0.0
        self.rung_fired = [False, False, False]
        self.rung_committed = 0.0
        self.run_high = NA
        self.dca_banked_cash = 0.0

    def on_bar(self):
        close = float(self.close)
        start_date = self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
        end_date = self.timestamp(self.end_year, self.end_month, self.end_day, 23, 59)

        sma200 = ta.sma(self.close, self.sma_len)
        sma50 = ta.sma(self.close, 50)

        if self.hysteresis_pct > 0:
            if close > sma200 * (1 + self.hysteresis_pct):
                self.base_regime = True
            elif close < sma200 * (1 - self.hysteresis_pct):
                self.base_regime = False
        else:
            self.base_regime = close > sma200
        safe_regime = self.base_regime
        if self.use_death_cross:
            safe_regime = safe_regime and (sma50 > sma200)

        month_prev = self.H("month")[1]
        month = self.month()
        self.H("month").set(month)
        is_new_month = month != month_prev            # na previous value on the first bar -> true

        safe_prev = self.H("safe")[1] == 1
        self.H("safe").set(1.0 if safe_regime else 0.0)

        t = float(self.time)
        in_window = t >= start_date and t <= end_date and not self.barstate.islastconfirmedhistory
        if in_window:
            self.run_high = close if self.run_high != self.run_high else max(self.run_high, close)

        st = self.strategy
        crash_event = (not safe_regime) and safe_prev
        if in_window and st.position_size > 0 and crash_event:
            self.exited_value = st.position_size * close
            st.close_all(comment="crash")
            self.was_crash = True
            self.lump_fired = False
            self.rung_fired = [False, False, False]
            self.rung_committed = 0.0

        rung_pcts = [self.rung1_pct, self.rung2_pct, self.rung3_pct]
        active_rungs = sum(1 for p in rung_pcts if p > 0)
        if in_window and self.use_dip_ladder and self.was_crash and not self.lump_fired and not safe_regime \
                and not crash_event and active_rungs > 0:
            per_rung = div(self.exited_value * self.lump_pct, active_rungs)
            for k in range(3):
                if rung_pcts[k] > 0 and not self.rung_fired[k] and close <= self.run_high * (1.0 - rung_pcts[k]):
                    st.entry("rung%d" % (k + 1), st.long, qty=div(per_rung, close), comment="rung%d" % (k + 1))
                    self.rung_fired[k] = True
                    self.rung_committed += per_rung

        if in_window and self.was_crash and not self.lump_fired and safe_regime:
            lump_budget = max(self.exited_value * self.lump_pct - self.rung_committed, 0.0)
            if lump_budget > 0:
                st.entry("lump", st.long, qty=div(lump_budget, close), comment="lump")
            self.lump_fired = True

        if in_window and is_new_month and (self.dca_always or safe_regime):
            if self.use_whole_share:
                dca_available = self.dca_banked_cash + self.dca_amount
                dca_shares = pmath.floor(div(dca_available, close))
                if dca_shares >= 1:
                    st.entry("dca", st.long, qty=dca_shares, comment="dca")
                    self.dca_banked_cash = dca_available - dca_shares * close
                else:
                    self.dca_banked_cash = dca_available
            else:
                st.entry("dca", st.long, qty=div(self.dca_amount, close), comment="dca")

        if self.barstate.islastconfirmedhistory or t > end_date:
            st.close_all(comment="end")

        self.plot(sma200, title="SMA200")
