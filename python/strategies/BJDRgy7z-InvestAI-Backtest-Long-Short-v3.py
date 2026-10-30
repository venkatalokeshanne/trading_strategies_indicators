"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : InvestAI - Backtest Long Short v3
Author       : ignaciodarias
Source URL   : https://www.tradingview.com/script/BJDRgy7z
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An EMA9 / EMA21 cross with RSI between the bounds and MACD on the same side (optional volume / EMA200 filters) is confirmed one bar later
(the signal is the previous bar's raw signal) and then enters at the next open, reversing an open opposite trade. The ATR stop (1x) and target (4x) are fixed on the
confirmation bar; a repeat signal while already in the trade ignores the entry but replaces the bracket.

Deviations from the original: none.
Not carried over: plots, signal labels and the HUD table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class InvestAiLongShort(Script):
    TITLE = "InvestAI - Backtest Long Short v3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=15, commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "BJDRgy7z", "author": "ignaciodarias", "licence": "not stated",
              "url": "https://www.tradingview.com/script/BJDRgy7z"}

    def init(self):
        self.ema_fast = self.input.int(9, "EMA Rápida")
        self.ema_slow = self.input.int(21, "EMA Lenta")
        self.rsi_len = self.input.int(14, "RSI Periodo")
        self.rsi_ob = self.input.int(70, "RSI Sobrecompra")
        self.rsi_os = self.input.int(30, "RSI Sobreventa")
        self.atr_len = self.input.int(14, "ATR Periodo")
        self.sl_mult = self.input.float(1.0, "SL Multiplicador ATR", minval=0.5, maxval=5.0, step=0.5)
        self.tp_mult = self.input.float(4.0, "TP Multiplicador ATR", minval=0.5, maxval=10.0, step=0.5)
        self.use_vol = self.input.bool(False, "Filtro Volumen")
        self.vol_mult = self.input.float(1.2, "Volumen mínimo vs media", minval=1.0, maxval=3.0, step=0.1)
        self.use_macro = self.input.bool(False, "Filtro EMA 200")
        self.use_confirm = self.input.bool(True, "Confirmar cierre de vela")
        self.prev_long_raw = False
        self.prev_short_raw = False

    def on_bar(self):
        e_fast = ta.ema(self.close, self.ema_fast)
        e_slow = ta.ema(self.close, self.ema_slow)
        e_macro = ta.ema(self.close, 200)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        vol20 = ta.sma(self.volume, 20)
        macd_line, signal_line, _ = ta.macd(self.close, 12, 26, 9)
        macd_bull = macd_line > signal_line
        macd_bear = macd_line < signal_line
        bull_cross = ta.crossover(e_fast, e_slow)
        bear_cross = ta.crossunder(e_fast, e_slow)
        vol_ok = (self.volume > vol20 * self.vol_mult) if self.use_vol else True
        macro_long = (self.close > e_macro) if self.use_macro else True
        macro_short = (self.close < e_macro) if self.use_macro else True
        long_raw = bull_cross and rsi > self.rsi_os and rsi < self.rsi_ob and macd_bull and vol_ok and macro_long
        short_raw = bear_cross and rsi < self.rsi_ob and rsi > self.rsi_os and macd_bear and vol_ok and macro_short
        long_sig = self.prev_long_raw if self.use_confirm else long_raw
        short_sig = self.prev_short_raw if self.use_confirm else short_raw
        self.prev_long_raw, self.prev_short_raw = bool(long_raw), bool(short_raw)
        st = self.strategy
        if long_sig:
            st.entry("LONG", st.long)
            st.exit("EXIT LONG", from_entry="LONG", stop=self.close - atr * self.sl_mult, limit=self.close + atr * self.tp_mult)
        if short_sig:
            st.entry("SHORT", st.short)
            st.exit("EXIT SHORT", from_entry="SHORT", stop=self.close + atr * self.sl_mult, limit=self.close - atr * self.tp_mult)
        self.plot(e_fast, "EMA Rápida", color=color.blue)
        self.plot(e_slow, "EMA Lenta", color=color.purple, linewidth=2)
