"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Mean Reversion (2 Candle Rejection)
Author       : Spencer1976
Source URL   : https://www.tradingview.com/script/3Q98707C-VWAP-Mean-Reversion-2-Candle-Rejection
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.vwap(close) resets at each trading day's session start (symbol
session). strategy.exit is re-issued on every signal bar with that bar's levels, as in Pine, and
replaces any earlier bracket of the same id. History of derived values (lowerBand[1], ema20[10])
goes through S().

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, pmath, ta


class VwapMeanReversion2Candle(Script):
    TITLE = "VWAP Mean Reversion (2 Candle Rejection)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "3Q98707C", "author": "Spencer1976", "licence": "not stated",
              "url": "https://www.tradingview.com/script/3Q98707C-VWAP-Mean-Reversion-2-Candle-Rejection"}

    def on_bar(self):
        vwap_value = ta.vwap(self.close)
        atr = ta.atr(14)
        hour_ny = self.hour(self.time, "America/New_York")
        session_filter = (hour_ny >= 18) or (hour_ny <= 2)
        ema20 = S(ta.ema(self.close, 20))
        ema_slope = pmath.abs(ema20 - ema20[10])
        flat_ema = ema_slope < atr * 0.4
        upper_band = S(vwap_value + atr * 2.5)
        lower_band = S(vwap_value - atr * 2.5)
        upper_stop = vwap_value + atr * 4
        lower_stop = vwap_value - atr * 4
        long_reject = (self.low[1] < lower_band[1]) or (self.low < lower_band)
        short_reject = (self.high[1] > upper_band[1]) or (self.high > upper_band)
        long_signal = long_reject and self.close > lower_band
        short_signal = short_reject and self.close < upper_band
        entry_long = self.close
        stop_long = lower_stop
        target_long = vwap_value
        risk_long = entry_long - stop_long
        reward_long = target_long - entry_long
        valid_long_rr = reward_long >= risk_long * 1.5
        entry_short = self.close
        stop_short = upper_stop
        target_short = vwap_value
        risk_short = stop_short - entry_short
        reward_short = entry_short - target_short
        valid_short_rr = reward_short >= risk_short * 1.5
        st = self.strategy
        if long_signal and valid_long_rr and session_filter and flat_ema:
            st.entry("Long", st.long)
            st.exit("Long Exit", from_entry="Long", stop=stop_long, limit=target_long)
        if short_signal and valid_short_rr and session_filter and flat_ema:
            st.entry("Short", st.short)
            st.exit("Short Exit", from_entry="Short", stop=stop_short, limit=target_short)
        self.plot(vwap_value, color=color.orange, linewidth=2)
        self.plot(upper_band, color=color.red)
        self.plot(lower_band, color=color.green)
        self.plot(upper_stop, color=color.purple)
        self.plot(lower_stop, color=color.purple)
