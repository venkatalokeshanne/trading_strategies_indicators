"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Beginner Trend & Risk Model (EMA + RSI)
Author       : hackermillionaire
Source URL   : https://www.tradingview.com/script/BjjAOuub-Beginner-Trend-Risk-Model-EMA-RSI
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long only: EMA9 crossing over EMA21 with RSI(14) between 30 and 70 enters when not already long, sized
at floor(1 % of equity / ATR) units (no order when that is 0); the bracket (stop 1 ATR, target 2 ATR from the signal close) is
issued with the entry, so it also works on the fill bar. An EMA cross under or RSI above 70 while long closes the position
at the next open.

Deviations from the original: none.
Not carried over: the EMA plots, background, signal shapes, qty label and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class BeginnerTrendRisk(Script):
    TITLE = "Beginner Trend & Risk Model (EMA + RSI)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "BjjAOuub", "author": "hackermillionaire", "licence": "not stated",
              "url": "https://www.tradingview.com/script/BjjAOuub-Beginner-Trend-Risk-Model-EMA-RSI"}

    def init(self):
        self.fast_len = self.input.int(9, "Fast EMA", minval=1)
        self.slow_len = self.input.int(21, "Slow EMA", minval=1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=2)
        self.rsi_ob = self.input.int(70, "RSI Overbought", minval=50, maxval=100)
        self.rsi_os = self.input.int(30, "RSI Oversold", minval=0, maxval=50)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.risk_rr = self.input.float(2.0, "Risk/Reward (TP = RR x SL)", minval=0.5, step=0.5)
        self.risk_pct = self.input.float(1.0, "Risk % per Trade", minval=0.1, maxval=5, step=0.1)

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        bull_trend = fast_ema > slow_ema
        long_entry_cond = ta.crossover(fast_ema, slow_ema) and bull_trend and rsi > self.rsi_os and rsi < self.rsi_ob
        long_exit_cond = ta.crossunder(fast_ema, slow_ema) or rsi > self.rsi_ob
        st = self.strategy
        risk_amount = st.equity * (self.risk_pct / 100.0)
        sl_distance = atr
        raw_qty = div(risk_amount, sl_distance) if sl_distance > 0 else 0.0
        qty = pmath.floor(raw_qty) if raw_qty > 0 else 0
        long_sl = self.close - atr
        long_tp = self.close + atr * self.risk_rr
        if long_entry_cond and st.position_size <= 0 and qty > 0:
            st.entry("LONG", st.long, qty=qty)
            st.exit("LONG EXIT", "LONG", stop=long_sl, limit=long_tp)
        if long_exit_cond and st.position_size > 0:
            st.close("LONG")
        self.plot(fast_ema, color=color.green, linewidth=2, title="Fast EMA")
        self.plot(slow_ema, color=color.red, linewidth=2, title="Slow EMA")
