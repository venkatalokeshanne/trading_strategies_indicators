"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Optimized Keltner Channels Strategy [NIFTY]
Author       : sudhank_naincy
Source URL   : https://www.tradingview.com/script/ek2aOo0g-Optimized-Keltner-Channels-Strategy-NIFTY
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A close crossing the Keltner band (moving average +/- a multiple of the ATR / true range / range) leaves a pending stop entry one tick beyond that bar's high / low, optionally filtered by the 200 EMA side and a Monday-Friday session; the pending order is cancelled once the close returns to the average or the level is reached. Optional extras: a wide ATR stop from the trade's entry price and an exit when the close crosses back through the middle band.

Deviations from the original: none.
Not carried over: none (the strategy has no display-only code besides the plots, which are omitted).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class OptimizedKeltner(Script):
    TITLE = "Optimized Keltner Channels Strategy [NIFTY]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "ek2aOo0g", "author": "sudhank_naincy", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ek2aOo0g-Optimized-Keltner-Channels-Strategy-NIFTY"}

    def init(self):
        i = self.input
        g = "Original Keltner Settings"
        self.length = i.int(20, "KC Length", minval=1, group=g)
        self.mult = i.float(2.0, "Multiplier", group=g)
        self.src = i.source(self.close, "Source", group=g)
        self.exp = i.bool(True, "Use Exponential MA", group=g)
        self.bands_style = i.string("Average True Range", "Bands Style", options=["Average True Range", "True Range", "Range"], group=g)
        self.atr_length = i.int(10, "ATR Length", group=g)
        g = "Optional Trend & Time Filters"
        self.use_trend_filter = i.bool(False, "Use 200 EMA Trend Filter", group=g)
        self.ema_period = i.int(200, "EMA Filter Period", group=g)
        self.use_time_filter = i.bool(False, "Use Time Session Filter", group=g)
        self.session_hours = i.string("0930-1445", "Trading Session (Exchange Time)", group=g)
        g = "Optional Exits & Stops"
        self.exit_on_mid_band = i.bool(False, "Exit on Mid-Band Close", group=g)
        self.use_atr_stop = i.bool(False, "Use Wide ATR Stop Loss", group=g)
        self.atr_stop_mult = i.float(3.0, "ATR Stop Multiplier", group=g)
        self.bprice = 0.0
        self.sprice = 0.0
        self.cross_b_cond = False
        self.cross_s_cond = False
        self.long_stop_price = NA
        self.short_stop_price = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        s_ = ta.sma(self.src, self.length)
        e_ = ta.ema(self.src, self.length)
        ma = e_ if self.exp else s_
        tr_v = ta.tr(True)
        atr_v = ta.atr(self.atr_length)
        rma_rng = ta.rma(high - low, self.length)
        rangema = tr_v if self.bands_style == "True Range" else (atr_v if self.bands_style == "Average True Range" else rma_rng)
        upper = ma + rangema * self.mult
        lower = ma - rangema * self.mult
        ema_filter = ta.ema(close, self.ema_period)
        trend_long_allowed = (not self.use_trend_filter) or close > ema_filter
        trend_short_allowed = (not self.use_trend_filter) or close < ema_filter
        session_string = self.session_hours + ":23456"
        time_allowed = (not self.use_time_filter) or not na(self.time_fn(None, session_string))
        long_allowed = trend_long_allowed and time_allowed
        short_allowed = trend_short_allowed and time_allowed
        cross_upper = ta.crossover(self.src, upper)
        cross_lower = ta.crossunder(self.src, lower)
        if cross_upper and long_allowed:
            self.bprice = high + mintick
        if cross_lower and short_allowed:
            self.sprice = low - mintick
        if cross_upper and long_allowed:
            self.cross_b_cond = True
        if cross_lower and short_allowed:
            self.cross_s_cond = True
        cancel_b = self.cross_b_cond and (self.src < ma or high >= self.bprice)
        cancel_s = self.cross_s_cond and (self.src > ma or low <= self.sprice)
        if cancel_b:
            st.cancel("KltChLE")
            self.cross_b_cond = False
        if cross_upper and long_allowed:
            st.entry("KltChLE", st.long, stop=self.bprice, comment="KltChLE")
        if cancel_s:
            st.cancel("KltChSE")
            self.cross_s_cond = False
        if cross_lower and short_allowed:
            st.entry("KltChSE", st.short, stop=self.sprice, comment="KltChSE")
        atr_val = ta.atr(self.atr_length)
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        is_new_long = st.position_size > 0 and pos_prev <= 0
        is_new_short = st.position_size < 0 and pos_prev >= 0
        if st.position_size > 0:
            if is_new_long or na(self.long_stop_price):
                entry_price = st.opentrades_entry_price(0) if st.opentrades_entry_price(0) > 0 else close
                self.long_stop_price = entry_price - (atr_val * self.atr_stop_mult)
        else:
            self.long_stop_price = NA
        if st.position_size < 0:
            if is_new_short or na(self.short_stop_price):
                entry_price = st.opentrades_entry_price(0) if st.opentrades_entry_price(0) > 0 else close
                self.short_stop_price = entry_price + (atr_val * self.atr_stop_mult)
        else:
            self.short_stop_price = NA
        if self.use_atr_stop:
            if st.position_size > 0:
                st.exit("SL Long", from_entry="KltChLE", stop=self.long_stop_price, comment="ATR Stop Loss")
            if st.position_size < 0:
                st.exit("SL Short", from_entry="KltChSE", stop=self.short_stop_price, comment="ATR Stop Loss")
        if self.exit_on_mid_band:
            cross_dn_mid = ta.crossunder(close, ma)
            cross_up_mid = ta.crossover(close, ma)
            if st.position_size > 0 and cross_dn_mid:
                st.close("KltChLE", comment="Exit Mid-Band")
            if st.position_size < 0 and cross_up_mid:
                st.close("KltChSE", comment="Exit Mid-Band")
