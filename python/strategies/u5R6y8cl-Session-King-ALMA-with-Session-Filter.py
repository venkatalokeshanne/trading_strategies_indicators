"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Session King - ALMA Baseline with Session Filter and Fixed 2R Exit
Author       : backtestbay
Source URL   : https://www.tradingview.com/script/u5R6y8cl-Session-King-ALMA-with-Session-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Price above (below) the ALMA baseline inside the London (05:45-09:45) or New York AM (12:00-16:00) London-time windows enters when flat, sized by
1% of equity over the stop distance. Both exit orders are rebuilt every bar from position_avg_price (3 ATR stop, 6 ATR target) and are na while flat, so they work from
the bar after the fill. The window bounds are built from the bar's exchange-time year / month / day, as in the source, but timestamped in Europe/London.

Deviations from the original: none.
Not carried over: the unused TTM squeeze filter output (off by default; its indicator calls are still made) and the ALMA plot.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class SessionKing(Script):
    TITLE = "Session King - ALMA Baseline with Session Filter and Fixed 2R Exit"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent",
                    commission_value=0.01, slippage=1, pyramiding=0)
    SOURCE = {"id": "u5R6y8cl", "author": "backtestbay", "licence": "not stated",
              "url": "https://www.tradingview.com/script/u5R6y8cl-Session-King-ALMA-with-Session-Filter"}

    def init(self):
        self.source_alma = self.input.source(self.close, "Source", group="ALMA")
        self.alma_window = self.input.int(9, "Window", group="ALMA", minval=2, maxval=50)
        self.alma_offset = self.input.float(0.85, "Offset", group="ALMA", minval=0, maxval=1, step=0.01)
        self.alma_sigma = self.input.float(6.0, "Sigma", group="ALMA", minval=0.5, maxval=10, step=0.1)
        g = "TTM Squeeze"
        self.squeeze_on = self.input.bool(False, "Enable Squeeze Filter", group=g)
        self.sq_len = self.input.int(20, "Length", group=g, minval=1)
        self.sq_bb_mult = self.input.float(2.0, "BB Multiplier", group=g, minval=0.5, step=0.1)
        self.sq_kc_mult = self.input.float(1.5, "KC Multiplier", group=g, minval=0.5, step=0.1)
        g = "Session Filter"
        self.use_london = self.input.bool(True, "London  05:45-09:45 GMT", group=g)
        self.use_nyam = self.input.bool(True, "NY AM   12:00-16:00 GMT", group=g)
        self.use_nypm = self.input.bool(False, "NY PM   19:00-21:00 GMT", group=g)
        g = "Exits"
        self.atr_len = self.input.int(14, "ATR Length", group=g, minval=1)
        self.sl_mult = self.input.float(3.0, "SL ATR Multiplier", group=g, minval=0.5, step=0.1)
        self.tp_mult = self.input.float(6.0, "TP ATR Multiplier (2R)", group=g, minval=0.5, step=0.1)
        self.risk_pct = self.input.float(1.0, "Risk Per Trade (%)", group=g, minval=0.1, step=0.1)

    def on_bar(self):
        alma_line = ta.alma(self.source_alma, self.alma_window, self.alma_offset, self.alma_sigma)
        alma_bull = self.close > alma_line
        alma_bear = self.close < alma_line
        sq_basis = ta.sma(self.close, self.sq_len)
        sq_bb_half = self.sq_bb_mult * ta.stdev(self.close, self.sq_len)
        sq_bb_upper = sq_basis + sq_bb_half
        sq_bb_lower = sq_basis - sq_bb_half
        sq_kc_half = ta.atr(self.sq_len) * self.sq_kc_mult
        sq_kc_upper = sq_basis + sq_kc_half
        sq_kc_lower = sq_basis - sq_kc_half
        sq_compressed = sq_bb_upper <= sq_kc_upper and sq_bb_lower >= sq_kc_lower
        squeeze_active = not sq_compressed
        y, mo, d = self.year(), self.month(), self.dayofmonth()
        london_start = self.timestamp("Europe/London", y, mo, d, 5, 45)
        london_end = self.timestamp("Europe/London", y, mo, d, 9, 45)
        ny_am_start = self.timestamp("Europe/London", y, mo, d, 12, 0)
        ny_am_end = self.timestamp("Europe/London", y, mo, d, 16, 0)
        ny_pm_start = self.timestamp("Europe/London", y, mo, d, 19, 0)
        ny_pm_end = self.timestamp("Europe/London", y, mo, d, 21, 0)
        t = self.time
        in_session = ((self.use_london and t >= london_start and t < london_end)
                      or (self.use_nyam and t >= ny_am_start and t < ny_am_end)
                      or (self.use_nypm and t >= ny_pm_start and t < ny_pm_end))
        atr_val = ta.atr(self.atr_len)
        sl_distance = pmath.max(atr_val * self.sl_mult, self.syminfo.mintick)
        st = self.strategy
        qty = div(st.equity * (self.risk_pct / 100), sl_distance)
        sq_gate = squeeze_active if self.squeeze_on else True
        long_cond = alma_bull and sq_gate and in_session and st.position_size == 0
        short_cond = alma_bear and sq_gate and in_session and st.position_size == 0
        if long_cond:
            st.entry("Long", st.long, qty=qty)
        if short_cond:
            st.entry("Short", st.short, qty=qty)
        avg = st.position_avg_price
        st.exit("LX", "Long", stop=avg - self.sl_mult * atr_val, limit=avg + self.tp_mult * atr_val)
        st.exit("SX", "Short", stop=avg + self.sl_mult * atr_val, limit=avg - self.tp_mult * atr_val)
        self.plot(alma_line, "ALMA", color=color.blue)
