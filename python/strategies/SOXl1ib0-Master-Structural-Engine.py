"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TOTORO Master Structural Engine v24 (Single Mode)
Author       : tolgahanyildirimx22cw
Source URL   : https://www.tradingview.com/script/SOXl1ib0-Master-Structural-Engine
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A pullback to the EMA100 high / low channel inside a trend above / below the EMA200 (Heikin-Ashi and normal close both beyond it, unbroken since the touch, up to six bars back), with the EMA5 channel beyond the EMA100 channel, the momentum / clean-wick / doji / compression / news-spike filters and the session, enters once until the price has touched the EMA100 channel again; the stop sits at the opposite EMA100 band minus a buffer and the target is a reward / risk multiple. An opposing signal reverses; everything is flattened outside the session. The exit is re-issued every bar with the latest stop / target levels, as in the source.

Deviations from the original: none.
Not carried over: Heikin-Ashi candle painting and plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class MasterStructuralEngine(Script):
    TITLE = "TOTORO Master Structural Engine v24 (Single Mode)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, margin_long=10, margin_short=10)
    SOURCE = {"id": "SOXl1ib0", "author": "tolgahanyildirimx22cw", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SOXl1ib0-Master-Structural-Engine"}

    def init(self):
        i = self.input
        g = "=== Indicator Settings ==="
        self.fast_ema = i.int(5, "Fast EMA Period (White Channel)", group=g)
        self.mid_ema = i.int(100, "Mid EMA Period (Channel Filter)", group=g)
        self.slow_ema = i.int(200, "Slow Macro Trend EMA (Orange Line)", group=g)
        self.rsi_period = i.int(14, "RSI Period", group=g)
        self.atr_period = i.int(14, "ATR Period", group=g)
        g = "=== Strategy Filters ==="
        self.use_momentum = i.bool(True, "Filter 1: Strict Momentum (RSI > 55 / < 45)", group=g)
        self.use_clean_wick = i.bool(True, "Filter 2: Clean Heikin Ashi Wick Filter", group=g)
        self.use_compress = i.bool(True, "Filter 3: Dynamic Compression Gap", group=g)
        self.use_doji = i.bool(True, "Filter 4: Indecision Doji Filter (Absolute)", group=g)
        self.use_news_spike = i.bool(True, "Filter 5: News Spike/ATR Protection", group=g)
        g = "=== Filter Thresholds ==="
        self.use_atr_filter = i.bool(False, "Filter 6: Min/Max ATR Filter Active", group=g)
        self.min_atr = i.float(8.0, "Minimum ATR (Pips/Points)", group=g)
        self.max_atr = i.float(22.0, "Maximum ATR (Pips/Points)", group=g)
        self.compress_gap = i.int(30, "Filter 3: Compression Gap (Points)", group=g)
        self.doji_body_pct = i.float(40.0, "Filter 4: Min Body % of Candle Range", group=g)
        self.atr_mult = i.float(2.5, "Filter 5: ATR Spike Multiplier", group=g)
        self.use_override = i.bool(True, "Smart Override: Deep Pullbacks & Engulfing", group="=== Institutional Overrides ===")
        g = "=== Session Time Filter ==="
        self.time_session = i.session("0900-2200", "Trading Session Time", group=g)
        self.time_zone = i.string("UTC+3", "Session Timezone", group=g)
        g = "=== Risk Management ==="
        self.rr_ratio = i.float(3.0, "Reward/Risk Ratio", step=0.5, group=g)
        self.sl_buffer = i.int(10, "SL Buffer from EMA 100 (Points)", group=g)
        self.ha_open = NA
        self.block_long = False
        self.block_short = False
        self.active_sl = NA
        self.active_tp = NA

    def universal_atr(self, raw_atr):
        ticker = self.syminfo.ticker
        if "XAU" in ticker or "GOLD" in ticker:
            return div(raw_atr, 0.1)
        if "XAG" in ticker or "SILVER" in ticker:
            return div(raw_atr, 0.01)
        if self.syminfo.mintick <= 0.001 and "JPY" in ticker:
            return div(raw_atr, 0.01)
        if self.syminfo.mintick == 0.0001:
            return div(raw_atr, 0.0001)
        return raw_atr

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        ema5_high = ta.ema(high, self.fast_ema)
        ema5_low = ta.ema(low, self.fast_ema)
        ema100_high = ta.ema(high, self.mid_ema)
        ema100_low = ta.ema(low, self.mid_ema)
        ema200 = ta.ema(close, self.slow_ema)
        rsi_val = ta.rsi(close, self.rsi_period)
        raw_atr = ta.atr(self.atr_period)
        univ_atr = self.universal_atr(raw_atr)
        ha_close = (open_ + high + low + close) / 4.0
        hc_h, e1h_h, e1l_h, e2_h, atr_h = self.H("ha_close"), self.H("e100h"), self.H("e100l"), self.H("e200"), self.H("raw_atr")
        hc = [ha_close] + [hc_h[k] for k in range(1, 8)]
        e1h = [ema100_high] + [e1h_h[k] for k in range(1, 8)]
        e1l = [ema100_low] + [e1l_h[k] for k in range(1, 8)]
        e2 = [ema200] + [e2_h[k] for k in range(1, 8)]
        raw_atr_2 = atr_h[2]
        hc_h.set(ha_close)
        e1h_h.set(ema100_high)
        e1l_h.set(ema100_low)
        e2_h.set(ema200)
        atr_h.set(raw_atr)
        ha_open_prev = self.ha_open
        self.ha_open = (open_ + close) / 2.0 if na(ha_open_prev) else (ha_open_prev + hc[1]) / 2.0
        ha_open = self.ha_open
        ha_high = pmath.max(high, pmath.max(ha_open, ha_close))
        ha_low = pmath.min(low, pmath.min(ha_open, ha_close))
        in_session = not na(self.time_fn(None, self.time_session + ":1234567", self.time_zone))
        is_engulf_long = close > high[1]
        is_engulf_short = close < low[1]
        deep_long = deep_short = False
        for k in range(1, 7):
            if low[k] <= e1l[k]:
                deep_long = True
            if high[k] >= e1h[k]:
                deep_short = True
        atr_pass = True
        if self.use_atr_filter:
            if univ_atr < self.min_atr or univ_atr > self.max_atr:
                atr_pass = False
        news_pass = True
        if self.use_news_spike:
            if (high[2] - low[2]) > (raw_atr_2 * self.atr_mult):
                news_pass = False
        doji_pass = True
        if self.use_doji:
            ha_range = ha_high - ha_low
            body = abs(ha_close - ha_open)
            if ha_range == 0 or (div(body, ha_range) * 100.0) < self.doji_body_pct:
                doji_pass = False
        mom_long = mom_short = True
        if self.use_momentum:
            ov_long = self.use_override and (is_engulf_long or deep_long)
            tgt_long = 50.0 if ov_long else 55.0
            if rsi_val < tgt_long or rsi_val < 50.0 or close <= ema5_high or close <= ema100_high or ha_close <= ema5_high or ha_close <= ema100_high:
                mom_long = False
            ov_short = self.use_override and (is_engulf_short or deep_short)
            tgt_short = 50.0 if ov_short else 45.0
            if rsi_val > tgt_short or rsi_val > 50.0 or close >= ema5_low or close >= ema100_low or ha_close >= ema5_low or ha_close >= ema100_low:
                mom_short = False
        wick_long = wick_short = True
        if self.use_clean_wick and not (self.use_override and is_engulf_long):
            if ha_low < ha_open:
                wick_long = False
        if self.use_clean_wick and not (self.use_override and is_engulf_short):
            if ha_high > ha_open:
                wick_short = False
        valid_pb_long = False
        for k in range(1, 7):
            if low[k] <= e1h[k]:
                unbroken = True
                for c in range(k + 1):
                    if close[c] <= e2[c] or hc[c] <= e2[c]:
                        unbroken = False
                if unbroken:
                    valid_pb_long = True
        valid_pb_short = False
        for k in range(1, 7):
            if high[k] >= e1l[k]:
                unbroken = True
                for c in range(k + 1):
                    if close[c] >= e2[c] or hc[c] >= e2[c]:
                        unbroken = False
                if unbroken:
                    valid_pb_short = True
        comp_long = comp_short = True
        if self.use_compress:
            if abs(ema100_high - ema200) < (self.compress_gap * mintick):
                comp_long = False
            if abs(ema100_low - ema200) < (self.compress_gap * mintick):
                comp_short = False
        setup_long = (ema5_high > ema100_high) and atr_pass and news_pass and doji_pass and mom_long and wick_long and valid_pb_long and comp_long
        setup_short = (ema5_low < ema100_low) and atr_pass and news_pass and doji_pass and mom_short and wick_short and valid_pb_short and comp_short
        buy_signal = setup_long and close > ema200 and ha_close > ema200
        sell_signal = setup_short and close < ema200 and ha_close < ema200
        if low <= ema100_high or close < ema200:
            self.block_long = False
        if high >= ema100_low or close > ema200:
            self.block_short = False
        entering_long = buy_signal and (not self.block_long) and in_session
        entering_short = sell_signal and (not self.block_short) and in_session
        if entering_long:
            if st.position_size < 0:
                st.close("Totoro Short")
            self.active_sl = ema100_low - (self.sl_buffer * mintick)
            trade_risk = close - self.active_sl
            self.active_tp = close + (trade_risk * self.rr_ratio)
            st.entry("Totoro Long", st.long)
            self.block_long = True
        if entering_short:
            if st.position_size > 0:
                st.close("Totoro Long")
            self.active_sl = ema100_high + (self.sl_buffer * mintick)
            trade_risk = self.active_sl - close
            self.active_tp = close - (trade_risk * self.rr_ratio)
            st.entry("Totoro Short", st.short)
            self.block_short = True
        if st.position_size > 0 or entering_long:
            st.exit("Exit Long", from_entry="Totoro Long", stop=self.active_sl, limit=self.active_tp)
        if st.position_size < 0 or entering_short:
            st.exit("Exit Short", from_entry="Totoro Short", stop=self.active_sl, limit=self.active_tp)
        if st.position_size == 0 and not entering_long and not entering_short:
            self.active_sl = NA
            self.active_tp = NA
        if not in_session:
            st.close_all(comment="End of Session Flat Override")
            self.block_long = False
            self.block_short = False
            self.active_sl = NA
            self.active_tp = NA
