"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Estrategia EMA-RSI-ATR (FETUSDT - 4H)
Author       : kelvinibarey
Source URL   : https://www.tradingview.com/script/193w3Pua
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long when EMA21 > EMA89, the close is above EMA21, RSI(14) is within [55, 75] and ATR is above
its SMA(20), while flat. The stop (2.5 ATR) and target (4 ATR) are fixed on the signal bar into var levels; the exit is
issued only while a position is open at the close, so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: the EMA plots, signal background and level plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, pmath, pstr, ta


class EmaRsiAtrEth(Script):
    TITLE = "Estrategia EMA-RSI-ATR ETH 4H"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=40,
                    commission_type="percent", commission_value=0.075, slippage=2)
    SOURCE = {"id": "193w3Pua", "author": "kelvinibarey", "licence": "not stated",
              "url": "https://www.tradingview.com/script/193w3Pua"}

    def init(self):
        self.ema_fast_len = self.input.int(21, "EMA Rápida (21)", minval=1)
        self.ema_slow_len = self.input.int(89, "EMA Lenta (89)", minval=1)
        self.rsi_len = self.input.int(14, "Periodos RSI", minval=1)
        self.rsi_min = self.input.float(55.0, "RSI Mínimo", minval=0, maxval=100)
        self.rsi_max = self.input.float(75.0, "RSI Máximo", minval=0, maxval=100)
        self.atr_len = self.input.int(14, "Periodos ATR", minval=1)
        self.atr_ma_len = self.input.int(20, "Media ATR (Filtro Volatilidad)", minval=1)
        self.stop_loss_level = NA
        self.take_profit_level = NA

    def on_bar(self):
        ema21 = ta.ema(self.close, self.ema_fast_len)
        ema89 = ta.ema(self.close, self.ema_slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        atr_avg = ta.sma(atr, self.atr_ma_len)
        trend_condition = ema21 > ema89 and self.close > ema21
        momentum_condition = rsi >= self.rsi_min and rsi <= self.rsi_max
        volatility_condition = atr > atr_avg
        long_condition = trend_condition and momentum_condition and volatility_condition
        st = self.strategy
        if long_condition and st.position_size == 0:
            self.stop_loss_level = self.close - (atr * 2.5)
            self.take_profit_level = self.close + (atr * 4.0)
            st.entry("Long", st.long, comment="RSI:" + pstr.tostring(pmath.round(rsi, 2)))
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=self.stop_loss_level, limit=self.take_profit_level,
                    comment_loss="SL", comment_profit="TP")
        self.plot(ema21, color=color.blue, title="EMA 21")
        self.plot(ema89, color=color.orange, linewidth=2, title="EMA 89")
