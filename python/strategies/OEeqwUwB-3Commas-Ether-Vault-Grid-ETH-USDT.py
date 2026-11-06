"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [3Commas] Ether Vault Grid - ETH/USDT
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/OEeqwUwB-3Commas-Ether-Vault-Grid-ETH-USDT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas static grid bot: 28 levels between 1625.56 and 2258.88 (Geometric spacing). After a bar closes, any held slot whose upper level was just crossed upward is closed (sells first), then any free slot
whose level was just crossed downward is bought (one fixed amount per slot, fills at the next open). An optional trail-up shifts the grid when the close exceeds the high by a threshold. (Family member of the other 3Commas static grids; same logic, different instrument bounds / levels / sizing / window.)

Deviations from the original: none.
Not carried over: the webhook text, grid lines, stats card, watermark and timeframe warning (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, div, nz, pmath

START_TS = 1768608000000     # timestamp("2026-01-17 00:00 +0000")
END_TS = 1779062340000       # timestamp("2026-05-17 23:59 +0000")


class StaticGridOEeqwUwB(Script):
    TITLE = "[3Commas] Ether Vault Grid - ETH/USDT"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=100, initial_capital=6000, default_qty_type="cash", default_qty_value=178.57, commission_type="percent",
                    commission_value=0.1, slippage=2)
    SOURCE = {"id": "OEeqwUwB", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/OEeqwUwB-3Commas-Ether-Vault-Grid-ETH-USDT"}

    def init(self):
        g = "Grid Range"
        self.high_px = self.input.float(2258.88, "Grid High Price", step=0.01, group=g)
        self.low_px = self.input.float(1625.56, "Grid Low Price", step=0.01, group=g)
        self.levels = self.input.int(28, "Grid Levels", minval=2, maxval=100, group=g)
        self.grid_mode = self.input.string("Geometric", "Grid Mode", options=["Geometric", "Arithmetic"], group=g)
        g = "Sizing"
        self.amount_per_level = self.input.float(178.57, "Amount per Level (USDT)", minval=0.01, step=0.01, group=g)
        self.investment = self.input.float(5000.0, "Total Investment (USDT, ref)", minval=0.01, step=1, group=g)
        g = "Behavior"
        self.trail_up = self.input.bool(False, "Trailing Up — shift grid when price exceeds High", group=g)
        self.trail_up_thr = self.input.float(3.0, "Trail Up Threshold % above High", minval=0.1, step=0.1, group=g)
        self.trail_shift_pct = self.input.float(50, "Shift Up Magnitude % of range", minval=1, maxval=100, step=1, group=g)
        g = "Backtest Period"
        self.use_dates = self.input.bool(True, "Limit by Date Range", group=g)
        self.start_ts = self.input.time(START_TS, "Start", group=g)
        self.end_ts = self.input.time(END_TS, "End", group=g)
        self.cur_high = self.high_px
        self.cur_low = self.low_px
        self.grid_levels = [0.0] * self.levels
        self.filled = [False] * self.levels

    def f_compute_levels(self):
        for i in range(0, self.levels):
            ratio = div(i, self.levels - 1.0)
            if self.grid_mode == "Geometric":
                lvl = self.cur_low * pmath.pow(div(self.cur_high, self.cur_low), ratio)
            else:
                lvl = self.cur_low + (self.cur_high - self.cur_low) * ratio
            self.grid_levels[i] = lvl

    def on_bar(self):
        in_window = (not self.use_dates) or (self.time >= self.start_ts and self.time <= self.end_ts)
        if self.barstate.isfirst:
            self.f_compute_levels()
        if self.trail_up and in_window and self.close > self.cur_high * (1.0 + self.trail_up_thr / 100.0):
            rng = self.cur_high - self.cur_low
            shift = rng * self.trail_shift_pct / 100.0
            self.cur_high = self.cur_high + shift
            self.cur_low = self.cur_low + shift
            self.f_compute_levels()
        close = S(self.close)
        st = self.strategy
        if in_window and self.bar_index > 0:
            for i in range(0, self.levels - 1):
                if self.filled[i]:
                    sell_lvl = self.grid_levels[i + 1]
                    if self.close >= sell_lvl and close[1] < sell_lvl:
                        st.close("B" + str(i), comment="Grid Sell L" + str(i))
                        self.filled[i] = False
            for i in range(0, self.levels):
                if not self.filled[i]:
                    buy_lvl = self.grid_levels[i]
                    if self.close <= buy_lvl and close[1] > buy_lvl:
                        qty = div(self.amount_per_level, buy_lvl)
                        st.entry("B" + str(i), st.long, qty=qty, comment="Grid Buy L" + str(i))
                        self.filled[i] = True
