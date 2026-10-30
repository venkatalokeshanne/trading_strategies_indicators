"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NovaTrade IRB v2.0.0
Author       : not stated
Source URL   : https://www.tradingview.com/script/emAsZ8tc
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (stop entries, stop exits, market close at the next open). An inside-range-bar ("IRB") setup: a bar
whose open and close both sit in its lower 55 % (long) / upper 55 % (short), with EMA10 > EMA20 > EMA50 (reverse for shorts),
a rising/falling EMA20 slope over 20 bars (>= 0.4 ATR), a rising/falling 4-hour EMA20 (lookahead off), ADX >= 20, bar range
<= 2 ATR, the last N closes above/below EMA10 and a 50-bar warm-up. A buy stop one pip over the setup bar's high (sell stop one
pip under its low) is placed for 20 bars (re-issued when a new setup appears, cancelled when the window ends). Once filled, the
stop trails the EMA(40) (never loosened) and the position is closed after 40 bars. Size is 1 % of equity risked over the
setup bar's range, in lots of 100 000 units (0.01 to 1.00).
Deviations from the original: none.
Not carried over: the webhook alert payloads (they embed a secret), plots, background.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta

S_FLAT, S_PLONG, S_PSHORT, S_LONG, S_SHORT = 0, 1, 2, 3, 4


def _na(x):
    return x != x


def _nz(x, y=0.0):
    return y if x != x else x


class NovaTradeIrb(Script):
    TITLE = "NovaTrade IRB v2.0.0"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=10000, initial_capital=100000, currency="USD", pyramiding=0,
                    process_orders_on_close=False)
    SOURCE = {"id": "emAsZ8tc", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/emAsZ8tc"}

    IRB_PCT = 0.45
    EMA_FAST_PERIOD = 10
    EMA_PERIOD = 20
    EMA_SLOW_PERIOD = 50
    ATR_PERIOD = 14
    ADX_PERIOD = 14
    SLOPE_LOOKBACK = 20
    SLOPE_THRESH = 0.4
    MTF_H1_LOOKBACK = 20
    ADX_THRESH = 20
    OE_THRESH = 2.0
    PIP_BUF = 0.0001
    TRIGGER_WIN = 20
    TIME_STOP = 40
    RISK_PCT = 0.01
    MIN_LOTS = 0.01
    MAX_LOTS = 1.00
    PIP_VAL_LOT = 10.0
    WARMUP = 50
    UNITS_PER_LOT = 100000

    def init(self):
        i = self.input
        self.ema_confirm_bars = i.int(3, "Bars Closing Above/Below EMA 10", minval=1, group="Entry Filters")
        self.trail_ema_period = i.int(40, "Trailing Stop EMA Period", minval=1, group="Exit Management")
        # var state
        self.state = S_FLAT
        self.irb_hi = NA
        self.irb_lo = NA
        self.pend_bars = 0
        self.pos_bars = 0
        self.best_cl = NA
        self.cur_stop = NA

    def _f_qty(self, ep, sp, pip_size):
        sd = div(pmath.abs(ep - sp), pip_size)
        rd = self.strategy.equity * self.RISK_PCT
        raw = div(rd, sd * self.PIP_VAL_LOT) if sd > 0 else self.MIN_LOTS
        cl = max(self.MIN_LOTS, min(self.MAX_LOTS, raw))
        rnd = pmath.round(cl * 100.0) / 100.0
        return rnd * self.UNITS_PER_LOT

    def on_bar(self):
        close, high, low, open_ = float(self.close), float(self.high), float(self.low), float(self.open)
        pip_size = self.syminfo.mintick * 10

        ema_10 = ta.ema(self.close, self.EMA_FAST_PERIOD)
        ema_20 = ta.ema(self.close, self.EMA_PERIOD)
        ema_50 = ta.ema(self.close, self.EMA_SLOW_PERIOD)
        trail_ema = ta.ema(self.close, self.trail_ema_period)
        atr_val = ta.atr(self.ATR_PERIOD)
        _, _, adx_val = ta.dmi(self.ADX_PERIOD, self.ADX_PERIOD)
        ema_h4 = self.security(self.syminfo.tickerid, "240", lambda v: ta.ema(v.close, self.EMA_PERIOD), lookahead=False)

        # series with history: ema10 (for the confirm loops), ema20 (slope), ema_h4 (higher-timeframe slope)
        h10, h20, h4 = self.H("e10"), self.H("e20"), self.H("h4")
        h10.set(ema_10)
        ema20_back = h20[self.SLOPE_LOOKBACK]
        h20.set(ema_20)
        h4_back = h4[self.MTF_H1_LOOKBACK]
        h4.set(ema_h4)

        def all_closes(above):
            ok = True
            for k in range(self.ema_confirm_bars):
                s = close if k == 0 else self.close[k]
                r = ema_10 if k == 0 else h10[k]
                ok = ok and (not _na(s)) and (not _na(r)) and ((s > r) if above else (s < r))
            return ok

        warmup_ok = self.bar_index >= max(self.WARMUP, max(self.ema_confirm_bars, self.trail_ema_period))
        bar_rng = high - low
        valid_rng = bar_rng > 0
        up_thresh = high - self.IRB_PCT * bar_rng
        is_up_irb = valid_rng and open_ <= up_thresh and close <= up_thresh
        dn_thresh = low + self.IRB_PCT * bar_rng
        is_dn_irb = valid_rng and open_ >= dn_thresh and close >= dn_thresh

        ema_slope = div(ema_20 - _nz(ema20_back), atr_val) if _nz(atr_val) > 0 else 0.0
        trend_up = ema_slope >= self.SLOPE_THRESH
        trend_dn = ema_slope <= -self.SLOPE_THRESH
        h4_up = (not _na(ema_h4)) and (not _na(h4_back)) and ema_h4 > h4_back
        h4_dn = (not _na(ema_h4)) and (not _na(h4_back)) and ema_h4 < h4_back

        sw_pass = adx_val >= self.ADX_THRESH
        oe_ratio = div(bar_rng, atr_val) if _nz(atr_val) > 0 else 0.0
        oe_pass = oe_ratio <= self.OE_THRESH
        stack_bull = ema_10 > ema_20 and ema_20 > ema_50
        stack_bear = ema_10 < ema_20 and ema_20 < ema_50
        confirm_long = all_closes(True)
        confirm_short = all_closes(False)

        sig_long = warmup_ok and is_up_irb and trend_up and h4_up and sw_pass and oe_pass and stack_bull and confirm_long
        sig_short = warmup_ok and is_dn_irb and trend_dn and h4_dn and sw_pass and oe_pass and stack_bear and confirm_short

        st = self.strategy
        pos = st.position_size
        pos_prev = self.H("pos")[1]
        self.H("pos").set(pos)
        was_flat = pos_prev == 0
        now_long, now_short, now_flat = pos > 0, pos < 0, pos == 0
        fill_long = now_long and was_flat
        fill_short = now_short and was_flat
        pos_closed = now_flat and not was_flat

        if pos_closed:
            self.state = S_FLAT
            self.irb_hi = self.irb_lo = NA
            self.pend_bars = 0
            self.pos_bars = 0
            self.best_cl = NA
            self.cur_stop = NA
        if fill_long and self.state == S_PLONG:
            self.state = S_LONG
            self.pos_bars = 0
            self.best_cl = close
            self.cur_stop = self.irb_lo - self.PIP_BUF
        if fill_short and self.state == S_PSHORT:
            self.state = S_SHORT
            self.pos_bars = 0
            self.best_cl = close
            self.cur_stop = self.irb_hi + self.PIP_BUF
        if self.state in (S_PLONG, S_PSHORT):
            self.pend_bars += 1
        if self.state in (S_LONG, S_SHORT):
            self.pos_bars += 1
        if self.state == S_PLONG and self.pend_bars >= self.TRIGGER_WIN:
            st.cancel("Long")
            self.state = S_FLAT
            self.irb_hi = self.irb_lo = NA
            self.pend_bars = 0
        if self.state == S_PSHORT and self.pend_bars >= self.TRIGGER_WIN:
            st.cancel("Short")
            self.state = S_FLAT
            self.irb_hi = self.irb_lo = NA
            self.pend_bars = 0

        if self.state == S_FLAT and sig_long:
            ep, sp = high + self.PIP_BUF, low - self.PIP_BUF
            st.entry("Long", st.long, stop=ep, qty=self._f_qty(ep, sp, pip_size))
            self.irb_hi, self.irb_lo = high, low
            self.state = S_PLONG
            self.pend_bars = 0
        elif self.state == S_FLAT and sig_short:
            ep, sp = low - self.PIP_BUF, high + self.PIP_BUF
            st.entry("Short", st.short, stop=ep, qty=self._f_qty(ep, sp, pip_size))
            self.irb_hi, self.irb_lo = high, low
            self.state = S_PSHORT
            self.pend_bars = 0
        elif self.state == S_PLONG and sig_long:
            ep, sp = high + self.PIP_BUF, low - self.PIP_BUF
            st.entry("Long", st.long, stop=ep, qty=self._f_qty(ep, sp, pip_size))
            self.irb_hi, self.irb_lo = high, low
            self.pend_bars = 0
        elif self.state == S_PSHORT and sig_short:
            ep, sp = low - self.PIP_BUF, high + self.PIP_BUF
            st.entry("Short", st.short, stop=ep, qty=self._f_qty(ep, sp, pip_size))
            self.irb_hi, self.irb_lo = high, low
            self.pend_bars = 0

        if self.state == S_LONG:
            self.best_cl = max(_nz(self.best_cl, close), close)
            self.cur_stop = max(_nz(self.cur_stop, trail_ema), trail_ema)
            st.exit("Long Exit", "Long", stop=self.cur_stop)
            if self.pos_bars >= self.TIME_STOP:
                st.close("Long", comment="TIME_STOP")
        if self.state == S_SHORT:
            self.best_cl = min(_nz(self.best_cl, close), close)
            self.cur_stop = min(_nz(self.cur_stop, trail_ema), trail_ema)
            st.exit("Short Exit", "Short", stop=self.cur_stop)
            if self.pos_bars >= self.TIME_STOP:
                st.close("Short", comment="TIME_STOP")

        self.plot(ema_10, title="EMA 10 H1")
        self.plot(ema_20, title="EMA 20 H1")
        self.plot(ema_50, title="EMA 50 H1")
        self.plot(trail_ema, title="Trailing Stop EMA")
