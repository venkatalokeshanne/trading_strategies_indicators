"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Quant Synthesis Strategy [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/vxQ5o39J-Quant-Synthesis-Strategy-JOAT
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders processed at the bar close, process_orders_on_close). A long / short confluence score adds the EMA-spread / ADX regime, the higher-timeframe EMA bias (request.security, lookahead off) with pivot market structure, a momentum score
(EMA spread, regression slope, pulse, pivot oscillator divergences), the opening-range session module and volume participation (z-score, directional volume). With a trending regime, score >= minimum and above the opposite score, cooldown and per-session entry room it enters (reversing);
an ATR stop / target is issued while the trade is open, with a time exit, a bias / regime exit and a flat-at-session-end close.
Deviations from the original: none.
Not carried over: EMA / cloud / opening-range / stop-target plots, the regime background and the dashboard table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class QuantSynthesis(Script):
    TITLE = "Quant Synthesis Strategy [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000, default_qty_type="fixed", default_qty_value=1, commission_type="percent",
                    commission_value=0.01, slippage=1, process_orders_on_close=True)
    SOURCE = {"id": "vxQ5o39J", "author": "officialjackofalltrades", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/vxQ5o39J-Quant-Synthesis-Strategy-JOAT"}

    def init(self):
        i = self.input
        g = "Regime"
        self.fast_len = i.int(12, "Fast EMA", minval=1, group=g)
        self.slow_len = i.int(34, "Slow EMA", minval=2, group=g)
        self.signal_len = i.int(9, "Signal Length", minval=1, group=g)
        self.adx_len = i.int(14, "ADX Length", minval=1, group=g)
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        g = "Bias"
        self.htf_tf = i.timeframe("240", "Higher Timeframe", group=g)
        self.htf_fast = i.int(34, "HTF Fast EMA", minval=2, group=g)
        self.htf_slow = i.int(89, "HTF Slow EMA", minval=3, group=g)
        self.pivot_left = i.int(3, "Pivot Left", minval=1, group=g)
        self.pivot_right = i.int(3, "Pivot Right", minval=1, group=g)
        g = "Session"
        self.trade_session = i.session("0930-1600", "Trade Session", group=g)
        self.opening_range_bars = i.int(6, "Opening Range Bars", minval=1, group=g)
        self.use_session_filter = i.bool(True, "Require Session Context", group=g)
        g = "Risk"
        self.risk_pct = i.float(0.50, "Risk % of Equity", minval=0.05, step=0.05, group=g)
        self.stop_atr = i.float(1.6, "Stop ATR", minval=0.2, step=0.1, group=g)
        self.take_atr = i.float(2.8, "Take Profit ATR", minval=0.2, step=0.1, group=g)
        self.max_bars_in_trade = i.int(40, "Max Bars In Trade", minval=1, group=g)
        self.cooldown_bars = i.int(8, "Cooldown Bars", minval=0, group=g)
        self.max_entries_session = i.int(2, "Max Entries Per Session", minval=1, group=g)
        self.min_confluence = i.int(70, "Min Confluence", minval=1, maxval=100, group=g)
        self.htf_bias_on = i.bool(True, "Use HTF Bias Filter", group="Bias")
        self.prev_high_pivot = NA
        self.last_high_pivot = NA
        self.prev_low_pivot = NA
        self.last_low_pivot = NA
        self.last_bear_div_price = NA
        self.last_bear_div_osc = NA
        self.last_bull_div_price = NA
        self.last_bull_div_osc = NA
        self.session_open = NA
        self.session_high = NA
        self.session_low = NA
        self.opening_high = NA
        self.opening_low = NA
        self.session_bars = 0
        self.entries_this_session = 0
        self.last_trade_bar = NA
        self.entry_bar = NA
        self.prev_pos = 0.0

    @staticmethod
    def f_norm(v, scale):
        return 0.0 if scale == 0.0 else div(v, scale)

    @staticmethod
    def f_clamp(v, lo, hi):
        return pmath.min(pmath.max(v, lo), hi)

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        mintick = self.syminfo.mintick
        atr_value = ta.atr(self.atr_len)
        atr_safe = pmath.max(atr_value, mintick)
        atr_pct = self.f_norm(atr_value, close)
        atr_avg = nz(ta.sma(atr_pct, 50), atr_pct)
        fast_ema = ta.ema(close, self.fast_len)
        slow_ema = ta.ema(close, self.slow_len)
        signal_ema = ta.ema(fast_ema - slow_ema, self.signal_len)
        ema_spread = fast_ema - slow_ema
        ema_spread_norm = self.f_norm(ema_spread, atr_safe)
        signal_norm = self.f_norm(signal_ema, atr_safe)
        _, _, adx_value = ta.dmi(self.adx_len, self.adx_len)
        trend_regime = bool(adx_value >= 18 and abs(ema_spread_norm) >= 0.20)
        balance_regime = bool(adx_value < 16 or atr_pct < atr_avg * 0.90)
        expansion_regime = bool(atr_pct > atr_avg * 1.12)
        htf_fast_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_fast), lookahead=False)
        htf_slow_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_slow), lookahead=False)
        hf_h = self.H("htf_fast")
        hf_1 = hf_h[1]
        hf_h.set(htf_fast_ema)
        htf_slope = htf_fast_ema - hf_1
        htf_bull = bool(htf_fast_ema > htf_slow_ema and htf_slope > 0)
        htf_bear = bool(htf_fast_ema < htf_slow_ema and htf_slope < 0)
        ph = ta.pivothigh(high, self.pivot_left, self.pivot_right)
        pl = ta.pivotlow(low, self.pivot_left, self.pivot_right)
        if not na(ph):
            self.prev_high_pivot = self.last_high_pivot
            self.last_high_pivot = float(ph)
        if not na(pl):
            self.prev_low_pivot = self.last_low_pivot
            self.last_low_pivot = float(pl)
        have = not (na(self.last_high_pivot) or na(self.prev_high_pivot) or na(self.last_low_pivot) or na(self.prev_low_pivot))
        structure_bull = have and self.last_high_pivot > self.prev_high_pivot and self.last_low_pivot > self.prev_low_pivot
        structure_bear = have and self.last_high_pivot < self.prev_high_pivot and self.last_low_pivot < self.prev_low_pivot
        trend_slope = ta.linreg(close, 20, 0) - ta.linreg(close, 20, 1)
        trend_slope_norm = self.f_norm(trend_slope, atr_safe)
        trend_pulse = ta.ema(ema_spread_norm + trend_slope_norm, 5)
        esn_h, tsn_h, sn_h = self.H("esn"), self.H("tsn"), self.H("sn")
        pr = self.pivot_right
        osc_back = esn_h[pr] + tsn_h[pr] + sn_h[pr]
        esn_h.set(ema_spread_norm)
        tsn_h.set(trend_slope_norm)
        sn_h.set(signal_norm)
        bull_div = False
        bear_div = False
        osc_at_high = osc_back if not na(ph) else NA
        osc_at_low = osc_back if not na(pl) else NA
        if not na(ph) and not na(osc_at_high):
            bear_div = (not na(self.last_bear_div_price)) and ph > self.last_bear_div_price and osc_at_high < self.last_bear_div_osc
            self.last_bear_div_price = float(ph)
            self.last_bear_div_osc = float(osc_at_high)
        if not na(pl) and not na(osc_at_low):
            bull_div = (not na(self.last_bull_div_price)) and pl < self.last_bull_div_price and osc_at_low > self.last_bull_div_osc
            self.last_bull_div_price = float(pl)
            self.last_bull_div_osc = float(osc_at_low)
        div_bias = 1.0 if bull_div else (-1.0 if bear_div else 0.0)
        hh_h, ll_h = self.H("hh10"), self.H("ll10")
        hh_1, ll_1 = hh_h[1], ll_h[1]
        hh_h.set(ta.highest(high, 10))
        ll_h.set(ta.lowest(low, 10))
        breakout_long = close > nz(hh_1, high)
        breakout_short = close < nz(ll_1, low)
        momentum_score = self.f_clamp(ema_spread_norm * 16.0 + trend_slope_norm * 8.0 + trend_pulse * 5.0 + div_bias * 6.0, -25.0, 25.0)
        in_session = self.time_in_session(self.trade_session)
        ins_h = self.H("in_session")
        prev_in_session = bool(ins_h[1] == 1.0) if self.bar_index > 0 else False
        ins_h.set(1.0 if in_session else 0.0)
        new_session = in_session and not prev_in_session
        if new_session:
            self.session_open = float(open_)
            self.session_high = float(high)
            self.session_low = float(low)
            self.opening_high = float(high)
            self.opening_low = float(low)
            self.session_bars = 1
            self.entries_this_session = 0
        elif in_session:
            self.session_high = float(high) if na(self.session_high) else pmath.max(self.session_high, high)
            self.session_low = float(low) if na(self.session_low) else pmath.min(self.session_low, low)
            if self.session_bars < self.opening_range_bars:
                self.opening_high = float(high) if na(self.opening_high) else pmath.max(self.opening_high, high)
                self.opening_low = float(low) if na(self.opening_low) else pmath.min(self.opening_low, low)
            self.session_bars += 1
        or_ready = in_session and self.session_bars >= self.opening_range_bars
        or_high = self.opening_high if or_ready else NA
        or_low = self.opening_low if or_ready else NA
        or_mid = (or_high + or_low) * 0.5 if (or_ready and not na(or_high) and not na(or_low)) else NA
        session_long = (not self.use_session_filter) or (or_ready and close > or_high and close > or_mid)
        session_short = (not self.use_session_filter) or (or_ready and close < or_low and close < or_mid)
        session_bias_long = or_ready and close > self.session_open and close > or_mid
        session_bias_short = or_ready and close < self.session_open and close < or_mid
        vol_sma = ta.sma(volume, 20)
        vol_stdev = ta.stdev(volume, 20)
        vol_z = 0.0 if vol_stdev == 0.0 else div(volume - vol_sma, vol_stdev)
        vol_surprise = vol_z > 0.8
        directional_volume = self.f_norm(volume * (close - open_), pmath.max(ta.sma(volume * abs(close - open_), 20), mintick))
        volume_score = self.f_clamp(vol_z * 8.0 + directional_volume * 10.0, -15.0, 15.0)
        regime_score_long = 22 if (trend_regime and ema_spread_norm > 0) else (14 if (expansion_regime and ema_spread_norm > 0) else 0)
        regime_score_short = 22 if (trend_regime and ema_spread_norm < 0) else (14 if (expansion_regime and ema_spread_norm < 0) else 0)
        bias_score_long = (20 if htf_bull else 0) if self.htf_bias_on else 10
        bias_score_long += 10 if structure_bull else 0
        bias_score_short = (20 if htf_bear else 0) if self.htf_bias_on else 10
        bias_score_short += 10 if structure_bear else 0
        momentum_long = pmath.min(momentum_score, 25) if momentum_score > 0 else 0
        momentum_short = pmath.min(abs(momentum_score), 25) if momentum_score < 0 else 0
        volume_long = pmath.min(volume_score, 15) if (vol_surprise and close > open_) else 0
        volume_short = pmath.min(abs(volume_score), 15) if (vol_surprise and close < open_) else 0
        session_score_long = 12 if session_bias_long else (12 if (session_long and breakout_long) else 0)
        session_score_short = 12 if session_bias_short else (12 if (session_short and breakout_short) else 0)
        long_score = regime_score_long + bias_score_long + momentum_long + volume_long + session_score_long
        short_score = regime_score_short + bias_score_short + momentum_short + volume_short + session_score_short
        long_candidate = bool(long_score >= self.min_confluence and long_score > short_score and trend_regime and not balance_regime)
        short_candidate = bool(short_score >= self.min_confluence and short_score > long_score and trend_regime and not balance_regime)
        stop_distance = pmath.max(atr_value * self.stop_atr, mintick * 10.0)
        take_distance = pmath.max(atr_value * self.take_atr, mintick * 10.0)
        risk_capital = st.equity * self.risk_pct * 0.01
        contract_value = pmath.max(stop_distance * self.syminfo.pointvalue, mintick)
        trade_qty = pmath.max(div(risk_capital, contract_value), 0.0)
        can_trade = True if na(self.last_trade_bar) else self.bar_index - self.last_trade_bar >= self.cooldown_bars
        session_trade_room = self.entries_this_session < self.max_entries_session
        pos = st.position_size
        enter_long = bool(long_candidate and can_trade and session_trade_room and pos <= 0)
        enter_short = bool(short_candidate and can_trade and session_trade_room and pos >= 0)
        if enter_long:
            st.entry("Long", st.long, qty=trade_qty, comment="QSS Long")
            self.last_trade_bar = self.bar_index
            self.entries_this_session += 1
        if enter_short:
            st.entry("Short", st.short, qty=trade_qty, comment="QSS Short")
            self.last_trade_bar = self.bar_index
            self.entries_this_session += 1
        if pos != 0 and self.prev_pos == 0:
            self.entry_bar = self.bar_index
        if pos == 0:
            self.entry_bar = NA
        avg = st.position_avg_price
        if pos > 0:
            st.exit("Long Exit", "Long", stop=avg - stop_distance, limit=avg + take_distance, comment="ATR Exit")
        if pos < 0:
            st.exit("Short Exit", "Short", stop=avg + stop_distance, limit=avg - take_distance, comment="ATR Exit")
        time_exit_long = pos > 0 and (not na(self.entry_bar)) and self.bar_index - self.entry_bar >= self.max_bars_in_trade
        time_exit_short = pos < 0 and (not na(self.entry_bar)) and self.bar_index - self.entry_bar >= self.max_bars_in_trade
        if time_exit_long:
            st.close("Long", comment="Time Exit")
        if time_exit_short:
            st.close("Short", comment="Time Exit")
        regime_exit_long = pos > 0 and (structure_bear or htf_bear or balance_regime)
        regime_exit_short = pos < 0 and (structure_bull or htf_bull or balance_regime)
        if regime_exit_long:
            st.close("Long", comment="Bias Exit")
        if regime_exit_short:
            st.close("Short", comment="Bias Exit")
        session_close = (not in_session) and prev_in_session
        if session_close and pos != 0:
            st.close_all(comment="Session Flat")
        self.prev_pos = pos
