"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Nifty Futures ORB - Smart Trail
Author       : gentlegyani
Source URL   : https://www.tradingview.com/script/CDhXq8DM-Nifty-Futures-ORB-Smart-Trail
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The 09:15-09:30 IST opening range locks after the window and is valid when narrower than the maximum width; a close beyond it before 14:30 enters once per side per day when flat,
risk-sized by the larger of the distance to the other side of the range and an ATR multiple. From the first bar holding the position a stop ratchets with an ATR trail (multiple shrinking as the profit in R grows) or the
5-bar swing extreme, whichever is tighter; a large reversal candle closes the trade at the next open; everything is squared off in the 15:15-15:30 window. The day change follows the symbol's trading-day
convention (09:15 IST start for an NSE chart).

Deviations from the original: none.
Not carried over: the opening-range and stop plots and the entry shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta

IST = "Asia/Kolkata"


class NiftyOrbSmartTrail(Script):
    TITLE = "Nifty Futures ORB - Smart Trail"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=500000, default_qty_type="fixed", default_qty_value=1, pyramiding=0, commission_type="percent", commission_value=0.03, slippage=1)
    SOURCE = {"id": "CDhXq8DM", "author": "gentlegyani", "licence": "not stated",
              "url": "https://www.tradingview.com/script/CDhXq8DM-Nifty-Futures-ORB-Smart-Trail"}

    def init(self):
        self.or_start = self.input.session("0915-0930", "Opening Range Window (IST)", group="Opening Range")
        self.or_max_width_pct = self.input.float(0.5, "Max OR Width (% of price) — skip wider days", step=0.1, group="Opening Range")
        g = "Risk"
        self.atr_len = self.input.int(14, "ATR Length", group=g)
        self.init_stop_atr_mult = self.input.float(1.5, "Initial Stop = ATR x", step=0.1, group=g)
        self.risk_pct = self.input.float(1.0, "Risk % of Equity per Trade", step=0.1, group=g)
        g = "Trailing"
        self.trail_atr_mult1 = self.input.float(3.0, "Trail Mult: 0-1R profit", step=0.1, group=g)
        self.trail_atr_mult2 = self.input.float(2.0, "Trail Mult: 1R-2R profit", step=0.1, group=g)
        self.trail_atr_mult3 = self.input.float(1.0, "Trail Mult: beyond 2R profit", step=0.1, group=g)
        self.swing_len = self.input.int(5, "Structural Swing Lookback (bars)", group=g)
        self.reversal_atr_mult = self.input.float(1.0, "Reversal Exit: single candle moves x ATR against position", step=0.1, group=g)
        g = "Session"
        self.square_off_time = self.input.session("1515-1530", "Square-Off Window (IST)", group=g)
        self.no_new_entry_after = self.input.session("1430-1530", "No New Entries After (IST)", group=g)
        g = "Direction"
        self.allow_longs = self.input.bool(True, "Allow Longs", group=g)
        self.allow_shorts = self.input.bool(True, "Allow Shorts", group=g)
        self.or_high = NA
        self.or_low = NA
        self.or_locked = False
        self.took_long_today = False
        self.took_short_today = False
        self.entry_price = NA
        self.init_risk = NA
        self.stop_price = NA

    def on_bar(self):
        in_or_window = not na(self.time_fn(None, self.or_start, IST))
        in_square_off = not na(self.time_fn(None, self.square_off_time, IST))
        in_no_entry = not na(self.time_fn(None, self.no_new_entry_after, IST))
        new_day = ta.change(self.time_fn("D")) != 0
        if new_day:
            self.or_high = NA
            self.or_low = NA
            self.or_locked = False
        if in_or_window:
            self.or_high = float(self.high) if na(self.or_high) else pmath.max(self.or_high, self.high)
            self.or_low = float(self.low) if na(self.or_low) else pmath.min(self.or_low, self.low)
        if (not in_or_window) and (not self.or_locked) and not na(self.or_high):
            self.or_locked = True
        or_width_pct = div(self.or_high - self.or_low, self.close) * 100 if (not na(self.or_high) and not na(self.or_low)) else NA
        or_valid = self.or_locked and not na(or_width_pct) and or_width_pct <= self.or_max_width_pct
        atr_val = ta.atr(self.atr_len)
        if new_day:
            self.took_long_today = False
            self.took_short_today = False
        st = self.strategy
        can_enter = or_valid and (not in_no_entry) and st.position_size == 0
        long_signal = self.allow_longs and can_enter and (not self.took_long_today) and self.close > self.or_high
        short_signal = self.allow_shorts and can_enter and (not self.took_short_today) and self.close < self.or_low
        long_stop_dist = pmath.max(self.close - self.or_low, atr_val * self.init_stop_atr_mult)
        short_stop_dist = pmath.max(self.or_high - self.close, atr_val * self.init_stop_atr_mult)
        risk_amount = st.equity * (self.risk_pct / 100)
        long_qty = pmath.max(1, pmath.round(div(risk_amount, long_stop_dist))) if long_stop_dist > 0 else 1
        short_qty = pmath.max(1, pmath.round(div(risk_amount, short_stop_dist))) if short_stop_dist > 0 else 1
        if long_signal:
            st.entry("Long", st.long, qty=long_qty)
            self.entry_price = float(self.close)
            self.init_risk = long_stop_dist
            self.stop_price = self.close - long_stop_dist
            self.took_long_today = True
        if short_signal:
            st.entry("Short", st.short, qty=short_qty)
            self.entry_price = float(self.close)
            self.init_risk = short_stop_dist
            self.stop_price = self.close + short_stop_dist
            self.took_short_today = True
        swing_high = ta.highest(self.high, self.swing_len)
        swing_low = ta.lowest(self.low, self.swing_len)
        if st.position_size > 0:
            profit_r = div(self.high - self.entry_price, self.init_risk)
            trail_mult = self.trail_atr_mult3 if profit_r >= 2 else (self.trail_atr_mult2 if profit_r >= 1 else self.trail_atr_mult1)
            atr_trail = self.high - atr_val * trail_mult
            new_stop = pmath.max(atr_trail, swing_low)
            self.stop_price = pmath.max(self.stop_price, new_stop)
            st.exit("L-Exit", "Long", stop=self.stop_price)
        if st.position_size < 0:
            profit_r = div(self.entry_price - self.low, self.init_risk)
            trail_mult = self.trail_atr_mult3 if profit_r >= 2 else (self.trail_atr_mult2 if profit_r >= 1 else self.trail_atr_mult1)
            atr_trail = self.low + atr_val * trail_mult
            new_stop = pmath.min(atr_trail, swing_high)
            self.stop_price = pmath.min(self.stop_price, new_stop)
            st.exit("S-Exit", "Short", stop=self.stop_price)
        if st.position_size > 0 and (self.close - self.open) < 0 and (self.open - self.close) > atr_val * self.reversal_atr_mult:
            st.close("Long", comment="Reversal Candle")
        if st.position_size < 0 and (self.close - self.open) > 0 and (self.close - self.open) > atr_val * self.reversal_atr_mult:
            st.close("Short", comment="Reversal Candle")
        if in_square_off and st.position_size != 0:
            st.close_all(comment="Square Off")
        self.plot(self.or_high, "OR High", color=color.blue)
        self.plot(self.or_low, "OR Low", color=color.blue)
