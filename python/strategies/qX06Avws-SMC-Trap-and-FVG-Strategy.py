"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMC Trap → FVG Strategy
Author       : relivewithros
Source URL   : https://www.tradingview.com/script/qX06Avws-SMC-Trap-and-FVG-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A "trap" is a bar that pokes beyond the previous N-bar extreme (ta.highest(high[1], N) is the
highest high of the N bars before this one), closes back inside and leaves a wick of at least 10 % of its range, with a
3-bar cooldown per side. Every three-bar fair-value gap is appended to three parallel lists (top, bottom, bullish
flag). A bear trap goes long with its target at the bottom of the most recent bearish gap above the close, a bull trap
goes short at the top of the most recent bullish gap below the close; no gap, no trade. The entry and its bracket
(stop = bar extreme -/+ 0.3 ATR) are issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: nothing.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, div, na, pmath, ta


class SmcTrapFvg(Script):
    TITLE = "SMC Trap → FVG Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "qX06Avws", "author": "relivewithros", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qX06Avws-SMC-Trap-and-FVG-Strategy"}

    def init(self):
        self.lookback = self.input.int(10, "Structure Lookback")
        self.cooldown = self.input.int(3, "Trap Cooldown")
        self.wick_percent = self.input.float(0.1, "Trap Wick %")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult_sl = self.input.float(0.3, "SL Buffer (ATR)")
        self.last_bull_trap = NA
        self.last_bear_trap = NA
        self.top_arr = []
        self.bot_arr = []
        self.bull_arr = []

    def get_nearest_fvg(self, is_long):
        target = NA
        sz = len(self.top_arr)
        if sz > 0:
            for i in range(sz - 1, -1, -1):
                t = self.top_arr[i]
                b = self.bot_arr[i]
                bull = self.bull_arr[i]
                if is_long and (not bull) and b > self.close:
                    target = b
                    break
                if (not is_long) and bull and t < self.close:
                    target = t
                    break
        return target

    def on_bar(self):
        atr = ta.atr(self.atr_len)
        swing_high = S(ta.highest(self.high, self.lookback))[1]
        swing_low = S(ta.lowest(self.low, self.lookback))[1]
        bar_range = self.high - self.low
        upper_wick = self.high - pmath.max(self.open, self.close)
        lower_wick = pmath.min(self.open, self.close) - self.low
        upper_pct = div(upper_wick, bar_range) if bar_range > 0 else 0
        lower_pct = div(lower_wick, bar_range) if bar_range > 0 else 0
        raw_bull_trap = self.high > swing_high and self.close < swing_high and upper_pct >= self.wick_percent
        raw_bear_trap = self.low < swing_low and self.close > swing_low and lower_pct >= self.wick_percent
        bull_trap = raw_bull_trap and (na(self.last_bull_trap) or self.bar_index - self.last_bull_trap > self.cooldown)
        bear_trap = raw_bear_trap and (na(self.last_bear_trap) or self.bar_index - self.last_bear_trap > self.cooldown)
        if bull_trap:
            self.last_bull_trap = self.bar_index
        if bear_trap:
            self.last_bear_trap = self.bar_index
        bull_fvg = self.high[2] < self.low
        bear_fvg = self.low[2] > self.high
        if bull_fvg:
            self.top_arr.append(float(self.low))
            self.bot_arr.append(self.high[2])
            self.bull_arr.append(True)
        if bear_fvg:
            self.top_arr.append(self.low[2])
            self.bot_arr.append(float(self.high))
            self.bull_arr.append(False)
        st = self.strategy
        if bear_trap:
            sl = self.low - atr * self.atr_mult_sl
            tp = self.get_nearest_fvg(True)
            if not na(tp):
                st.entry("LONG", st.long)
                st.exit("TP/SL LONG", from_entry="LONG", stop=sl, limit=tp)
        if bull_trap:
            sl = self.high + atr * self.atr_mult_sl
            tp = self.get_nearest_fvg(False)
            if not na(tp):
                st.entry("SHORT", st.short)
                st.exit("TP/SL SHORT", from_entry="SHORT", stop=sl, limit=tp)
