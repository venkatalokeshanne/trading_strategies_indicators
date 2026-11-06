"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : PRO Scalping Strategy EMA50 + RSI3 + ADX5
Author       : jesusito216
Source URL   : https://www.tradingview.com/script/5T1yRlvM
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long: close above EMA50 with a rising EMA (vs 5 bars ago), RSI(3) crossing over 20, ADX(5)
above 30, a body over 60 % of the bar range, inside the London (08:00-12:00) or New York (13:00-17:00) exchange
session (bar start time). Short is the mirror (RSI crossing under 80). On a signal the entry and a strategy.exit with
stop = signal bar's low / high and limit = 1.5 R are issued together (so they also work on the fill bar); a further
signal on the side already open ignores the entry but re-issues the exit with the new levels.

Deviations from the original: none.
Not carried over: the EMA plot and BUY / SELL label shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, pmath, ta


class ProScalping(Script):
    TITLE = "PRO Scalping Strategy EMA50 + RSI3 + ADX5"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "5T1yRlvM", "author": "jesusito216", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5T1yRlvM"}

    def init(self):
        self.ema_length = self.input.int(50, "EMA Length")
        self.rsi_length = self.input.int(3, "RSI Length")
        self.rsi_overbought = self.input.int(80, "RSI Overbought")
        self.rsi_oversold = self.input.int(20, "RSI Oversold")
        self.adx_length = self.input.int(5, "ADX Length")
        self.adx_threshold = self.input.int(30, "ADX Strength")
        self.risk_reward = self.input.float(1.5, "Risk Reward", step=0.1)
        self.session_london = self.input.session("0800-1200", "London Session")
        self.session_ny = self.input.session("1300-1700", "New York Session")

    def on_bar(self):
        ema50 = ta.ema(self.close, self.ema_length)
        ema50_h = self.H("ema50")
        rsi = ta.rsi(self.close, self.rsi_length)
        diplus, diminus, adx = ta.dmi(self.adx_length, self.adx_length)
        ema_slope = ema50 - ema50_h[5]
        candle_body = pmath.abs(self.close - self.open)
        candle_range = self.high - self.low
        strong_candle = candle_body > candle_range * 0.6
        in_london = not na(self.time_fn(None, self.session_london))
        in_ny = not na(self.time_fn(None, self.session_ny))
        session_filter = in_london or in_ny
        trend_long = self.close > ema50 and ema_slope > 0
        trend_short = self.close < ema50 and ema_slope < 0
        rsi_long = ta.crossover(rsi, self.rsi_oversold)
        rsi_short = ta.crossunder(rsi, self.rsi_overbought)
        strong_trend = adx > self.adx_threshold
        long_condition = trend_long and rsi_long and strong_trend and strong_candle and session_filter
        short_condition = trend_short and rsi_short and strong_trend and strong_candle and session_filter
        st = self.strategy
        if long_condition:
            stop = self.low
            risk = self.close - stop
            target = self.close + risk * self.risk_reward
            st.entry("LONG", st.long)
            st.exit("TP/SL LONG", "LONG", stop=stop, limit=target)
        if short_condition:
            stop = self.high
            risk = stop - self.close
            target = self.close - risk * self.risk_reward
            st.entry("SHORT", st.short)
            st.exit("TP/SL SHORT", "SHORT", stop=stop, limit=target)
        ema50_h.set(ema50)
        self.plot(ema50, color=color.orange, linewidth=2, title="EMA 50")
