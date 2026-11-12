"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DMT - Estrategia Universal Editable
Author       : DearmasTrader
Source URL   : https://www.tradingview.com/script/i0XSbToM
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. With the default switches: EMA9 crossing over EMA21 with the close above EMA200 goes long, crossing
under with the close below goes short (reversing, 10 % of equity). The optional RSI filter (off by default) is kept; the
bot-secret/pair JSON strings of the original only build alert messages.

Deviations from the original: none.
Not carried over: the alert JSON strings and the EMA plots (they feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class DmtUniversal(Script):
    TITLE = "DMT - Estrategia Universal Editable"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "i0XSbToM", "author": "DearmasTrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/i0XSbToM"}

    def init(self):
        g = "Estrategia"
        self.use_ema = self.input.bool(True, "Usar Cruce de EMAs?", group=g)
        self.ema_fast = self.input.int(9, "EMA Rápida", group=g)
        self.ema_slow = self.input.int(21, "EMA Lenta", group=g)
        self.use_rsi = self.input.bool(False, "Filtrar por RSI?", group=g)
        self.rsi_len = self.input.int(14, "RSI Longitud", group=g)
        self.rsi_over_b = self.input.int(70, "Sobrecompra", group=g)
        self.rsi_over_s = self.input.int(30, "Sobreventa", group=g)
        self.use_trend = self.input.bool(True, "Filtro de Tendencia (EMA 200)?", group=g)

    def on_bar(self):
        val_ema_f = ta.ema(self.close, self.ema_fast)
        val_ema_s = ta.ema(self.close, self.ema_slow)
        val_ema_t = ta.ema(self.close, 200)
        val_rsi = ta.rsi(self.close, self.rsi_len)
        l_ema = ta.crossover(val_ema_f, val_ema_s) if self.use_ema else True
        s_ema = ta.crossunder(val_ema_f, val_ema_s) if self.use_ema else True
        l_rsi = val_rsi < self.rsi_over_s if self.use_rsi else True
        s_rsi = val_rsi > self.rsi_over_b if self.use_rsi else True
        l_trend = self.close > val_ema_t if self.use_trend else True
        s_trend = self.close < val_ema_t if self.use_trend else True
        long_signal = l_ema and l_rsi and l_trend
        short_signal = s_ema and s_rsi and s_trend
        st = self.strategy
        if long_signal:
            st.entry("Long", st.long)
        if short_signal:
            st.entry("Short", st.short)
        self.plot(val_ema_f, color=color.blue, title="EMA Rápida")
        self.plot(val_ema_s, color=color.orange, title="EMA Lenta")
        self.plot(val_ema_t if self.use_trend else NA, color=color.white, linewidth=2, title="EMA Trend")
