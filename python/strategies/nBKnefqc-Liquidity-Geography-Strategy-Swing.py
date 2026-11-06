"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Liquidity Geography Strategy (Swing)
Author       : not stated
Source URL   : https://www.tradingview.com/script/nBKnefqc
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market entries at the next open, 10 % of equity unless risk-based sizing is on, 0.1 % commission, 2
ticks of slippage). Liquidity pools are the last confirmed pivot high / low (10 bars each side) or the N-day extremes up to the
previous bar. The sweep module goes long when a bar trades under the pool low and closes back above it (short mirrored), subject to the
regime filter (balance = the 20-bar EMA moved less than 2 ATR in 20 bars; the default also accepts trend entries that agree with a
weekly EMA(20) bias, weekly value with lookahead off), optional confluence with the prior day's extreme or a round number; stop
0.25 ATR beyond the bar, target 2 R (or the opposite pool). The gap-fill module (off by default) fades 1 % gaps back to the previous close.
Quirk kept: the stop / target prices of the exit order are those of the signal bar, not of the fill.
Deviations from the original: none.
Not carried over: terrain drawings (FVG / order-block boxes, structure labels, premium-discount zones), plots, tables.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


def _na(x):
    return x != x


class LiquidityGeography(Script):
    TITLE = "Liquidity Geography Strategy (Swing)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.1,
                    slippage=2, initial_capital=100000, currency="USD")
    SOURCE = {"id": "nBKnefqc", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/nBKnefqc"}

    def init(self):
        i = self.input
        self.atr_length = i.int(14, "ATR length", group="General")
        self.max_hold_bars = i.int(0, "Max holding bars (0 = off)", minval=0, group="General")
        self.auto_round_step = i.bool(True, "Auto round-number step (by price)", group="Terrain (drawing)")
        self.round_step_manual = i.float(1.0, "Manual round-number step", group="Terrain (drawing)")
        self.pool_source = i.string("Pivot", "Liquidity pool source", options=["Pivot", "N-day high/low"], group="Liquidity Pools / Structure")
        self.nday_length = i.int(20, "N-day high/low lookback (bars)", minval=1, group="Liquidity Pools / Structure")
        self.pivot_length = i.int(10, "Pivot length (left/right bars)", group="Liquidity Pools / Structure")
        self.gap_enabled = i.bool(False, "Enable Gap-Fill module", group="Gap-Fill Module")
        self.gap_longs = i.bool(True, "Longs (gap-down fill)", group="Gap-Fill Module")
        self.gap_shorts = i.bool(True, "Shorts (gap-up fill)", group="Gap-Fill Module")
        self.min_gap_percent = i.float(1.0, "Min gap size %", minval=0.0, group="Gap-Fill Module") / 100.0
        self.use_range_filter = i.bool(True, "Range filter (skip trends)", group="Gap-Fill Module")
        self.range_ema_length = i.int(20, "Range filter EMA length", group="Gap-Fill Module")
        self.max_trend_atr = i.float(2.0, "Max EMA travel in ATR (above = trend, skip)", group="Gap-Fill Module")
        self.gap_stop_atr = i.float(1.0, "Gap stop ATR multiple", group="Gap-Fill Module")
        self.sweep_enabled = i.bool(True, "Enable Sweep module", group="Liquidity Sweep Module")
        self.sweep_longs = i.bool(True, "Longs (sweep low-side)", group="Liquidity Sweep Module")
        self.sweep_shorts = i.bool(True, "Shorts (sweep high-side)", group="Liquidity Sweep Module")
        self.stop_buffer_atr = i.float(0.25, "Sweep stop buffer (ATR multiple)", group="Liquidity Sweep Module")
        self.risk_reward = i.float(2.0, "Risk:reward (target = RR x risk)", group="Liquidity Sweep Module")
        self.use_opposite_liquidity = i.bool(False, "Target = opposite liquidity (overrides RR)", group="Liquidity Sweep Module")
        self.regime_mode = i.string("Adaptive (fade in balance, follow trend)", "Sweep regime filter (Tier 1)",
                                    options=["Off", "Balance only", "Trend-aligned only", "Adaptive (fade in balance, follow trend)"],
                                    group="Optimization Filters")
        self.htf_bias_tf = i.timeframe("W", "Higher-timeframe bias", group="Optimization Filters")
        self.htf_bias_len = i.int(20, "Higher-timeframe EMA length", group="Optimization Filters")
        self.regime_ema_len = i.int(20, "Regime EMA length (this timeframe)", group="Optimization Filters")
        self.regime_trend_atr = i.float(2.0, "Trend threshold: EMA travel in ATR", group="Optimization Filters")
        self.require_confluence = i.bool(False, "Require confluence (Tier 2)", group="Optimization Filters")
        self.confluence_tol_atr = i.float(0.5, "Confluence tolerance (ATR)", group="Optimization Filters")
        self.risk_based_sizing = i.bool(False, "Risk-based position sizing (Tier 3)", group="Risk Sizing")
        self.risk_percent = i.float(1.0, "Risk % of equity per trade", minval=0.0, group="Risk Sizing") / 100.0
        # var state
        self.last_pivot_high = NA
        self.last_pivot_low = NA

    def on_bar(self):
        close, open_, high, low = float(self.close), float(self.open), float(self.high), float(self.low)

        atr_value = ta.atr(self.atr_length)
        pivot_high = ta.pivothigh(self.high, self.pivot_length, self.pivot_length)
        pivot_low = ta.pivotlow(self.low, self.pivot_length, self.pivot_length)
        if not _na(pivot_high):
            self.last_pivot_high = float(pivot_high)
        if not _na(pivot_low):
            self.last_pivot_low = float(pivot_low)

        nday_high_now = ta.highest(self.high, self.nday_length)
        nday_low_now = ta.lowest(self.low, self.nday_length)
        nday_high = self.H("nh")[1]
        nday_low = self.H("nl")[1]
        self.H("nh").set(nday_high_now)
        self.H("nl").set(nday_low_now)
        liq_high = self.last_pivot_high if self.pool_source == "Pivot" else nday_high
        liq_low = self.last_pivot_low if self.pool_source == "Pivot" else nday_low

        bullish_sweep = (not _na(liq_low)) and low < liq_low and close > liq_low
        bearish_sweep = (not _na(liq_high)) and high > liq_high and close < liq_high

        range_ema = ta.ema(self.close, self.range_ema_length)
        range_back = self.H("rema")[self.range_ema_length]
        self.H("rema").set(range_ema)
        ema_travel_in_atr = div(pmath.abs(range_ema - range_back), atr_value)
        is_ranging = (not self.use_range_filter) or ema_travel_in_atr < self.max_trend_atr
        prev_close = self.close[1]
        gap_up = open_ > prev_close * (1 + self.min_gap_percent)
        gap_down = open_ < prev_close * (1 - self.min_gap_percent)
        round_step = pmath.pow(10, pmath.floor(pmath.log10(close))) if self.auto_round_step else self.round_step_manual

        prior_day_high, prior_day_low = self.security(self.syminfo.tickerid, "D", lambda v: (v.high[1], v.low[1]), lookahead=True)

        bias_ema = self.security(self.syminfo.tickerid, self.htf_bias_tf, lambda v: ta.ema(v.close, self.htf_bias_len), lookahead=False)
        bias_up = (not _na(bias_ema)) and close > bias_ema
        bias_down = (not _na(bias_ema)) and close < bias_ema
        regime_ema = ta.ema(self.close, self.regime_ema_len)
        regime_back = self.H("gema")[self.regime_ema_len]
        self.H("gema").set(regime_ema)
        regime_travel_atr = div(pmath.abs(regime_ema - regime_back), atr_value)
        is_trending = regime_travel_atr >= self.regime_trend_atr
        is_balance = not is_trending
        rm = self.regime_mode
        long_regime_ok = True if rm == "Off" else is_balance if rm == "Balance only" else bias_up if rm == "Trend-aligned only" else (is_balance or bias_up)
        short_regime_ok = True if rm == "Off" else is_balance if rm == "Balance only" else bias_down if rm == "Trend-aligned only" else (is_balance or bias_down)

        conf_tol = self.confluence_tol_atr * atr_value
        if (not self.require_confluence) or _na(liq_low):
            long_confluence = True
        else:
            long_confluence = pmath.abs(liq_low - prior_day_low) <= conf_tol \
                or pmath.abs(liq_low - pmath.round(div(liq_low, round_step)) * round_step) <= conf_tol
        if (not self.require_confluence) or _na(liq_high):
            short_confluence = True
        else:
            short_confluence = pmath.abs(liq_high - prior_day_high) <= conf_tol \
                or pmath.abs(liq_high - pmath.round(div(liq_high, round_step)) * round_step) <= conf_tol

        st = self.strategy
        took_trade_this_bar = False
        if self.gap_enabled and st.position_size == 0:
            if gap_down and is_ranging and self.gap_longs:
                gap_stop = close - self.gap_stop_atr * atr_value
                gap_qty = div(st.equity * self.risk_percent, close - gap_stop) if (self.risk_based_sizing and (close - gap_stop) > 0) else NA
                st.entry("Gap Long", st.long, qty=gap_qty)
                st.exit("Gap Long Exit", from_entry="Gap Long", limit=prev_close, stop=gap_stop)
                took_trade_this_bar = True
            elif gap_up and is_ranging and self.gap_shorts:
                gap_stop = close + self.gap_stop_atr * atr_value
                gap_qty = div(st.equity * self.risk_percent, gap_stop - close) if (self.risk_based_sizing and (gap_stop - close) > 0) else NA
                st.entry("Gap Short", st.short, qty=gap_qty)
                st.exit("Gap Short Exit", from_entry="Gap Short", limit=prev_close, stop=gap_stop)
                took_trade_this_bar = True
        if self.sweep_enabled and st.position_size == 0 and not took_trade_this_bar:
            if bullish_sweep and self.sweep_longs and long_regime_ok and long_confluence:
                stop_price = low - self.stop_buffer_atr * atr_value
                risk_per_unit = close - stop_price
                target = liq_high if (self.use_opposite_liquidity and not _na(liq_high) and liq_high > close) \
                    else close + self.risk_reward * risk_per_unit
                sweep_qty = div(st.equity * self.risk_percent, risk_per_unit) if (self.risk_based_sizing and risk_per_unit > 0) else NA
                st.entry("Sweep Long", st.long, qty=sweep_qty)
                st.exit("Sweep Long Exit", from_entry="Sweep Long", stop=stop_price, limit=target)
            elif bearish_sweep and self.sweep_shorts and short_regime_ok and short_confluence:
                stop_price = high + self.stop_buffer_atr * atr_value
                risk_per_unit = stop_price - close
                target = liq_low if (self.use_opposite_liquidity and not _na(liq_low) and liq_low < close) \
                    else close - self.risk_reward * risk_per_unit
                sweep_qty = div(st.equity * self.risk_percent, risk_per_unit) if (self.risk_based_sizing and risk_per_unit > 0) else NA
                st.entry("Sweep Short", st.short, qty=sweep_qty)
                st.exit("Sweep Short Exit", from_entry="Sweep Short", stop=stop_price, limit=target)

        bars_held = self.bar_index - st.opentrades_entry_bar_index(0) if st.position_size != 0 else 0
        if self.max_hold_bars > 0 and st.position_size != 0 and bars_held >= self.max_hold_bars:
            st.close_all(comment="Time stop")

        self.plot(range_ema, title="Range EMA")
