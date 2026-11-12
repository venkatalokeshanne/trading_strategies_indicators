"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMC Fractal Strategy [Jamol] v3
Author       : JamolCooper
Source URL   : https://www.tradingview.com/script/97G0VL40-SMC-Fractal-Strategy-Jamol-v3
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A liquidity sweep of the latest swing (pivot) low / high followed within `Sweep expiry` bars by a break of structure (close through the opposite swing with the previous close on the other side) sets the market trend. The break records an order block (the last
opposing candle in the preceding 30 bars); a breaker (three opposing candles then a close beyond their bodies) and a fair value gap are tracked too. While the higher-timeframe EMA(20) bias agrees and the session is on, a close that taps any of the zones enters at the next open with the stop
behind the zone and a reward / risk target, placed with the entry. A consumed zone's upper edge is cleared.

Deviations from the original: none.
Not carried over: the zone boxes, labels and lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta

NY = "America/New_York"


class SmcFractal(Script):
    TITLE = "SMC Fractal Strategy [Jamol] v3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=2, commission_type="percent", commission_value=0.01, slippage=1)
    SOURCE = {"id": "97G0VL40", "author": "JamolCooper", "licence": "not stated",
              "url": "https://www.tradingview.com/script/97G0VL40-SMC-Fractal-Strategy-Jamol-v3"}

    def init(self):
        g = "Sessions"
        self.use_ny = self.input.bool(True, "NY + London Close (7am-3pm EST)", group=g)
        self.use_asian = self.input.bool(False, "Asian Session", group=g)
        g = "Structure"
        self.swing_len = self.input.int(10, "Swing Length", minval=5, maxval=30, group=g)
        self.htf = self.input.timeframe("240", "HTF Bias Timeframe", group=g)
        self.sweep_exp = self.input.int(20, "Sweep expiry (bars)", group=g)
        self.rr_ratio = self.input.float(2.0, "R:R Ratio", minval=1.0, step=0.5, group="Risk")
        self.sl_buf = self.input.float(0.00010, "SL Buffer", minval=0, step=0.00001, group="Risk")
        self.fvg_min = self.input.float(0.00010, "Min FVG Size", minval=0, step=0.00001, group="FVG")
        self.last_hi = NA
        self.last_lo = NA
        self.swept_bull_bar = -999
        self.swept_bear_bar = -999
        self.trend = 0
        self.bull_ob_hi = NA
        self.bull_ob_lo = NA
        self.bear_ob_hi = NA
        self.bear_ob_lo = NA
        self.bull_brk_hi = NA
        self.bull_brk_lo = NA
        self.bear_brk_hi = NA
        self.bear_brk_lo = NA
        self.bull_fvg_hi = NA
        self.bull_fvg_lo = NA
        self.bear_fvg_hi = NA
        self.bear_fvg_lo = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ny_time = self.time_fn(None, "0700-1500", NY)
        asian_time = self.time_fn(None, "2000-0000", NY)
        in_ses = (self.use_ny and not na(ny_time)) or (self.use_asian and not na(asian_time))
        htf_ema = self.security(None, self.htf, lambda v: ta.ema(v.close, 20), lookahead=False)
        htf_close = self.security(None, self.htf, lambda v: v.close, lookahead=False)
        htf_trend = 1 if htf_close > htf_ema else (-1 if htf_close < htf_ema else 0)
        ph = ta.pivothigh(high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_hi = ph
        if not na(pl):
            self.last_lo = pl
        bull_sweep = (not na(self.last_lo)) and low < self.last_lo and close > self.last_lo
        bear_sweep = (not na(self.last_hi)) and high > self.last_hi and close < self.last_hi
        if bull_sweep:
            self.swept_bull_bar = self.bar_index
        if bear_sweep:
            self.swept_bear_bar = self.bar_index
        sweep_bull_ok = (self.bar_index - self.swept_bull_bar) <= self.sweep_exp
        sweep_bear_ok = (self.bar_index - self.swept_bear_bar) <= self.sweep_exp
        bull_bos = sweep_bull_ok and (not na(self.last_hi)) and close > self.last_hi and close[1] <= self.last_hi
        bear_bos = sweep_bear_ok and (not na(self.last_lo)) and close < self.last_lo and close[1] >= self.last_lo
        if bull_bos:
            self.trend = 1
            self.swept_bull_bar = -999
        if bear_bos:
            self.trend = -1
            self.swept_bear_bar = -999
        if bull_bos:
            for k in range(1, 31):
                if close[k] < open_[k]:
                    self.bull_ob_hi = high[k]
                    self.bull_ob_lo = low[k]
                    break
        if bear_bos:
            for k in range(1, 31):
                if close[k] > open_[k]:
                    self.bear_ob_hi = high[k]
                    self.bear_ob_lo = low[k]
                    break
        if (not na(self.bull_ob_lo)) and close < self.bull_ob_lo:
            self.bull_ob_hi = NA
            self.bull_ob_lo = NA
        if (not na(self.bear_ob_hi)) and close > self.bear_ob_hi:
            self.bear_ob_hi = NA
            self.bear_ob_lo = NA
        prior_bear3 = close[1] < open_[1] and close[2] < open_[2] and close[3] < open_[3]
        prior_bull3 = close[1] > open_[1] and close[2] > open_[2] and close[3] > open_[3]
        bear_body_top = pmath.max(open_[1], pmath.max(open_[2], open_[3]))
        bull_body_bot = pmath.min(open_[1], pmath.min(open_[2], open_[3]))
        bull_brk_formed = self.trend == 1 and prior_bear3 and close > bear_body_top
        bear_brk_formed = self.trend == -1 and prior_bull3 and close < bull_body_bot
        if bull_brk_formed:
            self.bull_brk_hi = pmath.max(high[1], pmath.max(high[2], high[3]))
            self.bull_brk_lo = pmath.min(low[1], pmath.min(low[2], low[3]))
        if bear_brk_formed:
            self.bear_brk_hi = pmath.max(high[1], pmath.max(high[2], high[3]))
            self.bear_brk_lo = pmath.min(low[1], pmath.min(low[2], low[3]))
        if (not na(self.bull_brk_lo)) and close < self.bull_brk_lo:
            self.bull_brk_hi = NA
            self.bull_brk_lo = NA
        if (not na(self.bear_brk_hi)) and close > self.bear_brk_hi:
            self.bear_brk_hi = NA
            self.bear_brk_lo = NA
        bull_fvg = self.trend == 1 and high[2] < low and (low - high[2]) >= self.fvg_min
        bear_fvg = self.trend == -1 and low[2] > high and (low[2] - high) >= self.fvg_min
        if bull_fvg:
            self.bull_fvg_hi = float(low)
            self.bull_fvg_lo = high[2]
        if bear_fvg:
            self.bear_fvg_hi = low[2]
            self.bear_fvg_lo = float(high)
        bull_ob_tap = (not na(self.bull_ob_hi)) and close <= self.bull_ob_hi and close >= self.bull_ob_lo
        bull_fvg_tap = (not na(self.bull_fvg_hi)) and close <= self.bull_fvg_hi and close >= self.bull_fvg_lo
        bull_brk_tap = (not na(self.bull_brk_hi)) and close <= self.bull_brk_hi and close >= self.bull_brk_lo
        bear_ob_tap = (not na(self.bear_ob_hi)) and close >= self.bear_ob_lo and close <= self.bear_ob_hi
        bear_fvg_tap = (not na(self.bear_fvg_hi)) and close >= self.bear_fvg_lo and close <= self.bear_fvg_hi
        bear_brk_tap = (not na(self.bear_brk_hi)) and close >= self.bear_brk_lo and close <= self.bear_brk_hi
        long_zone = bull_ob_tap or bull_fvg_tap or bull_brk_tap
        short_zone = bear_ob_tap or bear_fvg_tap or bear_brk_tap
        long_sig = in_ses and self.trend == 1 and htf_trend == 1 and long_zone and st.position_size == 0
        short_sig = in_ses and self.trend == -1 and htf_trend == -1 and short_zone and st.position_size == 0
        if long_sig:
            lo_ref = self.bull_ob_lo if bull_ob_tap else (self.bull_fvg_lo if bull_fvg_tap else self.bull_brk_lo)
            sl = lo_ref - self.sl_buf
            tp = close + (close - sl) * self.rr_ratio
            st.entry("Long", st.long)
            st.exit("LX", "Long", limit=tp, stop=sl)
            self.bull_ob_hi = NA
            self.bull_fvg_hi = NA
            self.bull_brk_hi = NA
        if short_sig:
            hi_ref = self.bear_ob_hi if bear_ob_tap else (self.bear_fvg_hi if bear_fvg_tap else self.bear_brk_hi)
            sl = hi_ref + self.sl_buf
            tp = close - (sl - close) * self.rr_ratio
            st.entry("Short", st.short)
            st.exit("SX", "Short", limit=tp, stop=sl)
            self.bear_ob_hi = NA
            self.bear_fvg_hi = NA
            self.bear_brk_hi = NA
