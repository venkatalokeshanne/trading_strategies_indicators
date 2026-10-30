"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Supertrend + Volatility Regime Switch (TrendShift | Supertrend + ADX Regime-Adaptive Strategy)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/TbK1rB5B-TrendShift-Supertrend-ADX-Regime-Adaptive-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ADX classes the market as trending (tight SuperTrend multiplier), choppy (wide multiplier) or neutral (keeps the last multiplier). SuperTrend direction flips open
(and reverse) positions with a risk-sized quantity (risk percent of equity over the distance to the SuperTrend line), except new entries are blocked while choppy. The optional trailing stop at the
SuperTrend line with an R-multiple target, the max-bars exit and the flatten-on-chop exit are inputs that are off by default; they are implemented as written but are not covered by the independent check (defaults only).

Deviations from the original: none.
Not carried over: the glow plots, fill, flip labels, regime background and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta

START_DATE = 1704067200000     # timestamp("1 Jan 2024 00:00") read as UTC
END_DATE = 1893456000000       # timestamp("1 Jan 2030 00:00") read as UTC


class SupertrendRegimeSwitch(Script):
    TITLE = "Supertrend + Volatility Regime Switch"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "TbK1rB5B", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TbK1rB5B-TrendShift-Supertrend-ADX-Regime-Adaptive-Strategy"}

    def init(self):
        g = "Regime Detection (ADX)"
        self.adx_len = self.input.int(14, "ADX / DI Length", group=g)
        self.adx_smooth = self.input.int(14, "ADX Smoothing", group=g)
        self.adx_trend_th = self.input.float(25, "Trending Threshold (ADX >)", group=g)
        self.adx_chop_th = self.input.float(20, "Choppy Threshold (ADX <)", group=g)
        g = "Supertrend"
        self.atr_len = self.input.int(10, "ATR Length", group=g)
        self.tight_mult = self.input.float(1.75, "Trending Multiplier (tight)", step=0.25, group=g)
        self.wide_mult = self.input.float(4.5, "Choppy Multiplier (wide)", step=0.25, group=g)
        self.disable_chop = self.input.bool(True, "Disable new entries in choppy regime", group=g)
        self.flatten_on_chop = self.input.bool(False, "Flatten open position if regime turns choppy", group=g)
        g = "Risk Management"
        self.use_trailing = self.input.bool(False, "Use trailing stop", group=g)
        self.risk_pct = self.input.float(1.0, "Risk per Trade (% of Equity)", minval=0.1, step=0.1, group=g)
        self.use_tp = self.input.bool(True, "Use Take Profit (R multiple)", group=g)
        self.r_multiple = self.input.float(2.0, "Take Profit (R multiple)", step=0.5, group=g)
        self.max_bars_in_trade = self.input.int(0, "Max Bars in Trade (0 = off)", minval=0, group=g)
        g = "Date Filter"
        self.use_date_filter = self.input.bool(False, "Use Date Filter", group=g)
        self.start_date = self.input.time(START_DATE, "Start Date", group=g)
        self.end_date = self.input.time(END_DATE, "End Date", group=g)
        self.regime = "NEUTRAL"
        self.effective_mult = self.tight_mult
        self.bars_in_trade = 0

    def on_bar(self):
        di_plus, di_minus, adx_val = ta.dmi(self.adx_len, self.adx_smooth)
        is_trending = adx_val > self.adx_trend_th
        is_choppy = adx_val < self.adx_chop_th
        if is_trending:
            self.regime = "TRENDING"
        elif is_choppy:
            self.regime = "CHOPPY"
        if self.regime == "TRENDING":
            self.effective_mult = self.tight_mult
        elif self.regime == "CHOPPY":
            self.effective_mult = self.wide_mult
        st_line, st_dir = ta.supertrend(self.effective_mult, self.atr_len)
        dir_change = ta.change(st_dir) != 0
        bull_flip = dir_change and st_dir == -1
        bear_flip = dir_change and st_dir == 1
        entries_allowed = not (is_choppy and self.disable_chop)
        long_signal = bull_flip and entries_allowed
        short_signal = bear_flip and entries_allowed
        in_date_range = (self.time >= self.start_date and self.time <= self.end_date) if self.use_date_filter else True
        st = self.strategy
        stop_dist = abs(self.close - st_line)
        risk_amt = st.equity * (self.risk_pct / 100)
        qty = div(risk_amt, stop_dist) if stop_dist > 0 else 0
        if in_date_range:
            if long_signal and st.position_size <= 0 and qty > 0:
                st.entry("Long", st.long, qty=qty, comment="LONG")
            if short_signal and st.position_size >= 0 and qty > 0:
                st.entry("Short", st.short, qty=qty, comment="SHORT")
        avg = st.position_avg_price
        long_tp = avg + stop_dist * self.r_multiple
        short_tp = avg - stop_dist * self.r_multiple
        if self.use_trailing and st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", stop=st_line, limit=long_tp if self.use_tp else NA)
        if self.use_trailing and st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", stop=st_line, limit=short_tp if self.use_tp else NA)
        if self.flatten_on_chop and is_choppy and st.position_size != 0:
            st.close_all(comment="Close (Choppy)")
        self.bars_in_trade = self.bars_in_trade + 1 if st.position_size != 0 else 0
        if self.max_bars_in_trade > 0 and self.bars_in_trade >= self.max_bars_in_trade and st.position_size != 0:
            st.close_all(comment="Max Bars Exit")
        self.plot(st_line, "Supertrend", color=color.green if st_dir == -1 else color.red, linewidth=2)
