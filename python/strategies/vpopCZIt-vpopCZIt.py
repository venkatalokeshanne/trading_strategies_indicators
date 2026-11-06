"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA-RSI-ATR Strategy (AXSUSDT - D)
Author       : kelvinibarey
Source URL   : https://www.tradingview.com/script/vpopCZIt
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long when EMA21 > EMA89, the close is above EMA21, RSI(14) is between 55 and 75 and ATR is
above its SMA(20), while flat. entryAtr (var) captures the ATR of the first bar on which the position is open at the
close and is reset when flat; the exit is issued only while a position is open, so the 2.5 ATR stop / 4 ATR target
(around the average price) first work on the bar after the fill.

Deviations from the original: none.
Not carried over: the EMA plots and the signal background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class EmaRsiAtrStrategy(Script):
    TITLE = "EMA-RSI-ATR Strategy (AXSUSDT - D)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=40,
                    commission_type="percent", commission_value=0.075, slippage=2)
    SOURCE = {"id": "vpopCZIt", "author": "kelvinibarey", "licence": "not stated",
              "url": "https://www.tradingview.com/script/vpopCZIt"}

    def init(self):
        self.ema_fast_len = self.input.int(21, "EMA Rápida", group="EMAs")
        self.ema_slow_len = self.input.int(89, "EMA Lenta", group="EMAs")
        self.rsi_len = self.input.int(14, "RSI Período", group="RSI")
        self.rsi_low = self.input.int(55, "RSI Mínimo", group="RSI")
        self.rsi_high = self.input.int(75, "RSI Máximo", group="RSI")
        self.atr_len = self.input.int(14, "ATR Período", group="ATR")
        self.atr_ma_len = self.input.int(20, "ATR Media Período", group="ATR")
        self.sl_mult = self.input.float(2.5, "Stop Loss ATR x", group="Gestión de riesgo")
        self.tp_mult = self.input.float(4.0, "Take Profit ATR x", group="Gestión de riesgo")
        self.entry_atr = NA

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        atr_ma = ta.sma(atr, self.atr_ma_len)
        trend_ok = ema_fast > ema_slow and self.close > ema_fast
        momentum_ok = rsi > self.rsi_low and rsi < self.rsi_high
        volat_ok = atr > atr_ma
        long_signal = trend_ok and momentum_ok and volat_ok
        st = self.strategy
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long)
        if st.position_size > 0 and na(self.entry_atr):
            self.entry_atr = atr
        if st.position_size == 0:
            self.entry_atr = NA
        stop_price = st.position_avg_price - self.sl_mult * self.entry_atr
        tp_price = st.position_avg_price + self.tp_mult * self.entry_atr
        if st.position_size > 0:
            st.exit("Exit", "Long", stop=stop_price, limit=tp_price)
        self.plot(ema_fast, "EMA 21", color=color.orange)
        self.plot(ema_slow, "EMA 89", color=color.blue, linewidth=2)
