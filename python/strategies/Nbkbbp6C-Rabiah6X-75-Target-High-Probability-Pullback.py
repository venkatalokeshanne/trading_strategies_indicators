"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rabiah6X - 75% Target High-Probability Pullback
Author       : Soheibhussen357
Source URL   : https://www.tradingview.com/script/Nbkbbp6C-Rabiah6X-75-Target-High-Probability-Pullback
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long when the close is above SMA200, the hand-written ADX(14) (dirmov: +DM / -DM from the
changes of high and low, RMA-smoothed against ta.tr, fixnan on the DI lines) is above 20, the close crosses back above
EMA21 (a ta.crossover, or close > EMA21 with the previous close at or under the previous EMA21) and RSI(14) is within
[45, 70]. Further signals while long are ignored (pyramiding 1). While a position is open at the close, a bracket of
1.8 ATR below / 1.2 ATR above that close is issued, so it first works on the bar after the fill and always uses the
previous bar's levels.

Deviations from the original: none.
Not carried over: the MA plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, fixnan, na, pmath, ta


class RabiahPullback(Script):
    TITLE = "Rabiah6X - 75% Target High-Probability Pullback"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "Nbkbbp6C", "author": "Soheibhussen357", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Nbkbbp6C-Rabiah6X-75-Target-High-Probability-Pullback"}

    def init(self):
        self.ma_long_len = self.input.int(200, title="Macro Trend Filter MA (200)")
        self.ma_short_len = self.input.int(21, title="Short Trend MA (21)")
        self.rsi_len = self.input.int(14, title="RSI Length")
        self.rsi_oversold = self.input.int(45, title="RSI Pullback Low Threshold")
        self.rsi_overbought = self.input.int(70, title="RSI Overbought Cap")
        self.adx_len = self.input.int(14, title="ADX Smoothing")
        self.adx_threshold = self.input.float(20.0, title="Minimum ADX Trend Strength")

    def dirmov(self, length):
        up = ta.change(self.high)
        down = -ta.change(self.low)
        plus_dm = NA if na(up) else (up if (up > down and up > 0) else 0)
        minus_dm = NA if na(down) else (down if (down > plus_dm and down > 0) else 0)
        return plus_dm, minus_dm

    def on_bar(self):
        macro_ma = ta.sma(self.close, self.ma_long_len)
        short_ma = ta.ema(self.close, self.ma_short_len)
        di_len = self.adx_len
        plus_dm, minus_dm = self.dirmov(di_len)
        trur = ta.rma(ta.tr(False), di_len)
        plus = fixnan(100 * div(ta.rma(plus_dm, di_len), trur))
        minus = fixnan(100 * div(ta.rma(minus_dm, di_len), trur))
        total = plus + minus
        adx = 100 * ta.rma(div(pmath.abs(plus - minus), 1 if total == 0 else total), di_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        short_ma_h = S(short_ma)
        macro_trend_ok = self.close > macro_ma
        trend_strong = adx > self.adx_threshold
        cross_up = ta.crossover(self.close, short_ma)
        pullback_trigger = cross_up or (self.close > short_ma and self.close[1] <= short_ma_h[1])
        rsi_filter = rsi >= self.rsi_oversold and rsi <= self.rsi_overbought
        buy_signal = macro_trend_ok and trend_strong and pullback_trigger and rsi_filter
        st = self.strategy
        if buy_signal:
            st.entry("75% Winrate Long", st.long)
        atr_val = ta.atr(14)
        stop_loss = self.close - (atr_val * 1.8)
        take_profit = self.close + (atr_val * 1.2)
        if st.position_size > 0:
            st.exit("Managed Exit", "75% Winrate Long", stop=stop_loss, limit=take_profit)
        self.plot(macro_ma, color=color.blue, title="Macro Trend MA (200)")
        self.plot(short_ma, color=color.orange, title="Short Trend MA (21)")
