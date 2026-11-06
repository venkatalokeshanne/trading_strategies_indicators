"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Institutional Flow [STRICT ANCHOR + PRO]
Author       : QueenBee11_
Source URL   : https://www.tradingview.com/script/j6kU7okA-Institutional-Flow-STRATEGY
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A break of structure (close crossing over the last confirmed pivot high / under the last pivot low, pivots of 10 bars each side) with a fair-value gap (low over the high two bars back / high under the low two bars back) in the last 5 bars and the price on the right side of the 290 SMA and 200 EMA,
while the script's own "trade active" flag is off, enters one unit with a fixed stop distance (pips x pip size) and a take-profit at the risk-reward multiple (plus an optional tick buffer). The flag is maintained by the script from the bar's high / low: break-even (stop to the entry) once the favourable move reaches the BE multiple,
and a stop or target touch clears the flag and closes both entry ids at the next open (market).
Deviations from the original: none.
Not carried over: the boxes, lines, labels, win / loss counters and the statistics table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class InstitutionalFlow(Script):
    TITLE = "Institutional Flow [STRICT ANCHOR + PRO]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = {}
    SOURCE = {"id": "j6kU7okA", "author": "QueenBee11_", "licence": "not stated", "url": "https://www.tradingview.com/script/j6kU7okA-Institutional-Flow-STRATEGY"}

    def init(self):
        i = self.input
        g = "── Signal Engine ──"
        self.swing_len = i.int(10, "Structure Lookback", group=g)
        self.fvg_lookback = i.int(5, "FVG Lookback Window", group=g)
        g = "── Trend Filter (Both Must Match) ──"
        self.use_ma_filter = i.bool(True, "Enable MA Filter", group=g)
        self.sma_length = i.int(290, "SMA Length", group=g)
        self.ema_length = i.int(200, "EMA Length", group=g)
        g = "── Risk Management ──"
        self.fixed_sl_pips = i.float(20.0, "Fixed SL (Pips/Points)", group=g)
        self.rr_ratio = i.float(2.0, "Risk:Reward Ratio", group=g)
        self.tp_tick_offset = i.int(0, "TP Ticks Beyond Line", minval=0, group=g)
        g = "── Break Even ──"
        self.use_be = i.bool(True, "Enable Break Even", group=g)
        self.be_at_rr = i.float(1.0, "Trigger BE at RR", minval=0.1, step=0.1, group=g)
        self.last_high = NA
        self.last_low = NA
        self.t_active = False
        self.be_moved = False
        self.t_ent = NA
        self.t_sl = NA
        self.t_tp = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        multiplier = 10.0 if (mintick == 0.00001 or mintick == 0.001) else 1.0
        pip_size = mintick * multiplier
        sl_dist = self.fixed_sl_pips * pip_size
        tp_dist = sl_dist * self.rr_ratio
        tp_buffer = self.tp_tick_offset * mintick
        sma_val = ta.sma(close, self.sma_length)
        ema_val = ta.ema(close, self.ema_length)
        trend_bull = (not self.use_ma_filter) or (close > sma_val and close > ema_val)
        trend_bear = (not self.use_ma_filter) or (close < sma_val and close < ema_val)
        high_ = ta.pivothigh(high, self.swing_len, self.swing_len)
        low_ = ta.pivotlow(low, self.swing_len, self.swing_len)
        if not (high_ != high_):
            self.last_high = high_
        if not (low_ != low_):
            self.last_low = low_
        bull_bos = ta.crossover(close, self.last_high)
        bear_bos = ta.crossunder(close, self.last_low)
        bull_fvg = low > self.high[2]
        bear_fvg = high < self.low[2]
        has_recent_bull_fvg = ta.barssince(bull_fvg) <= self.fvg_lookback
        has_recent_bear_fvg = ta.barssince(bear_fvg) <= self.fvg_lookback
        long_signal = bull_bos and has_recent_bull_fvg and trend_bull
        short_signal = bear_bos and has_recent_bear_fvg and trend_bear
        if (long_signal or short_signal) and not self.t_active:
            self.t_active = True
            self.be_moved = False
            self.t_ent = float(close)
            if long_signal:
                st.entry("Long", st.long)
            if short_signal:
                st.entry("Short", st.short)
            self.t_sl = self.t_ent - sl_dist if long_signal else self.t_ent + sl_dist
            self.t_tp = self.t_ent + tp_dist + tp_buffer if long_signal else self.t_ent - tp_dist - tp_buffer
        if self.t_active:
            is_long = self.t_tp > self.t_sl
            if self.use_be and not self.be_moved:
                trigger_price = self.t_ent + (sl_dist * self.be_at_rr) if is_long else self.t_ent - (sl_dist * self.be_at_rr)
                if (is_long and high >= trigger_price) or ((not is_long) and low <= trigger_price):
                    self.t_sl = self.t_ent
                    self.be_moved = True
            if (is_long and low <= self.t_sl) or ((not is_long) and high >= self.t_sl):
                self.t_active = False
                st.close("Long", comment="SL Hit")
                st.close("Short", comment="SL Hit")
            elif (is_long and high >= self.t_tp) or ((not is_long) and low <= self.t_tp):
                self.t_active = False
                st.close("Long", comment="TP Hit")
                st.close("Short", comment="TP Hit")
