"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : London NZ Sweep + FVG (HTF FILTER)
Author       : abesamisj
Source URL   : https://www.tradingview.com/script/WVQB9xGo-London-NZ-Sweep-FVG-HTF-FILTER
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, sessions evaluated in Pacific/Auckland. The Asia session (13:00-19:00) high / low is
tracked from its first bar; in the London window (20:00-22:00) the first sweep of that low (bullish) or high (bearish)
fixes the direction, and a displacement candle bigger than ATR(14) with a fair-value gap versus two bars ago in the
direction of the 60-minute close vs its SMA20 enters once per window. Quantity risks 1 % of equity over the distance to
the previous bar's extreme (no order when that distance is 0); the entry and its stop (previous low / high) / 3 R target
are issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: nothing.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

TZ = "Pacific/Auckland"
RISK_PERCENT = 1.0


class LondonNzSweepFvg(Script):
    TITLE = "London NZ Sweep + FVG (HTF FILTER)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=150000, default_qty_type="cash")
    SOURCE = {"id": "WVQB9xGo", "author": "abesamisj", "licence": "not stated",
              "url": "https://www.tradingview.com/script/WVQB9xGo-London-NZ-Sweep-FVG-HTF-FILTER"}

    def init(self):
        self.rr = self.input.float(3.0, "RR")
        self.asia_high = NA
        self.asia_low = NA
        self.trade_taken = False
        self.sweep_dir = 0

    def calc_qty(self, entry, sl):
        risk = pmath.abs(entry - sl)
        risk_value = self.strategy.equity * (RISK_PERCENT / 100)
        return div(risk_value, risk) if risk > 0 else 0

    def on_bar(self):
        htf_close = self.security(self.syminfo.tickerid, "60", lambda v: v.close)
        htf_ma = self.security(self.syminfo.tickerid, "60", lambda v: ta.sma(v.close, 20))
        bull_bias = htf_close > htf_ma
        bear_bias = htf_close < htf_ma
        in_asia = not na(self.time_fn(None, "1300-1900", TZ))
        in_london = not na(self.time_fn(None, "2000-2200", TZ))
        asia_h, london_h = self.H("asia"), self.H("london")
        asia_start = in_asia and not asia_h[1]
        london_start = in_london and not london_h[1]
        asia_h.set(in_asia)
        london_h.set(in_london)
        if asia_start:
            self.asia_high = float(self.high)
            self.asia_low = float(self.low)
        if in_asia:
            self.asia_high = pmath.max(nz(self.asia_high, self.high), self.high)
            self.asia_low = pmath.min(nz(self.asia_low, self.low), self.low)
        if london_start:
            self.trade_taken = False
            self.sweep_dir = 0
        bull_sweep = in_london and self.low < self.asia_low
        bear_sweep = in_london and self.high > self.asia_high
        if (not self.trade_taken) and self.sweep_dir == 0:
            if bull_sweep:
                self.sweep_dir = 1
            elif bear_sweep:
                self.sweep_dir = -1
        atr_bull = ta.atr(14)
        atr_bear = ta.atr(14)
        bull_displacement = self.close > self.open and pmath.abs(self.close - self.open) > atr_bull
        bear_displacement = self.close < self.open and pmath.abs(self.close - self.open) > atr_bear
        bull_fvg = self.low > self.high[2]
        bear_fvg = self.high < self.low[2]
        buy_signal = (not self.trade_taken) and in_london and self.sweep_dir == 1 and bull_displacement and bull_fvg and bull_bias
        sell_signal = (not self.trade_taken) and in_london and self.sweep_dir == -1 and bear_displacement and bear_fvg and bear_bias
        st = self.strategy
        if buy_signal:
            entry = float(self.close)
            sl = self.low[1]
            tp = entry + (entry - sl) * self.rr
            qty = self.calc_qty(entry, sl)
            if qty > 0:
                st.entry("BUY", st.long, qty=qty)
                st.exit("TP/SL BUY", "BUY", stop=sl, limit=tp)
                self.trade_taken = True
        if sell_signal:
            entry = float(self.close)
            sl = self.high[1]
            tp = entry - (sl - entry) * self.rr
            qty = self.calc_qty(entry, sl)
            if qty > 0:
                st.entry("SELL", st.short, qty=qty)
                st.exit("TP/SL SELL", "SELL", stop=sl, limit=tp)
                self.trade_taken = True
