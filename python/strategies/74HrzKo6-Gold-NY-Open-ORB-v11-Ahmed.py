"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold NY Open ORB v11 — LIVE [Ahmed]
Author       : YukozB
Source URL   : https://www.tradingview.com/script/74HrzKo6-Gold-NY-Open-ORB-v11-Ahmed
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The 13:00-14:00 UTC range of a weekday is the opening range; between 14:00 and 16:30 UTC a
bullish close back above the range high (previous close at or below it), on 1.5x volume, with a contained range and ATR regime,
goes long once per day. Risk 1.5% of equity over the range size sets the quantity; stop and target sit one range below / above
the close (fixed on the signal bar). Open longs are closed at the 16:30 UTC bar. The day rolls on the chart's daily
bar (time("D") change).

Deviations from the original: none.
Not carried over: the OR lines, background highlights, entry shape and BUY NOW label (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, pmath, ta


class GoldNyOrb(Script):
    TITLE = "Gold NY Open ORB v11 — LIVE [Ahmed]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1,
                    commission_type="percent", commission_value=0.02, slippage=2)
    SOURCE = {"id": "74HrzKo6", "author": "YukozB", "licence": "not stated",
              "url": "https://www.tradingview.com/script/74HrzKo6-Gold-NY-Open-ORB-v11-Ahmed"}

    def init(self):
        self.risk_pct = self.input.float(1.5, "Risk per trade (%)", minval=0.1, maxval=5.0, step=0.1, group="Position Sizing")
        self.or_high = NA
        self.or_low = NA
        self.or_ready = False
        self.long_fired = False

    def on_bar(self):
        is_wkd = self.dayofweek() != 7 and self.dayofweek() != 1
        b_hour = self.hour(self.time, "UTC")
        b_min = self.minute(self.time, "UTC")
        is_or_period = is_wkd and b_hour == 13
        is_entry_win = is_wkd and b_hour >= 14 and (b_hour < 16 or (b_hour == 16 and b_min <= 30))
        is_session_end = is_wkd and b_hour == 16 and b_min == 30
        atr = S(ta.atr(14))
        vol_avg = ta.sma(self.volume, 20)
        atr_avg20 = ta.sma(atr[0], 20)
        regime_ok = atr[0] <= atr_avg20 * 2.0
        is_new_day = ta.change(self.time_fn("D")) != 0
        if is_new_day:
            self.or_high = NA
            self.or_low = NA
            self.or_ready = False
            self.long_fired = False
        if is_or_period:
            self.or_high = float(self.high) if na(self.or_high) else pmath.max(self.or_high, self.high)
            self.or_low = float(self.low) if na(self.or_low) else pmath.min(self.or_low, self.low)
        if (not is_or_period) and (not na(self.or_high)) and (not self.or_ready) and b_hour >= 14:
            self.or_ready = True
        or_range = NA if (na(self.or_high) or na(self.or_low)) else self.or_high - self.or_low
        or_ok = self.or_ready and (not na(or_range)) and or_range <= atr[0] * 2.5
        c = S(self.close)
        long_break = (is_entry_win and or_ok and regime_ok and (not self.long_fired)
                      and self.close > self.or_high and c[1] <= self.or_high and self.close > self.open
                      and self.volume > vol_avg * 1.5)
        st = self.strategy
        if long_break:
            risk_amt = st.equity * self.risk_pct / 100
            trade_qty = pmath.max(div(risk_amt, pmath.max(or_range, 0.01)), 0.001)
            st.entry("Long", st.long, qty=trade_qty)
            st.exit("LongX", "Long", stop=self.close - or_range, limit=self.close + or_range)
            self.long_fired = True
        if is_session_end and st.position_size > 0:
            st.close_all("Session End")
        self.plot(self.or_high if self.or_ready else NA, "OR High", color=color.green)
        self.plot(self.or_low if self.or_ready else NA, "OR Low", color=color.red)
