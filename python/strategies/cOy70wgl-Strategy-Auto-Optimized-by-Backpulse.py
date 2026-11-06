"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy Auto-Optimized by Backpulse
Author       : Backpulse
Source URL   : https://www.tradingview.com/script/cOy70wgl
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A fast / slow EMA cross on the right side of the slow EMA, from the start year on, enters in that direction (the entry is ignored if already in the trade or the direction is disabled,
but the ATR trailing stop is re-seeded on every signal). While a position exists the exit uses the trailing stop (ratcheted every bar) or a fixed percentage stop plus a percentage target around position_avg_price.

Deviations from the original: none.
Not carried over: EMA / trail plots and background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, nz, pmath, ta


class BackpulseOptimized(Script):
    TITLE = "Strategy Auto-Optimized by Backpulse"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.075, slippage=1)
    SOURCE = {"id": "cOy70wgl", "author": "Backpulse", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cOy70wgl"}

    def init(self):
        g = "Trend Engine (v6)"
        self.fast_length = self.input.int(14, "Fast EMA Length", minval=5, maxval=100, step=1, group=g)
        self.slow_length = self.input.int(44, "Slow EMA Length", minval=20, maxval=200, step=2, group=g)
        g = "Volatility & Trailing Stop Filter"
        self.atr_period = self.input.int(14, "ATR Length", minval=5, maxval=50, step=1, group=g)
        self.atr_mult = self.input.float(2.5, "ATR Multiplier", minval=0.5, maxval=6.0, step=0.25, group=g)
        g = "Risk & Money Management"
        self.tp_percent = self.input.float(6.0, "Take Profit %", minval=1.0, maxval=25.0, step=0.5, group=g)
        self.sl_percent = self.input.float(3.0, "Hard Stop Loss %", minval=0.5, maxval=10.0, step=0.5, group=g)
        self.use_trailing = self.input.bool(True, "Enable Dynamic Trailing Stop", group=g)
        self.trade_dir = self.input.string("Both", "Trade Direction", options=["Both", "Long Only", "Short Only"], group=g)
        self.start_year = self.input.int(2023, "Start Year", minval=2015, maxval=2030, group="Backtest Timeframe Filter")
        self.long_trail_stop = NA
        self.short_trail_stop = NA

    def on_bar(self):
        in_date_range = self.time >= self.timestamp(self.syminfo.timezone, self.start_year, 1, 1, 0, 0)
        fast_ema = ta.ema(self.close, self.fast_length)
        slow_ema = ta.ema(self.close, self.slow_length)
        atr_val = ta.atr(self.atr_period)
        long_cond = ta.crossover(fast_ema, slow_ema) and self.close > slow_ema and in_date_range
        short_cond = ta.crossunder(fast_ema, slow_ema) and self.close < slow_ema and in_date_range
        st = self.strategy
        dist = atr_val * self.atr_mult
        if long_cond:
            self.long_trail_stop = self.close - dist
        elif st.position_size > 0 and self.use_trailing:
            self.long_trail_stop = pmath.max(nz(self.long_trail_stop, self.close - dist), self.close - dist)
        else:
            self.long_trail_stop = NA
        if short_cond:
            self.short_trail_stop = self.close + dist
        elif st.position_size < 0 and self.use_trailing:
            self.short_trail_stop = pmath.min(nz(self.short_trail_stop, self.close + dist), self.close + dist)
        else:
            self.short_trail_stop = NA
        can_long = self.trade_dir == "Both" or self.trade_dir == "Long Only"
        can_short = self.trade_dir == "Both" or self.trade_dir == "Short Only"
        if long_cond and can_long:
            st.entry("Long", st.long)
        if short_cond and can_short:
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Exit Long", "Long",
                    stop=self.long_trail_stop if self.use_trailing else st.position_avg_price * (1 - self.sl_percent / 100),
                    limit=st.position_avg_price * (1 + self.tp_percent / 100))
        if st.position_size < 0:
            st.exit("Exit Short", "Short",
                    stop=self.short_trail_stop if self.use_trailing else st.position_avg_price * (1 + self.sl_percent / 100),
                    limit=st.position_avg_price * (1 - self.tp_percent / 100))
        self.plot(fast_ema, "Fast EMA", color=color.blue, linewidth=2)
        self.plot(slow_ema, "Slow EMA", color=color.orange, linewidth=2)
