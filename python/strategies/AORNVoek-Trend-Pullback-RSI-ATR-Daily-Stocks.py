"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Pullback RSI+ATR | Daily Stocks
Author       : Antonellago
Source URL   : https://www.tradingview.com/script/AORNVoek-Trend-Pullback-RSI-ATR-Daily-Stocks
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In an EMA50 > EMA200 regime with the close above EMA50, an RSI that crossed back above 50 within 5 bars of a dip into the 40-50 zone, and ATR over 1% of price,
a long enters at the bar close (process_orders_on_close). The ATR stop (2x) and target (4x) are fixed at that signal and issued once the position exists (they first work on the second bar after
the signal); a bearish EMA50 / EMA200 cross closes the trade.

Deviations from the original: timestamp("2018-01-01") (the date-string overload) is read in GMT+0 as the Pine docs describe, written as timestamp("UTC", 2018, 1, 1, 0, 0).
Not carried over: EMA plots, regime background, signal shape and stop / target lines (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class TrendPullbackRsiAtr(Script):
    TITLE = "Trend Pullback RSI+ATR | Daily Stocks"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.05, slippage=2, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "AORNVoek", "author": "Antonellago", "licence": "not stated",
              "url": "https://www.tradingview.com/script/AORNVoek-Trend-Pullback-RSI-ATR-Daily-Stocks"}

    def init(self):
        self.ema_fast_len = self.input.int(50, "EMA Rápida (régimen)", minval=10)
        self.ema_slow_len = self.input.int(200, "EMA Lenta (régimen)", minval=50)
        self.rsi_len = self.input.int(14, "RSI Length", minval=2)
        self.rsi_pullback = self.input.int(50, "RSI nivel pullback/cross", minval=30, maxval=70)
        self.rsi_zone_low = self.input.int(40, "RSI zona pullback - bajo", minval=20, maxval=50)
        self.atr_len = self.input.int(14, "ATR Length", minval=5)
        self.atr_stop_mult = self.input.float(2.0, "ATR Stop Multiplier", minval=0.5, step=0.1)
        self.atr_tp_mult = self.input.float(4.0, "ATR TP Multiplier", minval=0.5, step=0.1)
        self.risk_per_trade = self.input.float(1.0, "Riesgo % por trade", minval=0.1, maxval=5.0, step=0.1)
        self.start_date = self.input.time(self.timestamp("UTC", 2018, 1, 1, 0, 0), "Fecha inicio backtest")
        self.end_date = self.input.time(self.timestamp("UTC", 2099, 1, 1, 0, 0), "Fecha fin backtest")
        self.entry_price = NA
        self.stop_price = NA
        self.tp_price = NA

    def on_bar(self):
        in_date_range = self.time >= self.start_date and self.time <= self.end_date
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        bull_regime = ema_fast > ema_slow and self.close > ema_fast
        pullback_happened = ta.barssince(rsi <= self.rsi_pullback and rsi >= self.rsi_zone_low) <= 5
        rsi_cross_up = ta.crossover(rsi, self.rsi_pullback)
        atr_pct_of_price = div(atr, self.close) * 100
        vol_ok = atr_pct_of_price > 1.0
        long_condition = bull_regime and pullback_happened and rsi_cross_up and vol_ok and in_date_range
        cross_dn = ta.crossunder(ema_fast, ema_slow)
        st = self.strategy
        if long_condition and st.position_size == 0:
            self.entry_price = float(self.close)
            self.stop_price = self.close - self.atr_stop_mult * atr
            self.tp_price = self.close + self.atr_tp_mult * atr
            risk_amount = st.equity * (self.risk_per_trade / 100)
            risk_per_share = self.entry_price - self.stop_price
            qty = div(risk_amount, risk_per_share) if risk_per_share > 0 else 0
            st.entry("Long", st.long, qty=qty)
        if st.position_size > 0:
            st.exit("Exit", "Long", stop=self.stop_price, limit=self.tp_price)
        if st.position_size > 0 and cross_dn:
            st.close("Long", comment="Régimen roto")
        self.plot(ema_fast, "EMA 50", color=color.blue, linewidth=2)
        self.plot(ema_slow, "EMA 200", color=color.orange, linewidth=2)
