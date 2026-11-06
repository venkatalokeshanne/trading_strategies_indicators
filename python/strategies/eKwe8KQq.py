"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 🚀 DMT Full Control Pro V2 [DearmasTrader]
Author       : DearmasTrader
Source URL   : https://www.tradingview.com/script/eKwe8KQq
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. An EMA 9/21 golden (death) cross opens a long (short) when the optional RSI, MACD, Bollinger-squeeze, ATR-volatility and volume filters agree, in long, short or both directions; the opposite cross closes the position.
The original destructures ta.bb as [upper, basis, lower] although it returns [basis, upper, lower]; the squeeze test therefore divides (basis - lower) by the upper band, which is kept as written.

Deviations from the original: none.
Not carried over: the webhook alert strings and volume figure (alert payload only), the EMA / band plots and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class DmtFullControlProV2(Script):
    TITLE = "🚀 DMT Full Control Pro V2 [DearmasTrader]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=10, initial_capital=1000, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "eKwe8KQq", "author": "DearmasTrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/eKwe8KQq"}

    def init(self):
        i = self.input
        g = "⚙️ Modo de Operación"
        self.trade_mode = i.string("Long", "Modo", options=["Long", "Short", "Bidireccional"], group=g)
        g = "📈 EMAs (Golden/Death Cross)"
        self.ema_fast_len = i.int(9, "EMA Rápida", minval=1, group=g)
        self.ema_slow_len = i.int(21, "EMA Lenta", minval=5, group=g)
        self.use_ema = i.bool(True, "Activar filtro EMA", group=g)
        g = "🔵 RSI"
        self.rsi_len = i.int(14, "Longitud RSI", minval=2, group=g)
        self.rsi_ob = i.int(70, "Sobrecompra (OB)", minval=50, group=g)
        self.rsi_os = i.int(30, "Sobreventa (OS)", maxval=50, group=g)
        self.use_rsi = i.bool(True, "Activar filtro RSI", group=g)
        g = "⚡ MACD"
        self.macd_fast = i.int(12, "MACD Rápido", minval=1, group=g)
        self.macd_slow = i.int(26, "MACD Lento", minval=5, group=g)
        self.macd_signal = i.int(9, "MACD Señal", minval=1, group=g)
        self.use_macd = i.bool(True, "Activar filtro MACD", group=g)
        g = "🎯 Bandas de Bollinger"
        self.bb_len = i.int(20, "BB Longitud", minval=5, group=g)
        self.bb_mult = i.float(2.0, "BB Desviación", step=0.1, group=g)
        self.use_bb = i.bool(False, "Activar filtro BB (Squeeze)", group=g)
        g = "🌊 ATR — Filtro de Volatilidad"
        self.atr_len = i.int(14, "ATR Longitud", minval=1, group=g)
        self.atr_mult = i.float(1.5, "ATR Mínimo (x precio)", step=0.1, group=g)
        self.use_atr = i.bool(True, "Filtrar mercado plano con ATR", group=g)
        g = "📊 Volumen de Mercado"
        self.vol_ma_len = i.int(20, "MA Volumen", minval=5, group=g)
        self.use_vol_filter = i.bool(False, "Requiere volumen superior a la media", group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        golden_cross = ta.crossover(ema_fast, ema_slow)
        death_cross = ta.crossunder(ema_fast, ema_slow)
        rsi = ta.rsi(close, self.rsi_len)
        rsi_long = rsi < self.rsi_ob
        rsi_short = rsi > self.rsi_os
        macd_line, signal_line, hist_line = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_signal)
        macd_bullish = macd_line > signal_line and hist_line > 0
        macd_bearish = macd_line < signal_line and hist_line < 0
        bb_upper, bb_basis, bb_lower = ta.bb(close, self.bb_len, self.bb_mult)
        bb_squeeze = div(bb_upper - bb_lower, bb_basis) < 0.04
        atr_val = ta.atr(self.atr_len)
        atr_filter = atr_val > (close * (self.atr_mult / 100))
        vol_ma = ta.sma(self.volume, self.vol_ma_len)
        vol_filter = self.volume > vol_ma
        ema_long_ok = (not self.use_ema) or (ema_fast > ema_slow)
        ema_short_ok = (not self.use_ema) or (ema_fast < ema_slow)
        rsi_long_ok = (not self.use_rsi) or rsi_long
        rsi_short_ok = (not self.use_rsi) or rsi_short
        macd_long_ok = (not self.use_macd) or macd_bullish
        macd_short_ok = (not self.use_macd) or macd_bearish
        bb_long_ok = (not self.use_bb) or (not bb_squeeze)
        atr_ok = (not self.use_atr) or atr_filter
        vol_ok = (not self.use_vol_filter) or vol_filter
        long_condition = golden_cross and ema_long_ok and rsi_long_ok and macd_long_ok and bb_long_ok and atr_ok and vol_ok
        short_condition = death_cross and ema_short_ok and rsi_short_ok and macd_short_ok and bb_long_ok and atr_ok and vol_ok
        close_long = death_cross
        close_short = golden_cross
        is_long = self.trade_mode == "Long" or self.trade_mode == "Bidireccional"
        is_short = self.trade_mode == "Short" or self.trade_mode == "Bidireccional"
        if long_condition and is_long:
            st.entry("Long", st.long)
        if short_condition and is_short:
            st.entry("Short", st.short)
        if close_long and is_long:
            st.close("Long")
        if close_short and is_short:
            st.close("Short")
        self.plot(ema_fast, "EMA Rápida", color=color.yellow, linewidth=2)
        self.plot(ema_slow, "EMA Lenta", color=color.blue, linewidth=2)
