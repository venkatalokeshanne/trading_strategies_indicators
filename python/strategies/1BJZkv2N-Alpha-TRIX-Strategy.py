"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Alpha TRIX Strategy
Author       : BVLabs
Source URL   : https://www.tradingview.com/script/1BJZkv2N-Alpha-TRIX-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A TRIX (rate of change of the triple-smoothed EMA) zero-line cross, inside a trending market (Choppiness below its threshold and ADX above its minimum) and
with the EMA200 trend, enters; an opposite signal reverses when allowed. The ATR-based target and stop distances are locked at the entry signal and, while in a position, placed around the
average price.

Deviations from the original: none.
Not carried over: the trend EMA plot and the signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class AlphaTrix(Script):
    TITLE = "Alpha TRIX Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=10000, commission_type="percent", commission_value=0,
                    pyramiding=0, margin_long=0, margin_short=0, slippage=2)
    SOURCE = {"id": "1BJZkv2N", "author": "BVLabs", "licence": "not stated",
              "url": "https://www.tradingview.com/script/1BJZkv2N-Alpha-TRIX-Strategy"}

    def init(self):
        g = "Main Strategy Settings"
        self.trade_direction = self.input.string("Both", "Trade Direction", options=["Long", "Short", "Both"], group=g)
        self.allow_reversal = self.input.bool(True, "Reverse Position on Opposite Signal", group=g)
        g = "Entry Filters (CHOP & ADX)"
        self.chop_len = self.input.int(14, "Choppiness Length", minval=1, group=g)
        self.chop_thresh = self.input.float(50.0, "Choppiness Threshold (<)", group=g)
        self.adx_len = self.input.int(7, "ADX Length", minval=1, group=g)
        self.adx_min = self.input.float(20.0, "ADX Minimum Threshold (>)", group=g)
        g = "Trend Filter (EMA)"
        self.use_trend_filter = self.input.bool(True, "Only trade with the trend", group=g)
        self.trend_len = self.input.int(200, "Trend EMA Length", minval=1, group=g)
        g = "Trigger Settings (TRIX)"
        self.trix_len = self.input.int(8, "TRIX Length", minval=1, group=g)
        self.min_trix_slope = self.input.float(0.0, "Min TRIX Slope at Cross (abs value)", minval=0.0, step=0.01, group=g)
        g = "Exit Settings (ATR % Based)"
        self.atr_len = self.input.int(7, "Fast ATR Length", minval=1, group=g)
        self.tp_mult = self.input.float(1.5, "Take Profit Multiplier (x ATR)", step=0.1, group=g)
        self.sl_mult = self.input.float(1.0, "Stop Loss Multiplier (x ATR)", step=0.1, group=g)
        g = "Risk Management"
        self.use_equity_risk = self.input.bool(False, "Size Position by % Equity Risk", group=g)
        self.risk_pct = self.input.float(1.0, "Risk per Trade (% of Equity)", minval=0.1, step=0.1, group=g)
        self.locked_tp = NA
        self.locked_sl = NA

    def on_bar(self):
        range_hl = ta.highest(self.high, self.chop_len) - ta.lowest(self.low, self.chop_len)
        atr_sum = ta.msum(ta.atr(1), self.chop_len)
        chop_value = 0.0 if range_hl == 0 else div(100 * pmath.log10(div(atr_sum, range_hl)), pmath.log10(self.chop_len))
        di_plus, di_minus, adx_value = ta.dmi(self.adx_len, self.adx_len)
        trend_ema = ta.ema(self.close, self.trend_len)
        uptrend = self.close > trend_ema
        downtrend = self.close < trend_ema
        ema1 = ta.ema(self.close, self.trix_len)
        ema2 = ta.ema(ema1, self.trix_len)
        ema3 = ta.ema(ema2, self.trix_len)
        trix_value = ta.roc(ema3, 1)
        trix_prev = self.H("trix")[1]
        self.H("trix").set(trix_value)
        trix_slope = trix_value - trix_prev
        fast_atr = ta.atr(self.atr_len)
        tp_distance = fast_atr * self.tp_mult
        sl_distance = fast_atr * self.sl_mult
        can_long = self.trade_direction == "Both" or self.trade_direction == "Long"
        can_short = self.trade_direction == "Both" or self.trade_direction == "Short"
        filters_met = chop_value < self.chop_thresh and adx_value > self.adx_min
        trend_ok_long = (not self.use_trend_filter) or uptrend
        trend_ok_short = (not self.use_trend_filter) or downtrend
        cross_up = ta.crossover(trix_value, 0)
        cross_dn = ta.crossunder(trix_value, 0)
        long_trigger = cross_up and pmath.abs(trix_slope) >= self.min_trix_slope
        short_trigger = cross_dn and pmath.abs(trix_slope) >= self.min_trix_slope
        enter_long = can_long and filters_met and trend_ok_long and long_trigger
        enter_short = can_short and filters_met and trend_ok_short and short_trigger
        st = self.strategy
        equity = st.equity
        risk_amount = equity * (self.risk_pct / 100)
        max_qty = div(equity, self.close)
        qty = pmath.min(div(risk_amount, sl_distance), max_qty) if (self.use_equity_risk and sl_distance > 0) else NA
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        flat = st.position_size == 0
        if enter_long and (flat or (in_short and self.allow_reversal)):
            self.locked_tp = tp_distance
            self.locked_sl = sl_distance
            if self.use_equity_risk:
                st.entry("Long", st.long, qty=qty)
            else:
                st.entry("Long", st.long)
        if enter_short and (flat or (in_long and self.allow_reversal)):
            self.locked_tp = tp_distance
            self.locked_sl = sl_distance
            if self.use_equity_risk:
                st.entry("Short", st.short, qty=qty)
            else:
                st.entry("Short", st.short)
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Exit Long", "Long", limit=avg + self.locked_tp, stop=avg - self.locked_sl)
        if st.position_size < 0:
            st.exit("Exit Short", "Short", limit=avg - self.locked_tp, stop=avg + self.locked_sl)
        self.plot(trend_ema if self.use_trend_filter else NA, "Trend EMA", color=color.orange, linewidth=2)
