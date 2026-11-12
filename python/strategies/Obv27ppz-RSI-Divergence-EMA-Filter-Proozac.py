"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Divergence + EMA Filter [Proozac]
Author       : Proozac98
Source URL   : https://www.tradingview.com/script/Obv27ppz-RSI-Divergence-EMA-Filter-Proozac
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Confirmed pivot highs / lows of price (left / right bars input) are paired with the RSI value at the pivot bar: a higher price high with a lower RSI high is a bearish divergence (short), a lower price low with a higher RSI low a bullish divergence (long);
optionally the earlier pivot's RSI must have been overbought / oversold, and the 200 EMA must agree (long above, short below). A signal while flat enters; with "Use R:R" on, a stop and a target (ATR multiples) are issued with the entry; while in a position (default on) a trailing stop is re-issued every bar with
activation and offset both equal to ATR x multiplier converted to ticks.
Deviations from the original: none.
Not carried over: the divergence lines, entry labels and the position background (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class RsiDivergenceEma(Script):
    TITLE = "RSI Divergence + EMA Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=2, initial_capital=10000, commission_type="percent",
                    commission_value=0.05, slippage=2)
    SOURCE = {"id": "Obv27ppz", "author": "Proozac98", "licence": "not stated", "url": "https://www.tradingview.com/script/Obv27ppz-RSI-Divergence-EMA-Filter-Proozac"}

    def init(self):
        i = self.input
        g = "RSI Settings"
        self.rsi_len = i.int(14, "RSI Length", group=g, minval=2)
        self.pivot_lb = i.int(5, "Pivot Left Bars", group=g, minval=2, maxval=20)
        self.pivot_rb = i.int(5, "Pivot Right Bars", group=g, minval=2, maxval=20)
        self.rsi_ob = i.int(70, "Overbought Level", group=g, minval=50, maxval=90)
        self.rsi_os = i.int(30, "Oversold Level", group=g, minval=10, maxval=50)
        self.require_ob_os = i.bool(False, "Require RSI in OB/OS at First Pivot", group=g)
        g = "Trend Filter"
        self.use_ema_filter = i.bool(True, "Use EMA Trend Filter", group=g)
        self.ema_len = i.int(200, "Trend EMA Length", group=g, minval=10)
        g = "Risk Management"
        self.use_rr = i.bool(False, "Use R:R Target/Stop", group=g)
        self.rr_ratio = i.float(2.0, "Risk:Reward Ratio", group=g, minval=0.5, step=0.1)
        self.atr_mult_sl = i.float(1.5, "ATR Stop Multiplier", group=g, minval=0.5, step=0.1)
        self.atr_len = i.int(14, "ATR Length", group=g, minval=1)
        self.use_trail = i.bool(True, "Use Trailing ATR Stop", group=g)
        self.trail_mult = i.float(2.0, "Trailing ATR Multiplier", group=g, minval=0.5, step=0.1)
        self.prev_ph_p = NA
        self.prev_ph_r = NA
        self.last_ph_p = NA
        self.last_ph_r = NA
        self.prev_pl_p = NA
        self.prev_pl_r = NA
        self.last_pl_p = NA
        self.last_pl_r = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        rsi_val = ta.rsi(close, self.rsi_len)
        rsi_hist = self.H("rsi")
        rsi_at_pivot = rsi_hist[self.pivot_rb]
        rsi_hist.set(rsi_val)
        trend_ema = ta.ema(close, self.ema_len)
        atr_val = ta.atr(self.atr_len)
        ph_price = ta.pivothigh(self.high, self.pivot_lb, self.pivot_rb)
        pl_price = ta.pivotlow(self.low, self.pivot_lb, self.pivot_rb)
        if not na(ph_price):
            self.prev_ph_p = self.last_ph_p
            self.prev_ph_r = self.last_ph_r
            self.last_ph_p = ph_price
            self.last_ph_r = rsi_at_pivot
        if not na(pl_price):
            self.prev_pl_p = self.last_pl_p
            self.prev_pl_r = self.last_pl_r
            self.last_pl_p = pl_price
            self.last_pl_r = rsi_at_pivot
        bear_div = (not na(ph_price)) and (not na(self.prev_ph_p)) and self.last_ph_p > self.prev_ph_p and self.last_ph_r < self.prev_ph_r \
            and ((not self.require_ob_os) or self.prev_ph_r >= self.rsi_ob)
        bull_div = (not na(pl_price)) and (not na(self.prev_pl_p)) and self.last_pl_p < self.prev_pl_p and self.last_pl_r > self.prev_pl_r \
            and ((not self.require_ob_os) or self.prev_pl_r <= self.rsi_os)
        above_ema = close > trend_ema
        long_signal = bull_div and ((not self.use_ema_filter) or above_ema)
        short_signal = bear_div and ((not self.use_ema_filter) or not above_ema)
        if long_signal and st.position_size == 0:
            sl_price = close - self.atr_mult_sl * atr_val
            tp_price = close + self.rr_ratio * self.atr_mult_sl * atr_val
            st.entry("Long", st.long)
            if self.use_rr:
                st.exit("Long Exit", "Long", stop=sl_price, limit=tp_price)
        if short_signal and st.position_size == 0:
            sl_price = close + self.atr_mult_sl * atr_val
            tp_price = close - self.rr_ratio * self.atr_mult_sl * atr_val
            st.entry("Short", st.short)
            if self.use_rr:
                st.exit("Short Exit", "Short", stop=sl_price, limit=tp_price)
        trail_ticks = div(self.trail_mult * atr_val, self.syminfo.mintick)
        if self.use_trail and st.position_size > 0:
            st.exit("Long Trail", "Long", trail_points=trail_ticks, trail_offset=trail_ticks)
        if self.use_trail and st.position_size < 0:
            st.exit("Short Trail", "Short", trail_points=trail_ticks, trail_offset=trail_ticks)
