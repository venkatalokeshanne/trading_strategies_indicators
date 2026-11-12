"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Hull RSI - Trend Rider Pro
Author       : forexandy1946
Source URL   : https://www.tradingview.com/script/0ZBQpzty-Hull-RSI-Trend-Rider-Pro
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. HMA(550) direction (rising = 1, otherwise -1) sets the trend; in an uptrend an RSI(14) cross
under 50 goes long, in a downtrend a cross over 50 goes short, once per trend cycle (the flag resets whenever the Hull
direction changes) and only when flat. The stop is the lowest low / highest high of 13 bars and the target is 5 R,
kept in vars; an exit without from_entry is issued every bar a position is open at the close (so it first works on the
bar after the fill). A Hull direction flip closes the position at the next open.

In v6 `(trendDir == 1) and ta.crossunder(...) and not tradeTaken` short-circuits: the cross only runs while the trend
is up (the short-side cross while it is down), so each cross's "previous bar" is the last bar it ran on
(LESSONS P4/P5; pinelib models this).

Known caveat: ta.lowest / ta.highest sit inside the entry `if`, so pinelib's windows hold only the values fed on bars
where that branch ran (LESSONS P5). The first twelve entries therefore carry na stop / target (no bracket) until a 13-value
window exists; if TradingView computes them from the full bar history, those early trades would be bracketed there.

Deviations from the original: none.
Not carried over: the Hull colour and the SL / TP line plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class HullRsiTrendRider(Script):
    TITLE = "Hull RSI - Trend Rider Pro"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=1000)
    SOURCE = {"id": "0ZBQpzty", "author": "forexandy1946", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0ZBQpzty-Hull-RSI-Trend-Rider-Pro"}

    def init(self):
        self.hull_length = self.input.int(55, "Hull Base Length")
        self.hull_mult = self.input.float(10.0, "Hull Multiplier")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_upper = self.input.int(50, "RSI Upper (Short Trigger)")
        self.rsi_lower = self.input.int(50, "RSI Lower (Long Trigger)")
        self.lookback = self.input.int(13, "SL Lookback", minval=1)
        self.rr_ratio = self.input.float(5.0, "Risk:Reward Ratio", minval=0.1, step=0.1)
        self.sl_price = NA
        self.tp_price = NA
        self.trade_taken_this_cycle = False

    def on_bar(self):
        actual_length = int(self.hull_length * self.hull_mult)
        hma = ta.hma(self.close, actual_length)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        trend_dir = 1 if hma > self.H("hma")[1] else -1
        self.H("hma").set(hma)
        hull_changed = ta.change(trend_dir) != 0
        if hull_changed:
            self.trade_taken_this_cycle = False
        long_condition = (trend_dir == 1) and ta.crossunder(rsi_val, self.rsi_lower) and not self.trade_taken_this_cycle
        short_condition = (trend_dir == -1) and ta.crossover(rsi_val, self.rsi_upper) and not self.trade_taken_this_cycle
        st = self.strategy
        if long_condition and st.position_size == 0:
            self.sl_price = ta.lowest(self.low, self.lookback)
            risk = self.close - self.sl_price
            self.tp_price = self.close + (risk * self.rr_ratio)
            st.entry("Long", st.long)
            self.trade_taken_this_cycle = True
        if short_condition and st.position_size == 0:
            self.sl_price = ta.highest(self.high, self.lookback)
            risk = self.sl_price - self.close
            self.tp_price = self.close - (risk * self.rr_ratio)
            st.entry("Short", st.short)
            self.trade_taken_this_cycle = True
        if st.position_size > 0 and trend_dir == -1:
            st.close("Long", comment="Trend Flip")
        if st.position_size < 0 and trend_dir == 1:
            st.close("Short", comment="Trend Flip")
        if st.position_size != 0:
            st.exit("Exit", stop=self.sl_price, limit=self.tp_price, comment_loss="Safety SL", comment_profit="Take Profit")
        self.plot(hma, color=color.green if trend_dir == 1 else color.red, linewidth=3, title="Hull Suite")
