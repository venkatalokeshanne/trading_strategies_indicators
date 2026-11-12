"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : All-Day Futures Trend Pullback (EMA + RSI) [v5]
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/9tPTFXRh-All-Day-Futures-Trend-Pullback-EMA-RSI-v5
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Above (below) EMA100 with RSI14 pulled back to <= 45 (>= 55) enters at the bar close (process_orders_on_close), reversing an open
opposite trade. While a position exists, the stop / target around position_avg_price (tick or ATR distances, optional tick trail) are issued with
the matching exit order, so they first work on the bar after the fill.

Deviations from the original: none.
Not carried over: RSI hline and the signal characters (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class AllDayPullback(Script):
    TITLE = "All-Day Futures Trend Pullback (EMA + RSI) [v5]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="cash_per_contract", commission_value=0.0, pyramiding=0,
                    process_orders_on_close=True)
    SOURCE = {"id": "9tPTFXRh", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9tPTFXRh-All-Day-Futures-Trend-Pullback-EMA-RSI-v5"}

    def init(self):
        self.ema_len = self.input.int(100, "EMA Length", minval=1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.rsi_long_max = self.input.float(45.0, "Long: RSI must be <= (pullback)", step=0.5)
        self.rsi_short_min = self.input.float(55.0, "Short: RSI must be >= (pullback)", step=0.5)
        self.use_session = self.input.bool(False, "Use Session Filter?")
        self.session_str = self.input.session("0000-2359", "Session (exchange time)")
        self.risk_mode = self.input.string("Ticks", "Stop/Target Mode", options=["Ticks", "ATR"])
        self.sl_ticks = self.input.int(40, "Stop Loss (ticks)", minval=1)
        self.tp_ticks = self.input.int(80, "Take Profit (ticks)", minval=1)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.sl_atr_mult = self.input.float(1.5, "Stop Loss (ATR x)", step=0.1)
        self.tp_atr_mult = self.input.float(3.0, "Take Profit (ATR x)", step=0.1)
        self.use_trail = self.input.bool(False, "Use Trailing Stop?")
        self.trail_ticks = self.input.int(20, "Trailing Stop (ticks)", minval=1)
        self.qty = self.input.float(1, "Contracts", minval=0.0)

    def stop_target_prices(self, is_long, tick, atr):
        avg = self.strategy.position_avg_price
        if self.risk_mode == "Ticks":
            if is_long:
                return avg - self.sl_ticks * tick, avg + self.tp_ticks * tick
            return avg + self.sl_ticks * tick, avg - self.tp_ticks * tick
        if is_long:
            return avg - (self.sl_atr_mult * atr), avg + (self.tp_atr_mult * atr)
        return avg + (self.sl_atr_mult * atr), avg - (self.tp_atr_mult * atr)

    def on_bar(self):
        ema = ta.ema(self.close, self.ema_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        in_session = (not self.use_session) or (not na(self.time_fn(None, self.session_str)))
        trend_up = self.close > ema
        trend_down = self.close < ema
        long_cond = in_session and trend_up and rsi <= self.rsi_long_max
        short_cond = in_session and trend_down and rsi >= self.rsi_short_min
        tick = self.syminfo.mintick
        st = self.strategy
        if long_cond and st.position_size <= 0:
            st.entry("Long", st.long, qty=self.qty)
        if short_cond and st.position_size >= 0:
            st.entry("Short", st.short, qty=self.qty)
        if st.position_size > 0:
            sl, tp = self.stop_target_prices(True, tick, atr)
            if self.use_trail:
                st.exit("Long Exit", from_entry="Long", stop=sl, limit=tp, trail_points=self.trail_ticks * tick)
            else:
                st.exit("Long Exit", from_entry="Long", stop=sl, limit=tp)
        if st.position_size < 0:
            sl, tp = self.stop_target_prices(False, tick, atr)
            if self.use_trail:
                st.exit("Short Exit", from_entry="Short", stop=sl, limit=tp, trail_points=self.trail_ticks * tick)
            else:
                st.exit("Short Exit", from_entry="Short", stop=sl, limit=tp)
        self.plot(ema, "EMA", linewidth=2)
