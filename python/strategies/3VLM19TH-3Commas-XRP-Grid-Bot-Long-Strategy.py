"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [3Commas] XRP Grid Bot - Long Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/3VLM19TH-3Commas-XRP-Grid-Bot-Long-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas long-only grid bot: 23 price levels between 1.1124 and 1.5466 (geometric spacing). Crossing DOWN through a level (previous close above it, close at or below it) buys one slot of
investment / levels at the bar close (process_orders_on_close); crossing UP through the level above it (previous close below, close at or above) closes that slot. Each slot has its own entry id, so closes are per slot.


Deviations from the original: none.
Not carried over: the webhook alert text, grid lines, range box, labels, status table, watermark table and the average-entry plot's styling (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, nz, pmath

FROM_DATE = 1770336000000     # timestamp("06 Feb 2026 00:00 +0000")
TO_DATE = 1778803140000       # timestamp("14 May 2026 23:59 +0000")


class GridBot3VLM19TH(Script):
    TITLE = "[3Commas] XRP Grid Bot - Long Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=435, pyramiding=200, commission_type="percent",
                    commission_value=0.06, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "3VLM19TH", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/3VLM19TH-3Commas-XRP-Grid-Bot-Long-Strategy"}

    def init(self):
        g = "Grid Bounds"
        self.high_price = self.input.float(1.5466, "High Price", minval=0, step=0.0001, group=g)
        self.low_price = self.input.float(1.1124, "Low Price", minval=0, step=0.0001, group=g)
        g = "Grid Configuration"
        self.n_levels = self.input.int(23, "Grid Levels", minval=7, maxval=200, group=g)
        self.grid_mode = self.input.string("Geometric", "Spacing Mode", options=["Geometric", "Arithmetic"], group=g)
        self.investment = self.input.float(10000.0, "Total Investment (USDT)", minval=100, group=g)
        g = "Backtest Window"
        self.use_date_filter = self.input.bool(True, "Limit Backtest Period", group=g)
        self.from_date = self.input.time(FROM_DATE, "From", group=g)
        self.to_date = self.input.time(TO_DATE, "To", group=g)
        self.grid_owned = [False] * 200
        self.grid_levels = [NA] * 200

    def f_level_px(self, i):
        pct = div(float(i), float(self.n_levels - 1))
        if self.grid_mode == "Geometric":
            return self.high_price * pmath.pow(div(self.low_price, self.high_price), pct)
        return self.high_price - (self.high_price - self.low_price) * pct

    def on_bar(self):
        in_window = (not self.use_date_filter) or (self.time >= self.from_date and self.time <= self.to_date)
        usdt_per_level = div(self.investment, self.n_levels)
        if self.barstate.isfirst:
            for i in range(0, self.n_levels):
                self.grid_levels[i] = self.f_level_px(i)
        close = S(self.close)
        prev_close = nz(close[1], self.close)
        st = self.strategy
        if in_window:
            for i in range(1, self.n_levels):
                level_px = self.grid_levels[i]
                upper_px = self.grid_levels[i - 1]
                owned = self.grid_owned[i]
                if (not owned) and prev_close > level_px and self.close <= level_px:
                    qty = div(usdt_per_level, level_px)
                    st.entry("L" + str(i), st.long, qty=qty, comment="Grid_BUY_L" + str(i))
                    self.grid_owned[i] = True
                if owned and prev_close < upper_px and self.close >= upper_px:
                    st.close("L" + str(i), comment="Grid_TP_L" + str(i))
                    self.grid_owned[i] = False
        self.plot(st.position_avg_price if st.position_size > 0 else NA, "Avg Entry", color=color.orange, linewidth=2)
