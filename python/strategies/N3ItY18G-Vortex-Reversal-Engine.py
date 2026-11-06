"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Vortex Reversal Engine [forexobroker]
Author       : forexobroker
Source URL   : https://www.tradingview.com/script/N3ItY18G
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market entries at the next open, 100 % of equity, 1 tick of slippage, no commission). Mean reversion
in a ranging market (ADX below 30): after a Bollinger Band (20, 2) touch within the last 5 bars and RSI(14) beyond 30 / 70 within
those bars, a long needs the close back inside the lower half of the bands, RSI rising and under 55 and a bullish candle closing in
its upper half (shorts mirror). One position at a time, 5 bars of cooldown after either side. The exit is a limit at 1 ATR and a stop
at 3.5 ATR from the signal close; the optional partial mode splits it in two orders (50 % at the first target, the rest at 3 ATR with
an optional ATR trailing stop given in ticks).
Deviations from the original: none.
Not carried over: boxes, lines, dashboard, bar colours, statistics counters, alert conditions (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


def _nz(x, y=0.0):
    return y if x != x else x


class VortexReversalEngine(Script):
    TITLE = "Vortex Reversal Engine [forexobroker]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=10000, currency="USD",
                    commission_type="cash_per_order", commission_value=0, slippage=1)
    SOURCE = {"id": "N3ItY18G", "author": "forexobroker", "licence": "not stated", "url": "https://www.tradingview.com/script/N3ItY18G"}

    def init(self):
        i = self.input
        g = "Strategy"
        self.bb_len = i.int(20, "BB Length", minval=5, maxval=50, group=g)
        self.bb_mult = i.float(2.0, "BB Multiplier", minval=1.0, maxval=4.0, step=0.1, group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=2, maxval=50, group=g)
        self.rsi_ob = i.int(70, "RSI Overbought", minval=55, maxval=90, group=g)
        self.rsi_os = i.int(30, "RSI Oversold", minval=10, maxval=45, group=g)
        self.adx_len = i.int(14, "ADX Length", minval=5, maxval=50, group=g)
        self.adx_max = i.float(30.0, "ADX Max (Range Filter)", minval=15, maxval=50, step=1, group=g)
        self.touch_lookback = i.int(5, "Band Touch Lookback", minval=1, maxval=15, group=g)
        self.use_vol_filter = i.bool(False, "Volume Filter", group=g)
        self.vol_mult = i.float(1.0, "Volume Filter ×", minval=0.5, maxval=3.0, step=0.1, group=g)
        g = "Risk Management"
        self.atr_len = i.int(14, "ATR Length", minval=5, maxval=50, group=g)
        self.tp_atr_mult = i.float(1.0, "TP ATR Mult", minval=0.5, maxval=5.0, step=0.1, group=g)
        self.sl_atr_mult = i.float(3.5, "SL ATR Mult", minval=1.0, maxval=6.0, step=0.1, group=g)
        self.use_partial = i.bool(False, "Partial Exit Mode", group=g)
        self.tp2_atr_mult = i.float(3.0, "TP2 ATR Mult (partial)", minval=1.0, maxval=8.0, step=0.1, group=g)
        self.use_trail = i.bool(True, "Trailing Stop (partial)", group=g)
        self.trail_atr = i.float(1.5, "Trail ATR Mult", minval=0.5, maxval=4.0, step=0.1, group=g)
        g = "Filters"
        self.cooldown_bars = i.int(5, "Signal Cooldown (bars)", minval=1, maxval=50, group=g)
        self.filter_session = i.bool(False, "Session Filter", group=g)
        self.session_choice = i.string("London+NY", "Session", options=["Asia", "London", "New York", "London+NY"], group=g)
        # var state
        self.last_long_bar = -999
        self.last_short_bar = -999

    def on_bar(self):
        close, open_, high, low = float(self.close), float(self.open), float(self.high), float(self.low)
        bi = self.bar_index

        utc_hour = self.hour(float(self.time), "UTC")
        in_asia = utc_hour >= 0 and utc_hour < 8
        in_london = utc_hour >= 8 and utc_hour < 16
        in_ny = utc_hour >= 13 and utc_hour < 22
        ch = self.session_choice
        session_ok = (not self.filter_session) or (ch == "Asia" and in_asia) or (ch == "London" and in_london) \
            or (ch == "New York" and in_ny) or (ch == "London+NY" and (in_london or in_ny))

        bb_basis = ta.sma(self.close, self.bb_len)
        bb_dev = ta.stdev(self.close, self.bb_len) * self.bb_mult
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        vol_sma = ta.sma(self.volume, 20)
        vol_ok = (not self.use_vol_filter) or float(self.volume) > vol_sma * self.vol_mult
        _, _, adx_val = ta.dmi(self.adx_len, self.adx_len)
        is_ranging = adx_val < self.adx_max

        # stateful ta.barssince calls evaluated every bar
        bs_lower = ta.barssince(low <= bb_lower)
        bs_upper = ta.barssince(high >= bb_upper)
        bs_os = ta.barssince(rsi_val < self.rsi_os)
        bs_ob = ta.barssince(rsi_val > self.rsi_ob)
        touched_lower = _nz(bs_lower, 999) <= self.touch_lookback
        touched_upper = _nz(bs_upper, 999) <= self.touch_lookback
        rsi_was_os = _nz(bs_os, 999) <= self.touch_lookback
        rsi_was_ob = _nz(bs_ob, 999) <= self.touch_lookback
        rsi_prev = self.H("rsi")[1]
        self.H("rsi").set(rsi_val)
        rsi_rec_bull = rsi_val > rsi_prev and rsi_val < 55
        rsi_rec_bear = rsi_val < rsi_prev and rsi_val > 45
        mid = (high + low) / 2
        bull_candle = close > open_ and close > mid
        bear_candle = close < open_ and close < mid
        bull_recovery = close > bb_lower and close < bb_basis and touched_lower
        bear_recovery = close < bb_upper and close > bb_basis and touched_upper

        st = self.strategy
        no_position = st.position_size == 0
        long_sig = no_position and is_ranging and bull_recovery and rsi_was_os and rsi_rec_bull and bull_candle and vol_ok \
            and session_ok and self.barstate.isconfirmed and (bi - self.last_long_bar) >= self.cooldown_bars \
            and (bi - self.last_short_bar) >= self.cooldown_bars
        short_sig = no_position and is_ranging and bear_recovery and rsi_was_ob and rsi_rec_bear and bear_candle and vol_ok \
            and session_ok and self.barstate.isconfirmed and (bi - self.last_short_bar) >= self.cooldown_bars \
            and (bi - self.last_long_bar) >= self.cooldown_bars

        mintick = self.syminfo.mintick
        if long_sig:
            self.last_long_bar = bi
            tp_p = close + atr_val * self.tp_atr_mult
            sl_p = close - atr_val * self.sl_atr_mult
            tp2_p = close + atr_val * self.tp2_atr_mult
            st.entry("Long", st.long)
            if self.use_partial:
                st.exit("LX1", "Long", qty_percent=50, limit=tp_p, stop=sl_p)
                if self.use_trail:
                    ticks = pmath.round(div(atr_val * self.trail_atr, mintick))
                    st.exit("LX2", "Long", limit=tp2_p, stop=sl_p, trail_points=ticks, trail_offset=ticks)
                else:
                    st.exit("LX2", "Long", limit=tp2_p, stop=sl_p)
            else:
                st.exit("LX", "Long", limit=tp_p, stop=sl_p)
        if short_sig:
            self.last_short_bar = bi
            tp_p = close - atr_val * self.tp_atr_mult
            sl_p = close + atr_val * self.sl_atr_mult
            tp2_p = close - atr_val * self.tp2_atr_mult
            st.entry("Short", st.short)
            if self.use_partial:
                st.exit("SX1", "Short", qty_percent=50, limit=tp_p, stop=sl_p)
                if self.use_trail:
                    ticks = pmath.round(div(atr_val * self.trail_atr, mintick))
                    st.exit("SX2", "Short", limit=tp2_p, stop=sl_p, trail_points=ticks, trail_offset=ticks)
                else:
                    st.exit("SX2", "Short", limit=tp2_p, stop=sl_p)
            else:
                st.exit("SX", "Short", limit=tp_p, stop=sl_p)

        self.plot(bb_upper, title="BB Upper")
        self.plot(bb_basis, title="BB Basis")
        self.plot(bb_lower, title="BB Lower")
