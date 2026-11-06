"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Growth Breakout Strategy v3 - EMA + RVOL + Stoch RSI
Author       : anders_k
Source URL   : https://www.tradingview.com/script/cIaYJiab-Growth-Breakout-Strategy-v3-EMA-RVOL-Stoch-RSI
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A consolidating stock near its 52-week high breaking above the previous N bars' high on relative volume, with EMA momentum and a bullish (but not overbought)
Stochastic RSI, buys at the close when flat. One of six exits applies: a close under the 50 EMA or 20 EMA, a percent stop (optionally with a target), or an ATR stop (optionally with a target). The stochastic's raw value is 0
whenever the RSI window's high equals its low or either is na, as Pine's na-false ternary gives.

Deviations from the original: none.
Not carried over: labels, the background, the EMA plots, alerts and the debug table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class GrowthBreakoutV3(Script):
    TITLE = "Growth Breakout Strategy v3 - EMA + RVOL + Stoch RSI"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, commission_type="percent", commission_value=0.0, slippage=0, process_orders_on_close=True)
    SOURCE = {"id": "cIaYJiab", "author": "anders_k", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cIaYJiab-Growth-Breakout-Strategy-v3-EMA-RVOL-Stoch-RSI"}

    def init(self):
        self.ema_fast_len = self.input.int(20, "Fast EMA Length", minval=1)
        self.ema_slow_len = self.input.int(50, "Slow EMA Length", minval=1)
        self.consolidation_pct = self.input.float(2.0, "Max Distance From Fast EMA (%)", minval=0.1, step=0.1)
        self.lookback_52w = self.input.int(252, "52-Week High Lookback Bars", minval=20)
        self.near_high_pct = self.input.float(5.0, "Max Distance Below 52-Week High (%)", minval=0.1, step=0.1)
        self.breakout_lookback = self.input.int(10, "Breakout Lookback Bars", minval=2)
        self.rvol_len = self.input.int(20, "RVOL Average Volume Length", minval=1)
        self.rvol_threshold = self.input.float(1.5, "Minimum Relative Volume", minval=0.1, step=0.1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.stoch_len = self.input.int(14, "Stochastic RSI Length", minval=1)
        self.k_smooth = self.input.int(3, "Stoch RSI K Smoothing", minval=1)
        self.d_smooth = self.input.int(3, "Stoch RSI D Smoothing", minval=1)
        self.stoch_max = self.input.float(80.0, "Max Stoch RSI For Entry", minval=1, maxval=100)
        self.use_stoch_filter = self.input.bool(True, "Use Stoch RSI Filter")
        self.use_ema_trend_filter = self.input.bool(True, "Use EMA Trend Filter")
        self.use_ema_cross_or_above = self.input.bool(True, "Allow Fast EMA Cross OR Close Above Fast EMA")
        self.exit_mode = self.input.string("50 EMA Crossunder", "Exit Mode", options=["50 EMA Crossunder", "20 EMA Crossunder", "Percent Stop", "Percent Stop + Target",
                                                                                     "ATR Stop", "ATR Stop + Target"])
        self.stop_loss_pct = self.input.float(7.0, "Stop Loss (%)", minval=0.1, step=0.1)
        self.take_profit_pct = self.input.float(15.0, "Take Profit (%)", minval=0.1, step=0.1)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.atr_stop_mult = self.input.float(2.5, "ATR Stop Multiplier", minval=0.1, step=0.1)
        self.atr_target_mult = self.input.float(4.0, "ATR Target Multiplier", minval=0.1, step=0.1)
        self.use_equity_sizing = self.input.bool(True, "Use Percent of Equity Position Sizing")
        self.position_pct = self.input.float(100.0, "Position Size % of Equity", minval=1.0, maxval=100.0, step=1.0)
        self.fixed_qty = self.input.float(1.0, "Fixed Share Quantity", minval=0.0001)

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        high52w = ta.highest(self.high, self.lookback_52w)
        avg_volume = ta.sma(self.volume, self.rvol_len)
        rvol = div(self.volume, avg_volume) if avg_volume > 0 else NA
        rsi_value = ta.rsi(self.close, self.rsi_len)
        rsi_lowest = ta.lowest(rsi_value, self.stoch_len)
        rsi_highest = ta.highest(rsi_value, self.stoch_len)
        stoch_raw = 100 * div(rsi_value - rsi_lowest, rsi_highest - rsi_lowest) if (not na(rsi_highest) and not na(rsi_lowest) and rsi_highest != rsi_lowest) else 0
        stoch_k = ta.sma(stoch_raw, self.k_smooth)
        stoch_d = ta.sma(stoch_k, self.d_smooth)
        atr = ta.atr(self.atr_len)
        distance_from_fast_ema_pct = div(pmath.abs(self.close - ema_fast), self.close) * 100
        is_consolidating = distance_from_fast_ema_pct <= self.consolidation_pct
        near_highs = self.close >= high52w * (1 - self.near_high_pct / 100)
        prior_breakout_high = ta.highest(self.high[1], self.breakout_lookback)
        price_breakout = self.close > prior_breakout_high
        volume_breakout = rvol >= self.rvol_threshold
        breakout = price_breakout and volume_breakout
        ema_trend_bullish = ema_fast > ema_slow
        ema_cross = ta.crossover(ema_fast, ema_slow)
        ema_momentum = (ema_cross or self.close > ema_fast) if self.use_ema_cross_or_above else ema_trend_bullish
        ema_filter_passed = ema_momentum if self.use_ema_trend_filter else True
        stoch_bullish = stoch_k > stoch_d and stoch_k < self.stoch_max
        stoch_filter_passed = stoch_bullish if self.use_stoch_filter else True
        long_condition = is_consolidating and near_highs and breakout and ema_filter_passed and stoch_filter_passed
        st = self.strategy
        can_enter = long_condition and st.position_size == 0
        qty = div(st.equity * (self.position_pct / 100), self.close) if self.use_equity_sizing else self.fixed_qty
        if can_enter:
            st.entry("Growth Long", st.long, qty=qty)
        in_position = st.position_size > 0
        entry_price = st.position_avg_price
        percent_stop_price = entry_price * (1 - self.stop_loss_pct / 100)
        percent_target_price = entry_price * (1 + self.take_profit_pct / 100)
        atr_stop_price = entry_price - atr * self.atr_stop_mult
        atr_target_price = entry_price + atr * self.atr_target_mult
        exit_on_50 = ta.crossunder(self.close, ema_slow)
        exit_on_20 = ta.crossunder(self.close, ema_fast)
        if in_position and self.exit_mode == "50 EMA Crossunder" and exit_on_50:
            st.close("Growth Long", comment="Exit 50 EMA")
        if in_position and self.exit_mode == "20 EMA Crossunder" and exit_on_20:
            st.close("Growth Long", comment="Exit 20 EMA")
        if in_position and self.exit_mode == "Percent Stop":
            st.exit("Percent Stop Exit", from_entry="Growth Long", stop=percent_stop_price)
        if in_position and self.exit_mode == "Percent Stop + Target":
            st.exit("Percent Stop Target Exit", from_entry="Growth Long", stop=percent_stop_price, limit=percent_target_price)
        if in_position and self.exit_mode == "ATR Stop":
            st.exit("ATR Stop Exit", from_entry="Growth Long", stop=atr_stop_price)
        if in_position and self.exit_mode == "ATR Stop + Target":
            st.exit("ATR Stop Target Exit", from_entry="Growth Long", stop=atr_stop_price, limit=atr_target_price)
        self.plot(ema_fast, "Fast EMA", color=color.blue, linewidth=2)
        self.plot(ema_slow, "Slow EMA", color=color.red, linewidth=2)
