"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Atlantium Gold - Safe Trader
Author       : Charlycalvoes
Source URL   : https://www.tradingview.com/script/Bjez8v7B
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `dayofweek.friday` is Pine's 6 (Sunday = 1). In v6 `can_trade and ta.crossover(...)` only
evaluates the cross on bars where can_trade is true, so the cross's "previous bar" is the last bar it ran on
(LESSONS P4/P5; pinelib models this). sl / tp are var floats set on the signal bar; strategy.exit has no
from_entry and is issued every bar a position exists, so it first works on the bar after the fill. Friday from
20:00 closes any position at the next open.

Deviations from the original: none.
Not carried over: the background colours (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta

FRIDAY = 6


class AtlantiumGoldSafeTrader(Script):
    TITLE = "Atlantium Gold - Safe Trader"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1400, default_qty_type="fixed", default_qty_value=1, margin_long=0,
                    margin_short=0, pyramiding=0, commission_type="cash_per_order", commission_value=0.06)
    SOURCE = {"id": "Bjez8v7B", "author": "Charlycalvoes", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Bjez8v7B"}

    def init(self):
        self.sl = NA
        self.tp = NA

    def on_bar(self):
        hour = self.hour()
        is_allowed_hour = hour >= 8 and hour <= 19
        is_friday = self.dayofweek() == FRIDAY
        is_weekend_near = is_friday and hour >= 20
        atr_fast = ta.atr(5)
        atr_slow = ta.atr(20)
        news_spike = atr_fast > (atr_slow * 2.5)
        ema_f = ta.ema(self.close, 10)
        ema_s = ta.ema(self.close, 40)
        rsi = ta.rsi(self.close, 14)
        atr = ta.atr(14)
        st = self.strategy
        can_trade = st.position_size == 0 and is_allowed_hour and not is_weekend_near and not news_spike
        long_cond = can_trade and ta.crossover(ema_f, ema_s) and rsi > 50
        short_cond = can_trade and ta.crossunder(ema_f, ema_s) and rsi < 50
        tp_mult = 5.5
        sl_mult = 2.5
        if long_cond:
            self.sl = float(self.close - (atr * sl_mult))
            self.tp = float(self.close + (atr * tp_mult))
            st.entry("L", st.long, comment='{"action":"buy","lots":0.01}')
        if short_cond:
            self.sl = float(self.close + (atr * sl_mult))
            self.tp = float(self.close - (atr * tp_mult))
            st.entry("S", st.short, comment='{"action":"sell","lots":0.01}')
        if is_weekend_near and st.position_size != 0:
            st.close_all(comment='{"action":"close","reason":"weekend"}')
        if st.position_size != 0:
            st.exit("Exit", stop=self.sl, limit=self.tp, comment='{"action":"close"}')
        self.plot(ema_f, color=color.aqua)
        self.plot(ema_s, color=color.white, linewidth=2)
