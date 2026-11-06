"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Concord Execution Mandate [JOAT]
Author       : not stated
Source URL   : https://www.tradingview.com/script/iLXxAcTj
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation, orders fill at the bar close (process_orders_on_close), 5 % of equity, 0.02 % commission, 2 ticks of
slippage. A range filter (ATR(18) x an efficiency-ratio dependent multiplier) gives a trend; the "locked" regime only flips after the
raw trend disagreed for the adaptive number of confirmation bars. Long triggers are a break of the last pivot high with displacement and
a fair-value gap in the last three bars, a continuation cross of the range filter, or a rotation cross of the daily pivot / EMA basis /
EMA21; they need soft context, the soft regime gate (aggressive entries make it always open), one of four alignment votes and the
optional divergence block. The stop is the last pivot low (or 1.6 ATR) with a 2.2 R target and an ATR trail after 1 R; a flip of the
locked regime or the EMA weave bias closes the position.
Inputs that depend on higher timeframes: the 4-hour close / EMA55 and the previous day's high / low / close are requested with lookahead
on and shifted by one bar.
Deviations from the original: none.
Not carried over: dashboard table, bar colouring, plots, alerts.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


def _na(x):
    return x != x


def _nz(x, y=0.0):
    return y if x != x else x


class ConcordExecutionMandate(Script):
    TITLE = "Concord Execution Mandate [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, currency="USD", pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=5,
                    commission_type="percent", commission_value=0.02, slippage=2, process_orders_on_close=True)
    SOURCE = {"id": "iLXxAcTj", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/iLXxAcTj"}

    def init(self):
        i = self.input
        g = "Regime Engine"
        self.regime_source = i.source(self.close, "Regime Source", group=g)
        self.range_length = i.int(18, "Range Length", minval=5, group=g)
        self.range_multiplier = i.float(1.25, "Range Multiplier", minval=0.2, step=0.05, group=g)
        self.efficiency_length = i.int(14, "Efficiency Length", minval=5, group=g)
        self.confirm_base = i.int(2, "Base Confirm Bars", minval=1, maxval=6, group=g)
        g = "Trend And Context"
        self.adx_length = i.int(14, "ADX Length", minval=5, group=g)
        self.adx_floor = i.float(18.0, "ADX Floor", minval=5.0, step=0.5, group=g)
        self.chop_length = i.int(14, "Choppiness Length", minval=5, group=g)
        self.chop_ceiling = i.float(61.8, "Choppiness Ceiling", minval=35.0, maxval=80.0, step=0.5, group=g)
        self.htf_timeframe = i.timeframe("240", "HTF Timeframe", group=g)
        self.htf_ema_length = i.int(55, "HTF EMA Length", minval=5, group=g)
        self.use_htf_gate = i.bool(False, "Use HTF As Hard Gate", group=g)
        g = "Structure Trigger"
        self.swing_length = i.int(9, "Swing Length", minval=2, group=g)
        self.require_displacement = i.bool(True, "Require Displacement With Break", group=g)
        self.displacement_factor = i.float(1.0, "Displacement Threshold (ATR)", minval=0.2, step=0.1, group=g)
        self.continuation_entries = i.bool(True, "Allow Continuation Entries", group=g)
        g = "Execution Refinement"
        self.reversion_length = i.int(20, "Reversion Length", minval=5, group=g)
        self.reversion_mult = i.float(1.6, "Reversion Deviation", minval=0.5, step=0.1, group=g)
        self.require_reclaim = i.bool(True, "Require Intrabar Reclaim", group=g)
        self.aggressive_entries = i.bool(True, "Allow Aggressive Rotation Entries", group=g)
        g = "Divergence Safety"
        self.rsi_length = i.int(14, "RSI Length", minval=5, group=g)
        self.div_pivot_length = i.int(3, "Divergence Pivot Length", minval=2, maxval=8, group=g)
        self.div_window = i.int(50, "Divergence Window", minval=10, maxval=120, group=g)
        self.div_block_bars = i.int(20, "Divergence Block Bars", minval=1, maxval=80, group=g)
        self.use_divergence_block = i.bool(False, "Use Divergence Block Filter", group=g)
        g = "Risk Controls"
        self.atr_stop_multiple = i.float(1.6, "ATR Stop Multiple", minval=0.5, step=0.1, group=g)
        self.reward_multiple = i.float(2.2, "Reward Multiple", minval=0.5, step=0.1, group=g)
        self.trail_after_r = i.float(1.0, "Start Trail After R", minval=0.5, step=0.1, group=g)
        self.trail_multiple = i.float(1.2, "ATR Trail Multiple", minval=0.5, step=0.1, group=g)
        # var state
        self.filtered = NA          # f_range_state: var float filtered = source (first bar)
        self.trend = 0
        self.locked_regime = 0
        self.candidate_bars = 0
        self.last_bear_div_bar = NA
        self.last_bull_div_bar = NA
        self.prev_div_high_price = self.prev_div_high_rsi = self.prev_div_high_bar = NA
        self.prev_div_low_price = self.prev_div_low_rsi = self.prev_div_low_bar = NA
        self.htf_ema_prev = NA      # security state: previous higher-timeframe EMA(55)

    def _htf_ema(self, v):
        """ta.ema(close, n)[1] on the requested timeframe."""
        prev = self.htf_ema_prev
        self.htf_ema_prev = ta.ema(v.close, self.htf_ema_length)
        return prev

    def on_bar(self):
        close, open_, high, low = float(self.close), float(self.open), float(self.high), float(self.low)
        bi = self.bar_index
        src = self.regime_source
        src_now = float(src)

        # f_er
        er_len = self.efficiency_length
        net_move = pmath.abs(src_now - src[er_len])
        path = 0.0
        for k in range(er_len):
            path += pmath.abs(src[k] - src[k + 1]) if k > 0 else pmath.abs(src_now - src[1])
        er_raw = (div(net_move, path) if path > 0 else 0.0)
        er_value = ta.ema(er_raw, 3)
        if er_value < 0.22:
            adaptive_confirm = max(self.confirm_base + 2, 4)
        elif er_value < 0.42:
            adaptive_confirm = self.confirm_base + 1
        elif er_value < 0.68:
            adaptive_confirm = self.confirm_base
        else:
            adaptive_confirm = max(self.confirm_base - 1, 1)
        adaptive_range_mult = self.range_multiplier * (1.15 if er_value < 0.25 else 0.85 if er_value > 0.70 else 1.0)

        # f_range_state
        atr_value = ta.atr(self.range_length)
        buffer = atr_value * adaptive_range_mult
        if self.bar_index == 0:
            self.filtered = src_now
        filtered_prev = self.H("filt")[1]
        if src_now > self.filtered + buffer:
            self.filtered = src_now - buffer
        elif src_now < self.filtered - buffer:
            self.filtered = src_now + buffer
        self.H("filt").set(self.filtered)
        if self.filtered > filtered_prev:
            self.trend = 1
        elif self.filtered < filtered_prev:
            self.trend = -1
        regime_filter, raw_regime = self.filtered, self.trend

        if self.barstate.isfirst:
            self.locked_regime = 1 if raw_regime == 0 else raw_regime
        self.candidate_bars = self.candidate_bars + 1 if raw_regime != self.locked_regime else 0
        confirmed_shift = self.barstate.isconfirmed and raw_regime != 0 and raw_regime != self.locked_regime \
            and self.candidate_bars >= adaptive_confirm
        if confirmed_shift:
            self.locked_regime = raw_regime
            self.candidate_bars = 0
        locked = self.locked_regime

        # f_adx
        up_move = high - self.high[1]
        down_move = self.low[1] - low
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
        tr1 = ta.atr(1)
        plus_di = 100 * div(ta.rma(plus_dm, self.adx_length), ta.rma(tr1, self.adx_length))
        minus_di = 100 * div(ta.rma(minus_dm, self.adx_length), ta.rma(tr1, self.adx_length))
        dx = (div(pmath.abs(plus_di - minus_di), plus_di + minus_di) * 100) if (plus_di + minus_di) > 0 else 0.0
        adx_value = ta.rma(dx, self.adx_length)

        chop_range = ta.highest(self.high, self.chop_length) - ta.lowest(self.low, self.chop_length)
        chop_sum = ta.msum(ta.atr(1), self.chop_length)
        chop_value = (100 * div(pmath.log10(div(chop_sum, chop_range)), pmath.log10(self.chop_length))) if chop_range > 0 else 50.0

        htf_close = self.security(self.syminfo.tickerid, self.htf_timeframe, lambda v: v.close[1], lookahead=True)
        htf_ema = self.security(self.syminfo.tickerid, self.htf_timeframe, self._htf_ema, lookahead=True)
        htf_bias = 1 if htf_close > htf_ema else -1

        regime_quality = (1 if adx_value >= self.adx_floor else 0) + (1 if chop_value <= self.chop_ceiling else 0) \
            + (1 if htf_bias == locked else 0)
        regime_soft_open = (regime_quality >= 1 or self.aggressive_entries) and ((not self.use_htf_gate) or htf_bias == locked)

        prev_day_high, prev_day_low, prev_day_close = self.security(
            self.syminfo.tickerid, "D", lambda v: (v.high[1], v.low[1], v.close[1]), lookahead=True)
        day_pivot = (prev_day_high + prev_day_low + prev_day_close) / 3.0
        ema_21 = ta.ema(self.close, 21)
        ema_55 = ta.ema(self.close, 55)
        ema_89 = ta.ema(self.close, 89)
        weave_center = (ema_21 + ema_55 + ema_89) / 3.0
        wc_2 = self.H("wc")[2]
        self.H("wc").set(weave_center)
        if close > day_pivot and ema_21 > ema_55 and weave_center > wc_2:
            weave_bias = 1
        elif close < day_pivot and ema_21 < ema_55 and weave_center < wc_2:
            weave_bias = -1
        else:
            weave_bias = 0

        sw = self.swing_length
        ph = ta.pivothigh(self.high, sw, sw)
        pl = ta.pivotlow(self.low, sw, sw)
        last_pivot_high = ta.valuewhen(not _na(ph), ph, 0)
        last_pivot_low = ta.valuewhen(not _na(pl), pl, 0)
        recent_low_1 = ta.valuewhen(not _na(pl), pl, 0)
        recent_low_2 = ta.valuewhen(not _na(pl), pl, 1)
        recent_high_1 = ta.valuewhen(not _na(ph), ph, 0)
        recent_high_2 = ta.valuewhen(not _na(ph), ph, 1)

        bull_fvg = low > self.high[2]
        bear_fvg = high < self.low[2]
        bf1, bf2 = self.H("bf")[1] == 1, self.H("bf")[2] == 1
        sf1, sf2 = self.H("sf")[1] == 1, self.H("sf")[2] == 1
        self.H("bf").set(1.0 if bull_fvg else 0.0)
        self.H("sf").set(1.0 if bear_fvg else 0.0)
        displacement_ok = (not self.require_displacement) or pmath.abs(close - open_) >= atr_value * self.displacement_factor
        close_1 = self.close[1]
        bull_bos = self.barstate.isconfirmed and (not _na(last_pivot_high)) and close > last_pivot_high \
            and close_1 <= last_pivot_high and displacement_ok
        bear_bos = self.barstate.isconfirmed and (not _na(last_pivot_low)) and close < last_pivot_low \
            and close_1 >= last_pivot_low and displacement_ok

        if (not _na(recent_low_1)) and (not _na(recent_low_2)) and recent_low_1 > recent_low_2:
            geometry_bias = 1
        elif (not _na(recent_high_1)) and (not _na(recent_high_2)) and recent_high_1 < recent_high_2:
            geometry_bias = -1
        else:
            geometry_bias = 0

        reversion_basis = ta.ema(self.close, self.reversion_length)
        reversion_dev = ta.stdev(self.close, self.reversion_length) * self.reversion_mult
        long_reclaim = (not self.require_reclaim) or (low < reversion_basis and close > reversion_basis)
        short_reclaim = (not self.require_reclaim) or (high > reversion_basis and close < reversion_basis)

        rsi_value = ta.rsi(self.close, self.rsi_length)
        dp = self.div_pivot_length
        rsi_back = self.H("rsi")[dp]
        self.H("rsi").set(rsi_value)
        div_high = ta.pivothigh(self.high, dp, dp)
        div_low = ta.pivotlow(self.low, dp, dp)
        if not _na(div_high):
            current_bar = bi - dp
            if not _na(self.prev_div_high_price):
                within = current_bar - self.prev_div_high_bar <= self.div_window
                if within and div_high > self.prev_div_high_price and rsi_back < self.prev_div_high_rsi:
                    self.last_bear_div_bar = current_bar
            self.prev_div_high_price, self.prev_div_high_rsi, self.prev_div_high_bar = float(div_high), rsi_back, current_bar
        if not _na(div_low):
            current_bar = bi - dp
            if not _na(self.prev_div_low_price):
                within = current_bar - self.prev_div_low_bar <= self.div_window
                if within and div_low < self.prev_div_low_price and rsi_back > self.prev_div_low_rsi:
                    self.last_bull_div_bar = current_bar
            self.prev_div_low_price, self.prev_div_low_rsi, self.prev_div_low_bar = float(div_low), rsi_back, current_bar
        bear_div_block = (not _na(self.last_bear_div_bar)) and (bi - self.last_bear_div_bar) <= self.div_block_bars
        bull_div_block = (not _na(self.last_bull_div_bar)) and (bi - self.last_bull_div_bar) <= self.div_block_bars

        x_filter_up = ta.crossover(self.close, regime_filter)
        x_filter_dn = ta.crossunder(self.close, regime_filter)
        x_pivot_up = ta.crossover(self.close, day_pivot)
        x_pivot_dn = ta.crossunder(self.close, day_pivot)
        x_basis_up = ta.crossover(self.close, reversion_basis)
        x_basis_dn = ta.crossunder(self.close, reversion_basis)
        x_ema21_up = ta.crossover(self.close, ema_21)
        x_ema21_dn = ta.crossunder(self.close, ema_21)
        isc = self.barstate.isconfirmed
        bull_continuation = self.continuation_entries and isc and locked == 1 and x_filter_up and close > day_pivot and close > reversion_basis
        bear_continuation = self.continuation_entries and isc and locked == -1 and x_filter_dn and close < day_pivot and close < reversion_basis
        bull_rotation = self.aggressive_entries and isc and (locked == 1 or close > regime_filter) and (x_pivot_up or x_basis_up or x_ema21_up)
        bear_rotation = self.aggressive_entries and isc and (locked == -1 or close < regime_filter) and (x_pivot_dn or x_basis_dn or x_ema21_dn)
        long_context_soft = locked == 1 or close > regime_filter or ema_21 > ema_55
        short_context_soft = locked == -1 or close < regime_filter or ema_21 < ema_55

        long_trigger = (bull_bos and (bull_fvg or bf1 or bf2)) or bull_continuation or bull_rotation
        short_trigger = (bear_bos and (bear_fvg or sf1 or sf2)) or bear_continuation or bear_rotation
        long_alignment = (1 if weave_bias >= 0 else 0) + (1 if geometry_bias >= 0 else 0) + (1 if close > regime_filter else 0) \
            + (1 if close > day_pivot else 0)
        short_alignment = (1 if weave_bias <= 0 else 0) + (1 if geometry_bias <= 0 else 0) + (1 if close < regime_filter else 0) \
            + (1 if close < day_pivot else 0)
        long_reclaim_gate = long_reclaim or bull_rotation or bull_continuation
        short_reclaim_gate = short_reclaim or bear_rotation or bear_continuation
        long_stack = isc and long_context_soft and regime_soft_open and long_trigger and long_reclaim_gate and long_alignment >= 1 \
            and ((not self.use_divergence_block) or not bear_div_block)
        short_stack = isc and short_context_soft and regime_soft_open and short_trigger and short_reclaim_gate and short_alignment >= 1 \
            and ((not self.use_divergence_block) or not bull_div_block)

        mintick = self.syminfo.mintick
        long_stop_base = pmath.min(_nz(last_pivot_low, close - atr_value * self.atr_stop_multiple), close - atr_value * self.atr_stop_multiple)
        short_stop_base = pmath.max(_nz(last_pivot_high, close + atr_value * self.atr_stop_multiple), close + atr_value * self.atr_stop_multiple)
        long_risk = pmath.max(close - long_stop_base, mintick)
        short_risk = pmath.max(short_stop_base - close, mintick)

        st = self.strategy
        if long_stack and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_stack and st.position_size >= 0:
            st.entry("Short", st.short)

        avg = st.position_avg_price
        live_long_risk = pmath.max(avg - long_stop_base, mintick) if st.position_size > 0 else long_risk
        live_short_risk = pmath.max(short_stop_base - avg, mintick) if st.position_size < 0 else short_risk
        long_target = avg + live_long_risk * self.reward_multiple
        short_target = avg - live_short_risk * self.reward_multiple
        long_trail_ready = st.position_size > 0 and high >= avg + live_long_risk * self.trail_after_r
        short_trail_ready = st.position_size < 0 and low <= avg - live_short_risk * self.trail_after_r
        long_stop_live = pmath.max(long_stop_base, close - atr_value * self.trail_multiple) if long_trail_ready else long_stop_base
        short_stop_live = pmath.min(short_stop_base, close + atr_value * self.trail_multiple) if short_trail_ready else short_stop_base
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=long_stop_live, limit=long_target)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=short_stop_live, limit=short_target)
        if st.position_size > 0 and (locked == -1 or weave_bias == -1):
            st.close("Long", comment="Context Flip")
        if st.position_size < 0 and (locked == 1 or weave_bias == 1):
            st.close("Short", comment="Context Flip")

        self.plot(regime_filter, title="Regime Filter")
