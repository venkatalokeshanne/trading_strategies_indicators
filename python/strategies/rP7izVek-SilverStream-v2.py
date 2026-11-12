"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SilverStream v2
Author       : shaggygent102
Source URL   : https://www.tradingview.com/script/rP7izVek-SilverStream-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA30 / EMA50 trend plus a break of the previous bar's high (long) or low (short), with a
3-bar cooldown counted from the last signal (lastTradeBar is set on every signal, even one ignored because that
side is already open; pyramiding 1). Both strategy.exit calls are unconditional with levels from
strategy.position_avg_price (na while flat), so bar i works with the levels computed at bar i-1's close: none on a
fill bar, and the OLD position's average on the first bar after a reversal.

Deviations from the original: none.
Not carried over: the EMA plots and the BUY / SELL / EXIT shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class SilverStreamV2(Script):
    TITLE = "SilverStream v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=200000, default_qty_type="fixed", default_qty_value=1, pyramiding=1)
    SOURCE = {"id": "rP7izVek", "author": "shaggygent102", "licence": "not stated",
              "url": "https://www.tradingview.com/script/rP7izVek-SilverStream-v2"}

    def init(self):
        self.fast_ema = self.input.int(30, "Fast EMA")
        self.slow_ema = self.input.int(50, "Slow EMA")
        self.target_move = self.input.float(2.0, "Target Move ($)")
        self.stop_move = self.input.float(1.0, "Stop Move ($)")
        self.cooldown_bars = self.input.int(3, "Trade Cooldown")
        self.last_trade_bar = NA

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.fast_ema)
        ema_slow = ta.ema(self.close, self.slow_ema)
        long_trend = ema_fast > ema_slow
        short_trend = ema_fast < ema_slow
        bull_break = self.close > self.high[1]
        bear_break = self.close < self.low[1]
        buy_signal = long_trend and bull_break
        sell_signal = short_trend and bear_break
        cooldown_ok = na(self.last_trade_bar) or self.bar_index - self.last_trade_bar > self.cooldown_bars
        buy = buy_signal and cooldown_ok
        sell = sell_signal and cooldown_ok
        st = self.strategy
        if buy:
            st.entry("BUY", st.long)
            self.last_trade_bar = self.bar_index
        if sell:
            st.entry("SELL", st.short)
            self.last_trade_bar = self.bar_index
        avg = st.position_avg_price
        long_target = avg + self.target_move
        long_stop = avg - self.stop_move
        short_target = avg - self.target_move
        short_stop = avg + self.stop_move
        st.exit("Exit Buy", from_entry="BUY", limit=long_target, stop=long_stop)
        st.exit("Exit Sell", from_entry="SELL", limit=short_target, stop=short_stop)
        self.plot(ema_fast, color=color.green)
        self.plot(ema_slow, color=color.red)
