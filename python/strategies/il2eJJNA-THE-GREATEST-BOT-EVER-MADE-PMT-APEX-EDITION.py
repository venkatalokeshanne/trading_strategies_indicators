"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : THE GREATEST BOT EVER MADE - PMT APEX EDITION
Author       : SOLOBARBERTRADER
Source URL   : https://www.tradingview.com/script/il2eJJNA-THE-GREATEST-BOT-EVER-MADE-PMT-APEX-EDITION
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (the source is byte-identical to 3TPqnJu8 apart from its id). A fair value gap (with a bullish / bearish prior candle), an RSI-confirmed MACD cross, or an SMA20 "flag" on above-average volume, with ADX
above 20, opens a trade when flat. While a position exists the exit (400-tick stop from the entry plus a trailing stop that activates after 100 ticks and trails 50) is
issued at the bar close, so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: FVG background shading, the statistics table and alert messages.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class ApexBotCopy(Script):
    TITLE = "THE GREATEST BOT EVER MADE - PMT APEX EDITION"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "il2eJJNA", "author": "SOLOBARBERTRADER", "licence": "not stated",
              "url": "https://www.tradingview.com/script/il2eJJNA-THE-GREATEST-BOT-EVER-MADE-PMT-APEX-EDITION"}

    def init(self):
        self.sl_ticks = self.input.int(400, "Stop Loss (Ticks)")
        self.trail_activ = self.input.int(100, "Trail Activation (Ticks)")
        self.trail_offset = self.input.int(50, "Trail Offset (Ticks)")

    def on_bar(self):
        rsi_val = ta.rsi(self.close, 14)
        macd_line, signal_line, _ = ta.macd(self.close, 12, 26, 9)
        plus_di, minus_di, adx_val = ta.dmi(14, 14)
        atr_val = ta.atr(14)
        vol_sma = ta.sma(self.volume, 20)
        high_volume = self.volume > vol_sma
        low, high, close, open_ = S(self.low), S(self.high), S(self.close), S(self.open)
        bullish_fvg = low[0] > high[2] and close[1] > open_[1]
        bearish_fvg = high[0] < low[2] and close[1] < open_[1]
        bull_reversal = ta.crossover(macd_line, signal_line) and rsi_val < 40
        bear_reversal = ta.crossunder(macd_line, signal_line) and rsi_val > 60
        sma20 = ta.sma(self.close, 20)
        bull_flag = self.close > sma20 and high_volume and bullish_fvg
        sma20b = ta.sma(self.close, 20)
        bear_flag = self.close < sma20b and high_volume and bearish_fvg
        st = self.strategy
        long_cond = (bullish_fvg or bull_reversal or bull_flag) and high_volume and adx_val > 20
        if long_cond and st.position_size == 0:
            st.entry("APEX_LONG", st.long)
        short_cond = (bearish_fvg or bear_reversal or bear_flag) and high_volume and adx_val > 20
        if short_cond and st.position_size == 0:
            st.entry("APEX_SHORT", st.short)
        if st.position_size > 0:
            st.exit("Exit Long", "APEX_LONG", loss=self.sl_ticks, trail_points=self.trail_activ, trail_offset=self.trail_offset)
        if st.position_size < 0:
            st.exit("Exit Short", "APEX_SHORT", loss=self.sl_ticks, trail_points=self.trail_activ, trail_offset=self.trail_offset)
