"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fib Confluence Scanner (Fibonacci Cloud | Multi-Timeframe Fibonacci Scanner)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/rKsnPJbJ-Fibonacci-Cloud-Multi-Timeframe-Fibonacci-Scanner
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. For three lookbacks (20 / 50 / 100 bars) the five retracement levels (0.236, 0.382, 0.5, 0.618, 0.786 down from the lookback high) are
tested against the close; the number within the tolerance is the confluence count. With enough confluence and an EMA / RSI direction filter a position is
opened when flat, with a percent stop and an R:R target around the average price. fibLevels() holds ta.highest / ta.lowest state, so it is written out once per
lookback.

Deviations from the original: none.
Not carried over: confluence background, markers, trend fill and alert messages (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath, ta


class FibConfluenceScanner(Script):
    TITLE = "Fib Confluence Scanner"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "rKsnPJbJ", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/rKsnPJbJ-Fibonacci-Cloud-Multi-Timeframe-Fibonacci-Scanner"}

    def init(self):
        g = "Fibonacci Lookbacks"
        self.len_a = self.input.int(20, "Lookback A (short)", minval=2, group=g)
        self.len_b = self.input.int(50, "Lookback B (medium)", minval=2, group=g)
        self.len_c = self.input.int(100, "Lookback C (long)", minval=2, group=g)
        g = "Confluence Settings"
        self.tolerance = self.input.float(0.5, "Confluence Tolerance (%)", minval=0.01, step=0.01, group=g) / 100
        self.min_confluence = self.input.int(1, "Minimum Confluent Levels", minval=1, maxval=15, group=g)
        g = "Trend Filter"
        self.use_trend_filter = self.input.bool(True, "Use EMA Trend Filter", group=g)
        self.trend_len = self.input.int(50, "Trend EMA Length", minval=1, group=g)
        g = "RSI Filter"
        self.use_rsi_filter = self.input.bool(False, "Use RSI Momentum Filter", group=g)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1, group=g)
        self.rsi_long_min = self.input.int(45, "RSI Min for Longs", minval=0, maxval=100, group=g)
        self.rsi_short_max = self.input.int(55, "RSI Max for Shorts", minval=0, maxval=100, group=g)
        g = "Trade Management"
        self.trade_direction = self.input.string("Both", "Trade Direction", options=["Both", "Long Only", "Short Only"], group=g)
        self.sl_pct = self.input.float(1.5, "Stop Loss (%)", minval=0.1, step=0.1, group=g) / 100
        self.tp_rr = self.input.float(2.0, "Take Profit R:R", minval=0.1, step=0.1, group=g)
        self.one_trade = self.input.bool(True, "Only One Position At A Time", group=g)

    def _near(self, level):
        return div(pmath.abs(self.close - level), self.close) <= self.tolerance

    def on_bar(self):
        hi_a = ta.highest(self.high, self.len_a)
        lo_a = ta.lowest(self.low, self.len_a)
        hi_b = ta.highest(self.high, self.len_b)
        lo_b = ta.lowest(self.low, self.len_b)
        hi_c = ta.highest(self.high, self.len_c)
        lo_c = ta.lowest(self.low, self.len_c)
        count = 0
        for hi, lo in ((hi_a, lo_a), (hi_b, lo_b), (hi_c, lo_c)):
            rng = hi - lo
            for ratio in (0.236, 0.382, 0.5, 0.618, 0.786):
                if self._near(hi - ratio * rng):
                    count += 1
        confluence = count >= self.min_confluence
        ema_trend = ta.ema(self.close, self.trend_len)
        trend_up = self.close > ema_trend
        trend_dn = self.close < ema_trend
        rsi_val = ta.rsi(self.close, self.rsi_len)
        rsi_long_ok = (not self.use_rsi_filter) or rsi_val >= self.rsi_long_min
        rsi_short_ok = (not self.use_rsi_filter) or rsi_val <= self.rsi_short_max
        long_allowed = self.trade_direction != "Short Only"
        short_allowed = self.trade_direction != "Long Only"
        st = self.strategy
        position_free = st.position_size == 0 if self.one_trade else True
        long_condition = confluence and ((not self.use_trend_filter) or trend_up) and rsi_long_ok and long_allowed and position_free
        short_condition = confluence and ((not self.use_trend_filter) or trend_dn) and rsi_short_ok and short_allowed and position_free
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=avg * (1 - self.sl_pct), limit=avg * (1 + self.sl_pct * self.tp_rr))
        if st.position_size < 0:
            st.exit("Exit Short", "Short", stop=avg * (1 + self.sl_pct), limit=avg * (1 - self.sl_pct * self.tp_rr))
        self.plot(ema_trend if self.use_trend_filter else NA, "Trend EMA", color=color.gray)
