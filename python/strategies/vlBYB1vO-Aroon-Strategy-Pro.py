"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Aroon Strategy Pro - Whale Edition
Author       : QueenBee11_
Source URL   : https://www.tradingview.com/script/vlBYB1vO-Aroon-Strategy-Pro
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An Aroon up line crossing the Aroon down line (lines rebuilt from highestbars / lowestbars of length+1), filtered by the close
vs SMA290 and EMA200, opens a "Trade" at the signal close's levels; the script itself tracks the fixed stop, the R:R target (plus a tick buffer) and an optional
break-even move against each bar's high / low, and closes the trade with a market close (filled at the next open) when one is hit. A one-bar gap after each exit
blocks re-entry.

Deviations from the original: none.
Not carried over: the trade lines, WIN / LOSS / BE labels and the statistics table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class AroonStrategyPro(Script):
    TITLE = "Aroon Strategy Pro - Whale Edition"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "vlBYB1vO", "author": "QueenBee11_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/vlBYB1vO-Aroon-Strategy-Pro"}

    def init(self):
        g = "Trade Management"
        self.length = self.input.int(14, "Aroon Length", minval=1, group=g)
        self.rr_ratio = self.input.float(1.5, "Risk:Reward Ratio", minval=0.1, group=g)
        self.sl_pips = self.input.float(20.0, "Fixed SL (Pips/Points)", minval=1.0, group=g)
        self.tp_ticks = self.input.int(2, "Ticks Beyond TP to Trigger", minval=0, group=g)
        g = "Break Even"
        self.use_be = self.input.bool(True, "Enable Break Even?", group=g)
        self.be_at_rr = self.input.float(1.0, "Move to BE at RR", minval=0.1, group=g)
        g = "Trend Filter (SMA + EMA)"
        self.use_filter = self.input.bool(True, "Use Trend Filter?", group=g)
        self.sma_len = self.input.int(290, "SMA Length", minval=1, group=g)
        self.ema_len = self.input.int(200, "EMA Length", minval=1, group=g)
        self.in_trade = False
        self.trade_dir = 0
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.be_trigger_price = 0.0
        self.last_trade_exit_bar = 0

    def on_bar(self):
        sma_val = ta.sma(self.close, self.sma_len)
        ema_val = ta.ema(self.close, self.ema_len)
        trend_long = (not self.use_filter) or (self.close > sma_val and self.close > ema_val)
        trend_short = (not self.use_filter) or (self.close < sma_val and self.close < ema_val)
        upper = 100 * div(ta.highestbars(self.high, self.length + 1) + self.length, self.length)
        lower = 100 * div(ta.lowestbars(self.low, self.length + 1) + self.length, self.length)
        st = self.strategy
        mintick = self.syminfo.mintick
        if self.in_trade:
            if self.use_be:
                if (self.trade_dir == 1 and self.high >= self.be_trigger_price) or (self.trade_dir == -1 and self.low <= self.be_trigger_price):
                    self.sl_price = self.entry_price
            tp_trigger = self.tp_price + (self.trade_dir * self.tp_ticks * mintick)
            hit_tp = (self.trade_dir == 1 and self.high >= tp_trigger) or (self.trade_dir == -1 and self.low <= tp_trigger)
            hit_sl = (self.trade_dir == 1 and self.low <= self.sl_price) or (self.trade_dir == -1 and self.high >= self.sl_price)
            if hit_tp:
                st.close("Trade", comment="WIN")
                self.in_trade = False
                self.last_trade_exit_bar = self.bar_index
            elif hit_sl:
                st.close("Trade", comment="BE" if self.sl_price == self.entry_price else "LOSS")
                self.in_trade = False
                self.last_trade_exit_bar = self.bar_index
        can_enter = self.bar_index > self.last_trade_exit_bar + 1
        long_signal = ta.crossunder(lower, upper) and not self.in_trade and trend_long and can_enter
        short_signal = ta.crossover(lower, upper) and not self.in_trade and trend_short and can_enter
        if (long_signal or short_signal) and self.barstate.isconfirmed:
            self.in_trade = True
            self.entry_price = float(self.close)
            self.trade_dir = 1 if long_signal else -1
            tick_val = mintick * 10
            self.sl_price = self.entry_price - (self.trade_dir * self.sl_pips * tick_val)
            self.tp_price = self.entry_price + (self.trade_dir * self.sl_pips * tick_val * self.rr_ratio)
            self.be_trigger_price = self.entry_price + (self.trade_dir * self.sl_pips * tick_val * self.be_at_rr)
            if long_signal:
                st.entry("Trade", st.long)
            else:
                st.entry("Trade", st.short)
        self.plot(sma_val if self.use_filter else NA, "SMA Filter", color=color.blue)
        self.plot(ema_val if self.use_filter else NA, "EMA Filter", color=color.yellow)
