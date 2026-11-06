"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Velocity Breakout Strategy (VBS)
Author       : not stated
Source URL   : https://www.tradingview.com/script/m1JDhFR9
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, 100 % of equity, long only, 0.05 % commission). Four entry triggers, taken while flat: an EMA 20/50 golden cross with an uninterrupted higher low (the 12-bar low over the lowest low since the last bearish cross) and a run-up of at most 10 % ("A+" entry; a "risky" one when the higher-low rule is off), a reload (bullish trend, price touched the 20 EMA within 4 bars, in the discount of the 100-bar range, bullish shift or sweep, green ATR trail, armed by a close over the previous 5-bar high), and the breakout of a "master candle" consolidation (4 inside bars) in a bullish trend with a green ATR trail. The position closes when the UT-Bot style ATR trailing stop (3 ATR, 1.5 ATR once profitable inside an ADX squeeze) turns red or on a death cross.
Deviations from the original: none.
Not carried over: plots, labels, the point-of-control profile, the HUD and the pivot structure map (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class VelocityBreakout(Script):
    TITLE = "Velocity Breakout Strategy (VBS)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "m1JDhFR9", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/m1JDhFR9"}

    def init(self):
        i = self.input
        g = "Moving Averages & Trend"
        self.micro_length = i.int(9, "Micro EMA Length", group=g)
        self.fast_length = i.int(20, "Fast EMA Length", group=g)
        self.slow_length = i.int(50, "Slow EMA Length", group=g)
        g = "Smart Triggers & Structure"
        self.struct_window = i.int(12, "Real-Time Lookback (Micro)", group=g)
        self.strict_aplus = i.bool(True, "Require Higher Low for A+ Entry", group=g)
        self.max_chase_pct = i.float(10.0, "Max Run-up % (Chase Filter)", group=g)
        self.block_chop = i.bool(False, "Block Entries in Gray Chop Zone", group=g)
        g = "Master Candle Consolidation"
        self.consol_bars = i.int(4, "Required Follow-up Bars", group=g)
        self.use_master_wicks = i.bool(True, "Use Master High/Low Bounds", group=g)
        self.strict_trend_brk = i.bool(True, "Require Bull Trend & Green ATR for Breakout", group=g)
        g = "Smart Money Concepts (SMC)"
        self.smc_lookback = i.int(100, "Dealing Range Lookback", group=g)
        self.strict_smc = i.bool(True, "Require SMC Zone for Reloads", group=g)
        g = "Dynamic ATR Exits (ADX Squeeze)"
        self.atr_period = i.int(10, "ATR Period", group=g)
        self.atr_mult = i.float(3.0, "Base ATR Multiplier (Trend)", group=g)
        self.tight_atr_mult = i.float(1.5, "Tight ATR Multiplier (Chop)", group=g)
        self.adx_squeeze = i.int(20, "ADX Squeeze Threshold", group=g)
        self.x_trail = 0.0
        self.pos_state = 0
        self.m_top = NA
        self.m_bot = NA
        self.inside_count = 0
        self.consol_armed = False
        self.macro_bear_low = NA
        self.bull_armed = True

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        h_hi5 = self.H("hi5")
        hi5_1 = h_hi5[1]
        close_1 = self.close[1]
        micro_ema = ta.ema(close, self.micro_length)
        fast_ema = ta.ema(close, self.fast_length)
        slow_ema = ta.ema(close, self.slow_length)
        _, _, adx = ta.dmi(14, 14)
        is_tight_range = ta.atr(14) < ta.atr(50)
        is_bull_candle = close >= open_
        dr_high = ta.highest(high, self.smc_lookback)
        dr_low = ta.lowest(low, self.smc_lookback)
        dr_range = dr_high - dr_low
        upper_eq = dr_low + (dr_range * 0.60)
        in_discount = close <= upper_eq
        is_bullish_trend = fast_ema > slow_ema
        is_bearish_trend = fast_ema < slow_ema
        pos_size = st.position_size
        in_profit = pos_size > 0 and close > st.position_avg_price
        squeeze_active = (adx < self.adx_squeeze) and in_profit
        current_atr_mult = self.tight_atr_mult if squeeze_active else self.atr_mult
        n_loss = current_atr_mult * ta.atr(self.atr_period)
        prev = nz(self.x_trail, 0)
        if close > prev and close_1 > prev:
            x = pmath.max(prev, close - n_loss)
        elif close < prev and close_1 < prev:
            x = pmath.min(prev, close + n_loss)
        elif close > prev:
            x = close - n_loss
        else:
            x = close + n_loss
        pos_prev = self.pos_state
        if close_1 < prev and close > prev:
            self.pos_state = 1
        elif close_1 > prev and close < prev:
            self.pos_state = -1
        self.x_trail = float(x)
        pos = self.pos_state
        atr_is_green = pos == 1

        valid_trend_for_brk = (is_bullish_trend and atr_is_green) if self.strict_trend_brk else True
        is_breakout_up = self.consol_armed and close > self.m_top and is_bull_candle and valid_trend_for_brk
        take_consol_breakout = is_breakout_up and ((not self.block_chop) or not is_tight_range)
        if na(self.m_top) or close > self.m_top or close < self.m_bot:
            self.m_top = float(high) if self.use_master_wicks else pmath.max(open_, close)
            self.m_bot = float(low) if self.use_master_wicks else pmath.min(open_, close)
            self.inside_count = 0
            self.consol_armed = False
        else:
            self.inside_count += 1
        if self.inside_count >= self.consol_bars:
            self.consol_armed = True

        if self.bar_index == 0:
            self.macro_bear_low = float(low)
        golden_cross_raw = ta.crossover(fast_ema, slow_ema)
        death_cross_raw = ta.crossunder(fast_ema, slow_ema)
        if death_cross_raw:
            self.macro_bear_low = float(low)
        if not is_bullish_trend:
            self.macro_bear_low = pmath.min(self.macro_bear_low, low)
        golden_cross = golden_cross_raw
        death_cross = death_cross_raw
        recent_low = ta.lowest(low, self.struct_window)
        is_real_time_hl = recent_low > self.macro_bear_low
        valid_bull_structure = is_real_time_hl if self.strict_aplus else True
        run_up_pct = div(close - recent_low, recent_low) * 100
        valid_chase = run_up_pct <= self.max_chase_pct
        take_long_cross = golden_cross and valid_bull_structure and valid_chase and ((not self.block_chop) or not is_tight_range)
        take_risky_long = golden_cross and (not valid_bull_structure) and (not self.strict_aplus) and valid_chase and ((not self.block_chop) or not is_tight_range)

        hi5 = ta.highest(high, 5)
        if close > hi5_1:
            self.bull_armed = True
        body_size = abs(close - open_)
        lower_wick = pmath.min(open_, close) - low
        is_bull_sweep = (lower_wick > body_size * 1.5) and is_bull_candle
        valid_smc_bull = in_discount if self.strict_smc else True
        touched_ema = ta.lowest(low, 4) <= fast_ema
        bull_shift = close > fast_ema and is_bull_candle
        rt_bullish_reload = is_bullish_trend and self.bull_armed and touched_ema and valid_smc_bull and (bull_shift or is_bull_sweep) and atr_is_green and (not golden_cross) and ((not self.block_chop) or not is_tight_range)
        if rt_bullish_reload:
            self.bull_armed = False
        long_entry_condition = take_long_cross or take_risky_long or rt_bullish_reload or take_consol_breakout
        if long_entry_condition and pos_size == 0:
            st.entry("Long", st.long)
        visual_atr_exit = pos == -1 and pos_prev == 1
        if visual_atr_exit:
            st.close("Long", comment="Trail Exit")
        if death_cross:
            st.close("Long", comment="Macro Break")
        h_hi5.set(hi5)
