"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : All-Day Futures Scalper (EMA Trend + Cross + ATR Brackets)
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/PVXJsjmB-All-Day-Futures-Scalper-EMA-Trend-Cross-ATR-Brackets
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). A fast EMA crossing over (under) the slow EMA with the close above (below) the 200 EMA, outside the cooldown after the last exit and with the ATR as a percentage of price above the minimum, enters long (short) while flat. Both sides re-issue a bracket every bar from the
average entry price: stop ATR x multiple away and take-profit ATR x multiple away; once the bar's high (low) has gone the break-even trigger in profit, the stop is no worse than the entry price.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class AllDayFuturesScalper(Script):
    TITLE = "All-Day Futures Scalper (EMA Trend + Cross + ATR Brackets)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="cash_per_contract", commission_value=0.0, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "PVXJsjmB", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/PVXJsjmB-All-Day-Futures-Scalper-EMA-Trend-Cross-ATR-Brackets"}

    def init(self):
        i = self.input
        self.use_longs = i.bool(True, "Enable Longs")
        self.use_shorts = i.bool(True, "Enable Shorts")
        self.fast_len = i.int(9, "Fast EMA Length", minval=1)
        self.slow_len = i.int(21, "Slow EMA Length", minval=1)
        self.trend_len = i.int(200, "Trend EMA Length", minval=1)
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.sl_atr = i.float(1.0, "Stop (ATR Mult)", step=0.1)
        self.tp_atr = i.float(1.5, "Take Profit (ATR Mult)", step=0.1)
        self.use_be = i.bool(True, "Move Stop to Breakeven")
        self.be_atr = i.float(1.0, "Breakeven Trigger (ATR Mult)", step=0.1)
        self.cooldown_bars = i.int(3, "Cooldown Bars After Exit", minval=0)
        self.use_chop_filter = i.bool(True, "Chop Filter: Require ATR% of Price")
        self.min_atr_pct = i.float(0.05, "Min ATR %", step=0.01)
        self.last_flat_bar = NA
        self.prev_pos = 0.0

    def on_bar(self):
        st = self.strategy
        close = self.close
        fast_ema = ta.ema(close, self.fast_len)
        slow_ema = ta.ema(close, self.slow_len)
        trend_ema = ta.ema(close, self.trend_len)
        atr = ta.atr(self.atr_len)
        atr_pct = div(atr, close) * 100.0
        just_went_flat = st.position_size == 0 and self.prev_pos != 0
        if just_went_flat:
            self.last_flat_bar = self.bar_index
        in_cooldown = self.cooldown_bars > 0 and (not na(self.last_flat_bar)) and (self.bar_index - self.last_flat_bar) <= self.cooldown_bars
        trend_up = close > trend_ema
        trend_down = close < trend_ema
        long_trig = ta.crossover(fast_ema, slow_ema)
        short_trig = ta.crossunder(fast_ema, slow_ema)
        chop_ok = (not self.use_chop_filter) or atr_pct >= self.min_atr_pct
        can_trade = (not in_cooldown) and chop_ok
        long_cond = can_trade and self.use_longs and trend_up and long_trig
        short_cond = can_trade and self.use_shorts and trend_down and short_trig
        if long_cond and st.position_size == 0:
            st.entry("L", st.long)
        if short_cond and st.position_size == 0:
            st.entry("S", st.short)
        avg = st.position_avg_price
        long_stop = avg - (self.sl_atr * atr)
        long_tp = avg + (self.tp_atr * atr)
        short_stop = avg + (self.sl_atr * atr)
        short_tp = avg - (self.tp_atr * atr)
        long_be = self.use_be and st.position_size > 0 and (self.high - avg) >= (self.be_atr * atr)
        short_be = self.use_be and st.position_size < 0 and (avg - self.low) >= (self.be_atr * atr)
        long_stop_final = pmath.max(long_stop, avg) if long_be else long_stop
        short_stop_final = pmath.min(short_stop, avg) if short_be else short_stop
        st.exit("L-Exit", from_entry="L", stop=long_stop_final, limit=long_tp)
        st.exit("S-Exit", from_entry="S", stop=short_stop_final, limit=short_tp)
        self.prev_pos = st.position_size
