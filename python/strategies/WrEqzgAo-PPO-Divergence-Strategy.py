"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : PPO Divergence Strategy
Author       : Boisetrader
Source URL   : https://www.tradingview.com/script/WrEqzgAo-PPO-Divergence-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. PPO = (EMA12 - EMA26) / EMA26 * 100. Pivots (5 bars each side) of price and of PPO feed var pairs
(last / previous). On the confirmation bar of a new price pivot low, a lower price low with a higher PPO low (bullish
divergence) goes long; a higher price high with a lower PPO high goes short. Entry and strategy.exit (2 % stop, 4 % target
around the signal close) are issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the divergence shapes, PPO / signal / histogram panes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, ta


class PpoDivergence(Script):
    TITLE = "PPO Divergence Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "WrEqzgAo", "author": "Boisetrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/WrEqzgAo-PPO-Divergence-Strategy"}

    def init(self):
        self.fast_len = self.input.int(12, "Fast EMA Length", minval=1)
        self.slow_len = self.input.int(26, "Slow EMA Length", minval=1)
        self.signal_len = self.input.int(9, "Signal Length", minval=1)
        self.pivot_len = self.input.int(5, "Pivot Lookback", minval=2)
        self.sl_pct = self.input.float(2.0, "Stop Loss %", minval=0.1, step=0.1)
        self.tp_pct = self.input.float(4.0, "Take Profit %", minval=0.1, step=0.1)
        self.prev_price_low = self.prev_ppo_low = self.prev_price_high = self.prev_ppo_high = NA
        self.last_price_low = self.last_ppo_low = self.last_price_high = self.last_ppo_high = NA

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        ppo = div(fast_ema - slow_ema, slow_ema) * 100
        signal = ta.ema(ppo, self.signal_len)
        pivot_high_price = ta.pivothigh(self.high, self.pivot_len, self.pivot_len)
        pivot_low_price = ta.pivotlow(self.low, self.pivot_len, self.pivot_len)
        pivot_high_ppo = ta.pivothigh(ppo, self.pivot_len, self.pivot_len)
        pivot_low_ppo = ta.pivotlow(ppo, self.pivot_len, self.pivot_len)
        if not na(pivot_low_price):
            self.prev_price_low = self.last_price_low
            self.prev_ppo_low = self.last_ppo_low
            self.last_price_low = pivot_low_price
            self.last_ppo_low = pivot_low_ppo
        if not na(pivot_high_price):
            self.prev_price_high = self.last_price_high
            self.prev_ppo_high = self.last_ppo_high
            self.last_price_high = pivot_high_price
            self.last_ppo_high = pivot_high_ppo
        bull_div = (not na(self.prev_price_low) and not na(self.prev_ppo_low) and not na(self.last_price_low) and not na(self.last_ppo_low)
                    and (self.last_price_low < self.prev_price_low) and (self.last_ppo_low > self.prev_ppo_low))
        bear_div = (not na(self.prev_price_high) and not na(self.prev_ppo_high) and not na(self.last_price_high) and not na(self.last_ppo_high)
                    and (self.last_price_high > self.prev_price_high) and (self.last_ppo_high < self.prev_ppo_high))
        bull_signal = bull_div and not na(pivot_low_price)
        bear_signal = bear_div and not na(pivot_high_price)
        st = self.strategy
        if bull_signal:
            sl = self.close * (1 - self.sl_pct / 100)
            tp = self.close * (1 + self.tp_pct / 100)
            st.entry("Long", st.long)
            st.exit("Long Exit", from_entry="Long", stop=sl, limit=tp)
        if bear_signal:
            sl = self.close * (1 + self.sl_pct / 100)
            tp = self.close * (1 - self.tp_pct / 100)
            st.entry("Short", st.short)
            st.exit("Short Exit", from_entry="Short", stop=sl, limit=tp)
        self.plot(ppo, "PPO", color=color.blue, linewidth=2)
        self.plot(signal, "Signal", color=color.orange)
