"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Stepped trailing strategy example
Author       : adolgov
Source URL   : https://www.tradingview.com/script/jjhUHcje
Pine version : v4
Licence      : MPL 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A 14/28 SMA cross-over enters one long contract; the exit order "x" is re-issued every bar according to the stage reached by the position: stage 1 stop-loss and take-profit 3 given in ticks (percent of the average price), stage 2 (profit reached take-profit 1) stop at break-even, stage 3 (take-profit 2) stop at take-profit 1 level with either the fixed take-profit 3 or - when "activate trailing on third stage" is on - a trailing stop (activation = take-profit 3, offset = take-profit 3 - take-profit 2, in ticks); flat cancels the exit.
The source's trailing-level helper (calcTrailingAmountLevel / calcTrailingOffsetLevel) and the profit / stop plots only feed debug plots, never an order, and are not carried over.
Deviations from the original: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, ta


class SteppedTrailing(Script):
    TITLE = "Stepped trailing strategy example"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "jjhUHcje", "author": "adolgov", "licence": "MPL 2.0", "url": "https://www.tradingview.com/script/jjhUHcje"}

    def init(self):
        i = self.input
        self.sl_pct = i.float(5, "stop loss %%")
        self.tp1_pct = i.float(5, "take profit 1 %%")
        self.tp2_pct = i.float(10, "take profit 2 %%")
        self.tp3_pct = i.float(15, "take profit 3 %%")
        self.trail_third = i.bool(False, "activate trailing on third stage (tp3 is amount, tp2 is offset level)")
        self.stage = 0

    def on_bar(self):
        st = self.strategy
        mintick = self.syminfo.mintick
        if ta.crossover(ta.sma(self.close, 14), ta.sma(self.close, 28)):
            st.entry("My Long Entry Id", st.long)
        avg = st.position_avg_price
        pos = st.position_size
        sl = div(avg * self.sl_pct / 100, mintick)
        tp1 = div(avg * self.tp1_pct / 100, mintick)
        tp2 = div(avg * self.tp2_pct / 100, mintick)
        tp3 = div(avg * self.tp3_pct / 100, mintick)
        if pos > 0:
            cur_profit = div(self.high - avg, mintick)
        elif pos < 0:
            cur_profit = div(avg - self.low, mintick)
        else:
            cur_profit = 0
        if pos == 0:
            self.stage = 0
        if self.stage == 0 and pos != 0:
            self.stage = 1
        elif self.stage == 1 and cur_profit >= tp1:
            self.stage = 2
        elif self.stage == 2 and cur_profit >= tp2:
            self.stage = 3

        def stop_price(offset_pts):                 # calcStopLossPrice
            if pos > 0:
                return avg - offset_pts * mintick
            if pos < 0:
                return avg + offset_pts * mintick
            return NA

        if self.stage == 1:
            st.exit("x", loss=sl, profit=tp3, comment="sl or tp3")
        elif self.stage == 2:
            st.exit("x", stop=stop_price(0), profit=tp3, comment="breakeven or tp3")
        elif self.stage == 3:
            stop_level = stop_price(-tp1)
            if self.trail_third:
                st.exit("x", stop=stop_level, trail_points=tp3, trail_offset=tp3 - tp2, comment="stop tp1 or trailing tp3 with offset tp2")
            else:
                st.exit("x", stop=stop_level, profit=tp3, comment="tp1 or tp3")
        else:
            st.cancel("x")
