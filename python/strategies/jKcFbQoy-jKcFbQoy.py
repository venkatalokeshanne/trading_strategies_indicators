"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Smart Scalping PRO Strategy
Author       : jesusito216
Source URL   : https://www.tradingview.com/script/jKcFbQoy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long: close above EMA50, EMA50 above EMA200 with a rising EMA50 (vs 5 bars ago), RSI(3)
crossing over 20, ADX(5) above 30, ATR above its SMA(20), inside the London (08:00-12:00) or New York (13:00-17:00)
exchange session (bar start). Short is the mirror (RSI crossing under 80). Entry and strategy.exit (stop 1.2 ATR, limit
1.5 R) are issued together on the signal bar, so the bracket also works on the fill bar; a further signal on the open
side re-issues the exit.

Deviations from the original: none.
Not carried over: the EMA plots, signal shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class SmartScalpingPro(Script):
    TITLE = "Smart Scalping PRO Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "jKcFbQoy", "author": "jesusito216", "licence": "not stated",
              "url": "https://www.tradingview.com/script/jKcFbQoy"}

    def init(self):
        self.ema_fast_len = self.input.int(50, "EMA 50")
        self.ema_slow_len = self.input.int(200, "EMA 200")
        self.rsi_len = self.input.int(3, "RSI Length")
        self.rsi_ob = self.input.int(80, "RSI Overbought")
        self.rsi_os = self.input.int(20, "RSI Oversold")
        self.adx_len = self.input.int(5, "ADX Length")
        self.adx_level = self.input.int(30, "ADX Threshold")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.2, "ATR Multiplier")
        self.rr = self.input.float(1.5, "Risk Reward")
        self.london = self.input.session("0800-1200", "London Session")
        self.newyork = self.input.session("1300-1700", "New York Session")

    def on_bar(self):
        ema50 = ta.ema(self.close, self.ema_fast_len)
        ema50_h = self.H("ema50")
        ema200 = ta.ema(self.close, self.ema_slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        diplus, diminus, adx = ta.dmi(self.adx_len, self.adx_len)
        atr = ta.atr(self.atr_len)
        ema_slope = ema50 - ema50_h[5]
        atr_ma = ta.sma(atr, 20)
        volatility = atr > atr_ma
        in_london = not na(self.time_fn(None, self.london))
        in_ny = not na(self.time_fn(None, self.newyork))
        session_ok = in_london or in_ny
        trend_long = self.close > ema50 and ema50 > ema200 and ema_slope > 0
        trend_short = self.close < ema50 and ema50 < ema200 and ema_slope < 0
        rsi_long = ta.crossover(rsi, self.rsi_os)
        rsi_short = ta.crossunder(rsi, self.rsi_ob)
        strong_trend = adx > self.adx_level
        long_condition = trend_long and rsi_long and strong_trend and session_ok and volatility
        short_condition = trend_short and rsi_short and strong_trend and session_ok and volatility
        long_stop = self.close - atr * self.atr_mult
        short_stop = self.close + atr * self.atr_mult
        long_target = self.close + (self.close - long_stop) * self.rr
        short_target = self.close - (short_stop - self.close) * self.rr
        st = self.strategy
        if long_condition:
            st.entry("BUY", st.long)
            st.exit("TP/SL BUY", "BUY", stop=long_stop, limit=long_target)
        if short_condition:
            st.entry("SELL", st.short)
            st.exit("TP/SL SELL", "SELL", stop=short_stop, limit=short_target)
        ema50_h.set(ema50)
        self.plot(ema50, color=color.orange, linewidth=2, title="EMA 50")
        self.plot(ema200, color=color.blue, linewidth=2, title="EMA 200")
