"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Universal Strategy Feed
Author       : Options360
Source URL   : https://www.tradingview.com/script/gU6RDuh5-Universal-Strategy-Feed
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A generic signal feed: seven signal modes (pulse, sign cross, level cross, two-source cross, trigger sources, three-source logic, volume spike with candle colour) turn external
or chart sources into long / short signals that alternate (a signal only fires when it differs from the last one) and reverse the position. Exits: none (signal reversal), percent TP / SL around the average price, ATR TP / SL around the average
price (the ATR is sampled only on signal bars, as in the original), or a close on the TP / SL feed pulse.

Deviations from the original: none.
Not carried over: nothing (the script has no plots).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, ta


class UniversalStrategyFeed(Script):
    TITLE = "Universal Strategy Feed"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=1000000, margin_long=100, margin_short=100, commission_type="percent", commission_value=0.05,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "gU6RDuh5", "author": "Options360", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gU6RDuh5-Universal-Strategy-Feed"}

    def init(self):
        i = self.input
        g = "Signal"
        self.mode = i.string("Pulse (+ long / - short)", "Signal Mode", options=["Pulse (+ long / - short)", "Sign cross (over level)", "Level cross (up/down)", "Two sources cross",
                                                                             "Two trigger sources", "Three sources", "Volume (magnitude + candle)"], group=g)
        self.src_a = i.source(self.ohlc4, "Source A  (primary / long)", group=g)
        self.src_b = i.source(self.ohlc4, "Source B  (two-source modes / short)", group=g)
        self.src_3 = i.source(self.ohlc4, "Source C  (third source, 3-source mode)", group=g)
        self.level = i.float(0, "Level / midline (Pulse, Sign cross)", group=g)
        self.up_lvl = i.float(0, "Up level (Level cross)", group=g)
        self.dn_lvl = i.float(0, "Down level (Level cross)", group=g)
        self.t3logic = i.string("A above both B & C", "3-Source Logic", options=["A above both B & C", "A crosses B, filter C", "A>C long / B>C short"], group=g)
        self.filt = i.float(0, "3-Source filter level (A crosses B, filter C)", group=g)
        self.vol_ma_len = i.int(200, "Volume MA Length (Volume mode; 0 = use Source B as threshold)", minval=0, group=g)
        self.vol_ma_type = i.string("SMA", "Volume MA Type (Volume mode)", options=["SMA", "EMA", "WMA", "RMA"], group=g)
        self.invert = i.bool(False, "Invert long / short", group=g)
        self.qty = i.float(1, "Contracts per trade", minval=0.0, step=0.1, group="Sizing")
        g = "Exits"
        self.level_mode = i.string("Signal", "TP/SL Method", options=["Percent", "ATR", "Signal", "Feed (external TP/SL)"], group=g)
        self.reverse_on_opp = i.bool(True, "Reverse on opposite signal", group=g)
        self.tp_perc = i.float(10, "Take Profit %", step=0.1, group=g) / 100.0
        self.sl_perc = i.float(2.5, "Stop Loss %", step=0.1, group=g) / 100.0
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_tp = i.float(3, "ATR TP Multiplier", step=0.1, group=g)
        self.atr_sl = i.float(2, "ATR SL Multiplier", step=0.1, group=g)
        self.tp_feed = i.source(self.ohlc4, "TP feed  (Feed mode -> e.g. AI.1U: Take Profit Hit)", group=g)
        self.sl_feed = i.source(self.ohlc4, "SL feed  (Feed mode -> e.g. AI.1U: Stop Loss Hit)", group=g)
        g = "Filters"
        self.use_dates = i.bool(False, "Limit by date range", group=g)
        self.start_t = i.time(self.timestamp("UTC", 2020, 1, 1, 0, 0), "Start", group=g)
        self.end_t = i.time(self.timestamp("UTC", 2099, 1, 1, 0, 0), "End", group=g)
        self.last_sig = 0
        self.entry_atr = NA

    def ma(self, s, length, t):
        if t == "SMA":
            return ta.sma(s, length)
        if t == "EMA":
            return ta.ema(s, length)
        if t == "WMA":
            return ta.wma(s, length)
        if t == "RMA":
            return ta.rma(s, length)
        return NA

    def on_bar(self):
        st = self.strategy
        close, open_ = self.close, self.open
        a, b, c3 = self.src_a, self.src_b, self.src_3
        long3 = False
        short3 = False
        if self.t3logic == "A above both B & C":
            long3 = a > b and a > c3
            short3 = a < b and a < c3
        elif self.t3logic == "A crosses B, filter C":
            long3 = ta.crossover(a, b) and c3 > self.filt
        elif self.t3logic == "A>C long / B>C short":
            long3 = a > c3
        if self.t3logic == "A crosses B, filter C":
            short3 = ta.crossunder(a, b) and c3 < self.filt
        elif self.t3logic == "A>C long / B>C short":
            short3 = b > c3
        vol_thresh = self.ma(self.volume, self.vol_ma_len, self.vol_ma_type) if self.vol_ma_len > 0 else b
        vol_long = self.volume > vol_thresh and close >= open_
        vol_short = self.volume > vol_thresh and close < open_
        m = self.mode
        if m == "Pulse (+ long / - short)":
            long_raw = a > self.level
        elif m == "Sign cross (over level)":
            long_raw = ta.crossover(a, self.level)
        elif m == "Level cross (up/down)":
            long_raw = ta.crossover(a, self.up_lvl)
        elif m == "Two sources cross":
            long_raw = ta.crossover(a, b)
        elif m == "Two trigger sources":
            long_raw = (not na(a)) and a != 0
        elif m == "Three sources":
            long_raw = long3
        elif m == "Volume (magnitude + candle)":
            long_raw = vol_long
        else:
            long_raw = False
        if m == "Pulse (+ long / - short)":
            short_raw = a < self.level
        elif m == "Sign cross (over level)":
            short_raw = ta.crossunder(a, self.level)
        elif m == "Level cross (up/down)":
            short_raw = ta.crossunder(a, self.dn_lvl)
        elif m == "Two sources cross":
            short_raw = ta.crossunder(a, b)
        elif m == "Two trigger sources":
            short_raw = (not na(b)) and b != 0
        elif m == "Three sources":
            short_raw = short3
        elif m == "Volume (magnitude + candle)":
            short_raw = vol_short
        else:
            short_raw = False
        go_long = short_raw if self.invert else long_raw
        go_short = long_raw if self.invert else short_raw
        in_window = (not self.use_dates) or (self.time >= self.start_t and self.time <= self.end_t)
        buy = go_long and in_window and self.last_sig != 1
        sell = go_short and in_window and self.last_sig != -1 and not buy
        if buy:
            self.last_sig = 1
        if sell:
            self.last_sig = -1
        flat = st.position_size == 0
        if buy or sell:
            self.entry_atr = ta.atr(self.atr_len)
        if buy and (self.reverse_on_opp or flat):
            st.entry("Long", st.long, qty=self.qty)
        if sell and (self.reverse_on_opp or flat):
            st.entry("Short", st.short, qty=self.qty)
        if (self.level_mode == "Percent" or self.level_mode == "ATR") and st.position_size != 0:
            avg = st.position_avg_price
            if st.position_size > 0:
                tp = avg * (1 + self.tp_perc) if self.level_mode == "Percent" else avg + self.entry_atr * self.atr_tp
                sl = avg * (1 - self.sl_perc) if self.level_mode == "Percent" else avg - self.entry_atr * self.atr_sl
                st.exit("L x", "Long", limit=tp, stop=sl)
            else:
                tp = avg * (1 - self.tp_perc) if self.level_mode == "Percent" else avg - self.entry_atr * self.atr_tp
                sl = avg * (1 + self.sl_perc) if self.level_mode == "Percent" else avg + self.entry_atr * self.atr_sl
                st.exit("S x", "Short", limit=tp, stop=sl)
        if self.level_mode == "Feed (external TP/SL)":
            tf_h, sf_h = self.H("tpf"), self.H("slf")
            tp_prev, sl_prev = nz(tf_h[1]), nz(sf_h[1])
            tf_h.set(self.tp_feed)
            sf_h.set(self.sl_feed)
            tp_fire = self.tp_feed != 0 and tp_prev == 0
            sl_fire = self.sl_feed != 0 and sl_prev == 0
            if (tp_fire or sl_fire) and not buy and not sell and st.position_size != 0:
                st.close_all(comment="TP feed" if tp_fire else "SL feed")
