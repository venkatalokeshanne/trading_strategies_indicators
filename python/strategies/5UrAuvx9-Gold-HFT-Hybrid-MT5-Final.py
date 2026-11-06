"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold HFT - Hybrid MT5 Final
Author       : amivora19
Source URL   : https://www.tradingview.com/script/5UrAuvx9-Gold-HFT-Hybrid-MT5-Final
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The session string "0700-2000:23456" means Monday-Friday (Pine day numbers
2-6), read in the symbol's exchange time zone. Both strategy.exit calls are unconditional: absolute
5 / 3 point target and stop around the CURRENT average price (na while flat) plus a trailing stop
(3-point activation, 1.5-point offset, in ticks) that is always armed.

Deviations from the original: none.
Not carried over: the MT5 licence / alert_message strings (alerts do not affect a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, ta


class GoldHftHybridMt5(Script):
    TITLE = "Gold HFT - Hybrid MT5 Final"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "5UrAuvx9", "author": "amivora19", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5UrAuvx9-Gold-HFT-Hybrid-MT5-Final"}

    def on_bar(self):
        tp = 5.0
        sl = 3.0
        trail_act = 3.0
        trail_off = 1.5
        is_session = not na(self.time_fn(None, "0700-2000:23456"))
        ema_fast = ta.ema(self.close, 9)
        ema_slow = ta.ema(self.close, 21)
        _plus, _minus, adx_val = ta.dmi(14, 14)
        cross_up = ta.crossover(ema_fast, ema_slow)
        cross_dn = ta.crossunder(ema_fast, ema_slow)
        st = self.strategy
        if cross_up and adx_val > 15 and is_session:
            st.entry("L", st.long)
        if cross_dn and adx_val > 15 and is_session:
            st.entry("S", st.short)
        ts = self.syminfo.mintick
        avg = st.position_avg_price
        st.exit("XL", "L", limit=avg + tp, stop=avg - sl, trail_points=div(trail_act, ts), trail_offset=div(trail_off, ts))
        st.exit("XS", "S", limit=avg - tp, stop=avg + sl, trail_points=div(trail_act, ts), trail_offset=div(trail_off, ts))
