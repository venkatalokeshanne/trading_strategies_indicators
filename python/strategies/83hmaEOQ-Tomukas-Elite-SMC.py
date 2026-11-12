"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Tomukas Elite SMC
Author       : not stated
Source URL   : https://www.tradingview.com/script/83hmaEOQ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, 10 % of equity). A liquidity sweep of the latest 5-bar swing low (high) with a rejection candle (close in the upper / lower half, wick at least 1.5 x the opposite part) starts a setup; its market-structure shift is a close beyond the other swing (that must be beyond the sweep extreme) and, on that bar, a fair-value gap (low over the high two bars back, or the mirror) is stored. While a gap is stored a long (short) is entered when the bar trades into the gap, the 200 EMA agrees, ADX(14) (the source's own formula) is over 20 and the bar is inside the 08:00-17:00 UTC-4 session; the gap is dropped when price closes through it. The stop is the sweep extreme; at 1 R (the first target) half the position is taken and the stop moves to break-even; the rest closes on an opposite sweep or when the close crosses the EMA.
Deviations from the original: none.
Not carried over: labels, lines, boxes (including the minimum-size test, which only decides whether a box is drawn), the dashboard.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class TomukasEliteSmc(Script):
    TITLE = "Tomukas Elite SMC"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "83hmaEOQ", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/83hmaEOQ"}

    def init(self):
        i = self.input
        g = "Trend & Filter Settings"
        self.ema_len = i.int(200, "EMA Length", group=g)
        self.adx_len = i.int(14, "ADX Length", group=g)
        self.adx_thresh = i.int(20, "ADX Threshold", group=g)
        g = "SMC Settings"
        self.swing_len = i.int(5, "Swing Length", group=g)
        self.fvg_min_pct = i.float(0.1, "Min FVG Size (%)", step=0.05, group=g)
        g = "Session Settings"
        self.session_t = i.string("0800-1700", "Trading Session (London + NY)", group=g)
        self.tz_offset = i.string("UTC-4", "Timezone", group=g)
        self.risk_reward = i.float(1.0, "TP1 Risk/Reward", group="Risk Management")
        self.last_ph = NA
        self.last_pl = NA
        self.sweep_type = 0
        self.sweep_extremum = NA
        self.mss_confirmed = False
        self.fvg_top = NA
        self.fvg_bot = NA
        self.entry_price = NA
        self.sl_price = NA
        self.tp1_price = NA
        self.tp1_hit = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        high_1, low_1, high_2, low_2 = self.high[1], self.low[1], self.high[2], self.low[2]
        ema200 = ta.ema(close, self.ema_len)
        trend = 1 if close > ema200 else -1 if close < ema200 else 0
        tr = ta.rma(ta.tr(False), self.adx_len)
        plus = ta.rma(pmath.max(high - high_1, 0), self.adx_len)
        minus = ta.rma(pmath.max(low_1 - low, 0), self.adx_len)
        plus_di = 100 * div(plus, tr)
        minus_di = 100 * div(minus, tr)
        dx = 100 * div(abs(plus_di - minus_di), 1 if plus_di + minus_di == 0 else plus_di + minus_di)
        adx = ta.rma(dx, self.adx_len)
        is_trending = adx > self.adx_thresh
        in_session = self.time_in_session(self.session_t, self.tz_offset)
        ph = ta.pivothigh(high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_ph = float(ph)
        if not na(pl):
            self.last_pl = float(pl)
        mid = (high + low) / 2
        is_bullish_rejection = close > mid and (close - low) > (high - close) * 1.5
        sweep_low = (not na(self.last_pl)) and low < self.last_pl and close > self.last_pl and is_bullish_rejection
        is_bearish_rejection = close < mid and (high - close) > (close - low) * 1.5
        sweep_high = (not na(self.last_ph)) and high > self.last_ph and close < self.last_ph and is_bearish_rejection
        if sweep_low:
            self.sweep_type = 1
            self.sweep_extremum = float(low)
        if sweep_high:
            self.sweep_type = -1
            self.sweep_extremum = float(high)
        if sweep_low or sweep_high:
            self.mss_confirmed = False
            self.fvg_top = NA
            self.fvg_bot = NA
        if self.sweep_type == 1 and not self.mss_confirmed:
            if close > self.last_ph and self.last_ph > self.sweep_extremum:
                self.mss_confirmed = True
                if low > high_2:
                    self.fvg_top = float(low)
                    self.fvg_bot = float(high_2)
        if self.sweep_type == -1 and not self.mss_confirmed:
            if close < self.last_pl and self.last_pl < self.sweep_extremum:
                self.mss_confirmed = True
                if high < low_2:
                    self.fvg_top = float(low_2)
                    self.fvg_bot = float(high)
        setup_valid = self.mss_confirmed and (not na(self.fvg_top)) and is_trending and in_session
        long_entry = setup_valid and self.sweep_type == 1 and trend == 1 and low <= self.fvg_top and low >= self.fvg_bot
        short_entry = setup_valid and self.sweep_type == -1 and trend == -1 and high >= self.fvg_bot and high <= self.fvg_top
        if not na(self.fvg_top):
            if self.sweep_type == 1 and close < self.fvg_bot:
                self.fvg_top = NA
                self.fvg_bot = NA
            if self.sweep_type == -1 and close > self.fvg_top:
                self.fvg_top = NA
                self.fvg_bot = NA
        pos = st.position_size
        if long_entry and pos == 0:
            self.entry_price = float(close)
            self.sl_price = self.sweep_extremum
            self.tp1_price = self.entry_price + (self.entry_price - self.sl_price) * self.risk_reward
            st.entry("Buy", st.long)
            self.fvg_top = NA
        if short_entry and pos == 0:
            self.entry_price = float(close)
            self.sl_price = self.sweep_extremum
            self.tp1_price = self.entry_price - (self.sl_price - self.entry_price) * self.risk_reward
            st.entry("Sell", st.short)
            self.fvg_top = NA
        if pos > 0:
            if (not self.tp1_hit) and high >= self.tp1_price:
                self.tp1_hit = True
                self.sl_price = self.entry_price
                st.exit("TP1", "Buy", qty_percent=50, limit=self.tp1_price)
            st.exit("SL/BE", "Buy", stop=self.sl_price)
            if self.sweep_type == -1 or close < ema200:
                st.close("Buy", comment="Runner Exit")
        if pos < 0:
            if (not self.tp1_hit) and low <= self.tp1_price:
                self.tp1_hit = True
                self.sl_price = self.entry_price
                st.exit("TP1", "Sell", qty_percent=50, limit=self.tp1_price)
            st.exit("SL/BE", "Sell", stop=self.sl_price)
            if self.sweep_type == 1 or close > ema200:
                st.close("Sell", comment="Runner Exit")
        if pos == 0:
            self.tp1_hit = False
            self.entry_price = NA
