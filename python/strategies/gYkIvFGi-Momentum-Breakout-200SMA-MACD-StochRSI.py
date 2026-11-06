"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Momentum Breakout | 200SMA + MACD + StochRSI
Author       : martinearthheaven
Source URL   : https://www.tradingview.com/script/gYkIvFGi-Momentum-Breakout-200SMA-MACD-StochRSI
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The close crossing the 200 SMA with the MACD line on the same side of zero and the stochastic RSI %K beyond its threshold enters (reversing an open opposite position) at the next open, when the latest swing high / low give a valid
take-profit above / stop below (below / above for shorts). The bracket is placed with the entry; an entry that is ignored because the position already points that way still re-issues the bracket with the new levels, as in the original.

Deviations from the original: none.
Not carried over: the SMA / swing lines, entry labels and info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class MomentumBreakout(Script):
    TITLE = "Momentum Breakout | 200SMA + MACD + StochRSI"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.05, slippage=2)
    SOURCE = {"id": "gYkIvFGi", "author": "martinearthheaven", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gYkIvFGi-Momentum-Breakout-200SMA-MACD-StochRSI"}

    def init(self):
        self.sma_len = self.input.int(200, "SMA Length", minval=1, group="200 SMA")
        g = "MACD"
        self.macd_fast = self.input.int(12, "Fast Length", minval=1, group=g)
        self.macd_slow = self.input.int(26, "Slow Length", minval=1, group=g)
        self.macd_signal = self.input.int(9, "Signal Length", minval=1, group=g)
        g = "Stochastic RSI"
        self.rsi_len = self.input.int(14, "RSI Length", minval=1, group=g)
        self.stoch_len = self.input.int(14, "Stoch Length", minval=1, group=g)
        self.smooth_k = self.input.int(3, "Smooth %K", minval=1, group=g)
        self.smooth_d = self.input.int(3, "Smooth %D", minval=1, group=g)
        self.stoch_bull_lvl = self.input.int(80, "Bull Threshold (Long  Entry)", minval=50, maxval=100, group=g)
        self.stoch_bear_lvl = self.input.int(20, "Bear Threshold (Short Entry)", minval=0, maxval=50, group=g)
        g = "Dynamic TP / SL (Swing Pivots)"
        self.swing_lookback = self.input.int(10, "Pivot Lookback Bars (left & right)", minval=3, maxval=50, group=g)
        self.tp_buffer = self.input.float(0.001, "TP Buffer (fraction beyond pivot)", minval=0.0, step=0.001, group=g)
        self.sl_buffer = self.input.float(0.001, "SL Buffer (fraction beyond pivot)", minval=0.0, step=0.001, group=g)
        self.last_swing_high = NA
        self.last_swing_low = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        sma200 = ta.sma(close, self.sma_len)
        macd_line, _signal_line, _hist_line = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_signal)
        rsi_val = ta.rsi(close, self.rsi_len)
        stoch_k_raw = ta.stoch(rsi_val, rsi_val, rsi_val, self.stoch_len)
        stoch_k = ta.sma(stoch_k_raw, self.smooth_k)
        _stoch_d = ta.sma(stoch_k, self.smooth_d)
        ph = ta.pivothigh(self.high, self.swing_lookback, self.swing_lookback)
        pl = ta.pivotlow(self.low, self.swing_lookback, self.swing_lookback)
        if not na(ph):
            self.last_swing_high = ph
        if not na(pl):
            self.last_swing_low = pl
        cross_above_sma = ta.crossover(close, sma200)
        cross_below_sma = ta.crossunder(close, sma200)
        long_condition = cross_above_sma and macd_line > 0 and stoch_k > self.stoch_bull_lvl
        short_condition = cross_below_sma and macd_line < 0 and stoch_k < self.stoch_bear_lvl
        if long_condition and (not na(self.last_swing_high)) and (not na(self.last_swing_low)):
            long_tp = self.last_swing_high * (1 + self.tp_buffer)
            long_sl = self.last_swing_low * (1 - self.sl_buffer)
            if long_tp > close and long_sl < close:
                st.entry("Long", st.long, comment="Long")
                st.exit("Long Exit", from_entry="Long", limit=long_tp, stop=long_sl, comment_profit="TP Hit", comment_loss="SL Hit")
        if short_condition and (not na(self.last_swing_high)) and (not na(self.last_swing_low)):
            short_tp = self.last_swing_low * (1 - self.tp_buffer)
            short_sl = self.last_swing_high * (1 + self.sl_buffer)
            if short_tp < close and short_sl > close:
                st.entry("Short", st.short, comment="Short")
                st.exit("Short Exit", from_entry="Short", limit=short_tp, stop=short_sl, comment_profit="TP Hit", comment_loss="SL Hit")
        self.plot(sma200, "SMA 200", color=color.gray, linewidth=2)
