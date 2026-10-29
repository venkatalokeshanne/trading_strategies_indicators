"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ICT + Price Action | XAUUSD & EURUSD [v6]
Author       : demeth5D
Source URL   : https://www.tradingview.com/script/qkKBIVg4-ZETA9-v6
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Inside the London or New York kill-zone hours (UTC), with the EMA50/200 trend, an RSI that is not stretched, the session-VWAP side and an ICT setup (fair value gap, an engulfing-style order block, or a pin bar on the previous bar), a market entry is made with an ATR stop and target attached.

Deviations from the original: none.
Not carried over: FVG boxes, kill-zone shading, signal shapes and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, na, pmath, ta


class Zeta9(Script):
    TITLE = "ICT + Price Action | XAUUSD & EURUSD [v6]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=0, margin_short=0, default_qty_type="percent_of_equity", default_qty_value=2, commission_type="percent",
                    commission_value=0.01, slippage=2)
    SOURCE = {"id": "qkKBIVg4", "author": "demeth5D", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qkKBIVg4-ZETA9-v6"}

    def init(self):
        i = self.input
        self.ema_fast = i.int(50, "Fast EMA Length", minval=5, group="Trend Filter")
        self.ema_slow = i.int(200, "Slow EMA Length", minval=50, group="Trend Filter")
        g = "Risk Management"
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.sl_mult = i.float(1.5, "Stop Loss  (× ATR)", step=0.1, minval=0.5, group=g)
        self.tp_mult = i.float(2.5, "Take Profit (× ATR)", step=0.1, minval=1.0, group=g)
        g = "RSI Filter"
        self.rsi_len = i.int(14, "RSI Length", minval=2, group=g)
        self.rsi_ob = i.int(70, "Overbought Level", minval=55, group=g)
        self.rsi_os = i.int(30, "Oversold Level", maxval=45, group=g)
        g = "Kill Zones"
        self.lkz_start = i.int(7, "London KZ Start (UTC hour)", group=g)
        self.lkz_end = i.int(10, "London KZ End (UTC hour)", group=g)
        self.nykz_start = i.int(12, "New York KZ Start (UTC hour)", group=g)
        self.nykz_end = i.int(15, "New York KZ End (UTC hour)", group=g)
        self.use_vwap = i.bool(True, "Enable VWAP Direction Filter", group="VWAP")

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ema_fast_val = ta.ema(close, self.ema_fast)
        ema_slow_val = ta.ema(close, self.ema_slow)
        atr_val = ta.atr(self.atr_len)
        rsi_val = ta.rsi(close, self.rsi_len)
        vwap_val = ta.vwap()
        cur_hour = self.hour(self.time, "UTC")
        in_london = cur_hour >= self.lkz_start and cur_hour < self.lkz_end
        in_newyork = cur_hour >= self.nykz_start and cur_hour < self.nykz_end
        in_killzone = in_london or in_newyork
        bullish_trend = close > ema_slow_val and ema_fast_val > ema_slow_val
        bearish_trend = close < ema_slow_val and ema_fast_val < ema_slow_val
        vwap_bull = (not self.use_vwap) or close > vwap_val
        vwap_bear = (not self.use_vwap) or close < vwap_val
        rsi_ok_long = rsi_val < self.rsi_ob
        rsi_ok_short = rsi_val > self.rsi_os
        bull_fvg = high[2] < low
        bear_fvg = low[2] > high
        bull_ob = close[1] < open_[1] and close > high[1]
        bear_ob = close[1] > open_[1] and close < low[1]
        total_range = high - low
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - low
        body_size = abs(close - open_)
        bull_pinbar = total_range > 0 and lower_wick >= total_range * 0.667 and body_size <= total_range * 0.350
        bear_pinbar = total_range > 0 and upper_wick >= total_range * 0.667 and body_size <= total_range * 0.350
        bp_h, sp_h = self.H("bull_pin"), self.H("bear_pin")
        bull_pinbar_1, bear_pinbar_1 = bp_h[1], sp_h[1]
        bp_h.set(bull_pinbar)
        sp_h.set(bear_pinbar)
        ict_long_setup = bull_fvg or bull_ob or ((not na(bull_pinbar_1)) and bool(bull_pinbar_1))
        ict_short_setup = bear_fvg or bear_ob or ((not na(bear_pinbar_1)) and bool(bear_pinbar_1))
        no_position = st.position_size == 0
        long_signal = in_killzone and bullish_trend and vwap_bull and rsi_ok_long and ict_long_setup and no_position
        short_signal = in_killzone and bearish_trend and vwap_bear and rsi_ok_short and ict_short_setup and no_position
        if long_signal:
            sl = close - self.sl_mult * atr_val
            tp = close + self.tp_mult * atr_val
            st.entry("Long", st.long)
            st.exit("Long Exit", from_entry="Long", stop=sl, limit=tp)
        if short_signal:
            sl = close + self.sl_mult * atr_val
            tp = close - self.tp_mult * atr_val
            st.entry("Short", st.short)
            st.exit("Short Exit", from_entry="Short", stop=sl, limit=tp)
