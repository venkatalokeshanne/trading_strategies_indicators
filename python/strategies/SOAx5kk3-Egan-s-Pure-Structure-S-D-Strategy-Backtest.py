"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Pure Structure & S/D Strategy - Backtest
Author       : briancurry
Source URL   : https://www.tradingview.com/script/SOAx5kk3-Egan-s-Pure-Structure-S-D-Strategy-Backtest
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Market structure from pivot highs / lows: a close through the latest swing high (low) is a break of structure that flips the structure bullish (bearish) and records a demand (supply) zone at the last down (up) candle of the previous 30 bars.
A touch of the zone in the structure's direction (with the macro EMA) arms a setup; the next confirmation candle (bullish and closing above the previous high) enters at the next open while flat, with the stop at the zone edge and the target at the latest swing, if the reward / risk is at least the minimum.
The bracket is placed with the entry.

Deviations from the original: none.
Not carried over: the zone and risk / reward boxes and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

import math

from pinelib import NA, Script, div, na, ta


class PureStructureSd(Script):
    TITLE = "Pure Structure & S/D Strategy - Backtest"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, margin_long=10, margin_short=10, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "SOAx5kk3", "author": "briancurry", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SOAx5kk3-Egan-s-Pure-Structure-S-D-Strategy-Backtest"}

    def init(self):
        g = "Backtest Window"
        self.start_time = self.input.time(self.timestamp("UTC", 2023, 1, 1, 0, 0), "Start Date", group=g)
        self.end_time = self.input.time(self.timestamp("UTC", 2099, 1, 1, 0, 0), "End Date", group=g)
        g = "Market Structure"
        self.ms_len = self.input.int(10, "Pivot Lookback", minval=1, group=g)
        self.min_rr = self.input.float(1.5, "Minimum Risk:Reward", minval=0.1, step=0.1, group=g)
        g = "Filters"
        self.use_filter = self.input.bool(True, "Use Macro Trend Filter", group=g)
        self.ema_len_filter = self.input.int(200, "Macro EMA Length", minval=1, group=g)
        self.use_confirmation = self.input.bool(True, "Wait for Confirmation Candle", group=g)
        g = "Strategy Logic"
        self.qty_mode = self.input.string("Risk %", "Quantity Mode", options=["Risk %", "Fixed Contracts"], group=g)
        self.risk_per_trade = self.input.float(1.0, "Risk % Per Trade", minval=0.1, maxval=10.0, group=g)
        self.fixed_qty = self.input.float(1.0, "Fixed Contracts/Units", minval=0.1, group=g)
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.valid_high = NA
        self.valid_low = NA
        self.structure_bullish = False
        self.demand = None
        self.supply = None
        self.waiting_long = False
        self.waiting_short = False

    def f_get_qty(self, risk_p, sl_dist):
        st = self.strategy
        if self.qty_mode == "Fixed Contracts":
            qty = self.fixed_qty
        else:
            risk_val = st.equity * (risk_p / 100)
            qty = div(risk_val, sl_dist * self.syminfo.pointvalue)
        if self.syminfo.type == "futures":
            qty = math.floor(qty)
        return max(qty, 0)

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        in_window = self.time >= self.start_time and self.time <= self.end_time
        macro_ema = ta.ema(close, self.ema_len_filter)
        macro_bull = close > macro_ema
        macro_bear = close < macro_ema
        ph = ta.pivothigh(self.ms_len, self.ms_len)
        pl = ta.pivotlow(self.ms_len, self.ms_len)
        if not na(ph):
            self.last_swing_high = ph
        if not na(pl):
            self.last_swing_low = pl
        bos_bull = ta.crossover(close, self.last_swing_high)
        bos_bear = ta.crossunder(close, self.last_swing_low)
        if bos_bull:
            self.valid_low = self.last_swing_low
            self.structure_bullish = True
        if bos_bear:
            self.valid_high = self.last_swing_high
            self.structure_bullish = False
        trend_bull = self.structure_bullish and (na(self.valid_low) or close > self.valid_low)
        trend_bear = (not self.structure_bullish) and (na(self.valid_high) or close < self.valid_high)
        if bos_bull and trend_bull:
            search_idx = 0
            for k in range(1, 31):
                if open_[k] > close[k]:
                    search_idx = k
                    break
            self.demand = (high[search_idx], low[search_idx])
        if bos_bear and trend_bear:
            search_idx = 0
            for k in range(1, 31):
                if open_[k] < close[k]:
                    search_idx = k
                    break
            self.supply = (high[search_idx], low[search_idx])
        d_top, d_bot = self.demand if self.demand is not None else (NA, NA)
        s_top, s_bot = self.supply if self.supply is not None else (NA, NA)
        touching_demand = self.demand is not None and low <= d_top and high >= d_bot
        touching_supply = self.supply is not None and high >= s_bot and low <= s_top
        if trend_bull and touching_demand and ((not self.use_filter) or macro_bull):
            self.waiting_long = True
        if (not trend_bull) or (self.demand is not None and close < d_bot):
            self.waiting_long = False
        if trend_bear and touching_supply and ((not self.use_filter) or macro_bear):
            self.waiting_short = True
        if (not trend_bear) or (self.supply is not None and close > s_top):
            self.waiting_short = False
        trigger_long = touching_demand if not self.use_confirmation else (self.waiting_long and close > open_ and close > high[1])
        trigger_short = touching_supply if not self.use_confirmation else (self.waiting_short and close < open_ and close < low[1])
        if in_window and trigger_long and self.waiting_long and st.position_size == 0:
            sl = d_bot
            tp = self.last_swing_high
            risk_dist = abs(close - sl)
            rr = div(abs(tp - close), risk_dist) if risk_dist > 0 else 0
            if rr >= self.min_rr:
                q = self.f_get_qty(self.risk_per_trade, risk_dist)
                if q > 0:
                    st.entry("Long", st.long, qty=q)
                    st.exit("Exit", "Long", stop=sl, limit=tp)
                    self.waiting_long = False
        if in_window and trigger_short and self.waiting_short and st.position_size == 0:
            sl = s_top
            tp = self.last_swing_low
            risk_dist = abs(sl - close)
            rr = div(abs(close - tp), risk_dist) if risk_dist > 0 else 0
            if rr >= self.min_rr:
                q = self.f_get_qty(self.risk_per_trade, risk_dist)
                if q > 0:
                    st.entry("Short", st.short, qty=q)
                    st.exit("Exit", "Short", stop=sl, limit=tp)
                    self.waiting_short = False
