"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BIST30 to S&P 500 — ATR Momentum Rider
Author       : not stated
Source URL   : https://www.tradingview.com/script/jd1KSVn7
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, 1 tick of slippage). A setup is the first bar on which HMA(8) > HMA(9) > HMA(20) holds while the slow HMA's 3-bar slope per bar, in ATR units, is above -0.18, inside the start / end year window. A flat strategy buys one contract; with a position open the active lot is closed and the other of the two entry ids ("L-A" / "L-B") buys one contract, so the position is renewed. After the entry fills, the entry price and ATR are recorded; once the high has run 1.5 ATR above the entry a trailing level 5.75 % under the peak high activates, and the lot is closed at the next open when the close falls to that level after at least 4 bars. Past the end year the position is closed.
Deviations from the original: none.
Not carried over: plots and shading.
────────────────────────────────────────────────────────────────────────
"""


from pinelib import NA, Script, div, na, nz, pmath, ta


class AtrMomentumRider(Script):
    TITLE = "BIST30 to S&P 500 — ATR Momentum Rider"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1, pyramiding=2, commission_type="percent", commission_value=0, slippage=1)
    SOURCE = {"id": "jd1KSVn7", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/jd1KSVn7"}

    def init(self):
        i = self.input
        g = "Signal"
        self.fast_len = i.int(8, "HMA-F", minval=2, group=g)
        self.mid_len = i.int(9, "HMA-M", minval=3, group=g)
        self.slow_len = i.int(20, "HMA-S", minval=5, group=g)
        self.atr_len = i.int(14, "ATR-L", minval=2, group=g)
        g = "K1"
        self.k1_a = i.float(1.50, "K1-A · ATR activation", minval=0.25, step=0.25, group=g)
        self.k1_t = i.float(5.75, "K1-T · Peak trail (%)", minval=0.25, step=0.25, group=g)
        self.k1_w = i.int(4, "K1-W · Wait sessions", minval=0, group=g)
        g = "Backtest"
        self.start_year = i.int(2020, "Start year", minval=1970, maxval=2098, group=g)
        self.end_year = i.int(2099, "End year", minval=1971, maxval=2099, group=g)
        self.active_entry_id = "L-A"
        self.reset_on_next_bar = False
        self.reset_order_bar = NA
        self.pending_entry_atr = NA
        self.entry_price = NA
        self.entry_atr = NA
        self.peak_price = NA
        self.k1_trail = NA
        self.k1_active = False
        self.entry_bar = NA

    def _hma(self, source, length):
        half = pmath.max(1, int(pmath.floor(length / 2.0)))
        root = pmath.max(1, int(pmath.round(pmath.sqrt(length))))
        return ta.wma(2.0 * ta.wma(source, half) - ta.wma(source, length), root)

    def on_bar(self):
        st = self.strategy
        close, high = self.close, self.high
        h_regime, h_hmas = self.H("regime"), self.H("hmas")
        regime_1, hmas_3 = h_regime[1], h_hmas[3]
        hma_f = self._hma(close, self.fast_len)
        hma_m = self._hma(close, self.mid_len)
        hma_s = self._hma(close, self.slow_len)
        atr_value = ta.atr(self.atr_len)
        regime = hma_f > hma_m and hma_m > hma_s
        raw_setup = regime and not (regime_1 == 1)
        slope3 = div(div(hma_s - hmas_3, 3), atr_value) if atr_value > 0 else NA
        slope_allowed = (not na(slope3)) and slope3 >= -0.18
        setup = raw_setup and slope_allowed
        year = self.year()
        in_date_range = year >= self.start_year and year <= self.end_year
        pos = st.position_size

        if self.reset_on_next_bar and self.bar_index > self.reset_order_bar and pos > 0:
            self.entry_price = st.position_avg_price
            self.entry_atr = self.pending_entry_atr
            self.peak_price = float(high)
            self.k1_trail = NA
            self.k1_active = False
            self.entry_bar = self.bar_index
            self.reset_on_next_bar = False
        if pos == 0 and not self.reset_on_next_bar:
            self.entry_price = NA
            self.entry_atr = NA
            self.peak_price = NA
            self.k1_trail = NA
            self.k1_active = False
            self.entry_bar = NA
        k1_exit_signal = False
        if pos > 0 and not self.reset_on_next_bar:
            self.peak_price = pmath.max(nz(self.peak_price, float(high)), high)
            if self.k1_active:
                candidate = self.peak_price * (1.0 - self.k1_t / 100.0)
                self.k1_trail = pmath.max(nz(self.k1_trail, candidate), candidate)
                k1_exit_signal = self.bar_index >= self.entry_bar + self.k1_w and close <= self.k1_trail
            mfe_atr = div(self.peak_price - self.entry_price, self.entry_atr) if self.entry_atr > 0 else NA
            if (not self.k1_active) and (not na(mfe_atr)) and mfe_atr >= self.k1_a:
                self.k1_active = True
                self.k1_trail = NA
        if in_date_range and setup and not na(atr_value):
            known_atr = float(atr_value)
            if pos > 0:
                next_id = "L-B" if self.active_entry_id == "L-A" else "L-A"
                st.close(self.active_entry_id, comment="SET-R", immediately=False)
                st.entry(next_id, st.long, comment="SET")
                self.active_entry_id = next_id
            else:
                st.entry(self.active_entry_id, st.long, comment="SET")
            self.pending_entry_atr = known_atr
            self.reset_order_bar = self.bar_index
            self.reset_on_next_bar = True
        elif k1_exit_signal:
            st.close(self.active_entry_id, comment="K1", immediately=False)
        if year > self.end_year and pos > 0:
            st.close(self.active_entry_id, comment="DATE", immediately=False)
        h_regime.set(1 if regime else 0)
        h_hmas.set(hma_s)
