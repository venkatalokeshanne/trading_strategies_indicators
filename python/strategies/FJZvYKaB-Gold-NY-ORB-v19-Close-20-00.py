"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold NY ORB v19 [Ahmed] — 2.5:1 Close 20:00
Author       : YukozB
Source URL   : https://www.tradingview.com/script/FJZvYKaB-Gold-NY-ORB-v19-Close-20-00
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. timestamp("2024-01-01 00:00 UTC") is given as UTC epoch milliseconds. The
opening range is built from the 13:00 UTC hour; orHigh / orLow / flags are var variables reset on a new
trading day (`ta.change(time("D")) != 0`, na on the first bar = false) - note that the trading day starts at the
SYMBOL's session start, which can fall inside the 13:00 UTC hour. dayofweek is in the exchange time zone
(Sunday = 1, Saturday = 7). The bracket (1 range stop / 2.5 range target) is placed with the entry; any long
is closed at 20:00 UTC.

Deviations from the original: none.
Not carried over: the range lines and the entry marker (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta

DATE_2024 = 1704067200000          # timestamp("2024-01-01 00:00 UTC")
SATURDAY, SUNDAY = 7, 1


class GoldNyOrbV19(Script):
    TITLE = "Gold NY ORB v19 [Ahmed] — 2.5:1 Close 20:00"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.02, slippage=2)
    SOURCE = {"id": "FJZvYKaB", "author": "YukozB", "licence": "not stated",
              "url": "https://www.tradingview.com/script/FJZvYKaB-Gold-NY-ORB-v19-Close-20-00"}

    def init(self):
        self.or_high = NA
        self.or_low = NA
        self.or_ready = False
        self.long_fired = False

    def on_bar(self):
        in_date = self.time >= DATE_2024
        dow = self.dayofweek()
        is_wkd = dow != SATURDAY and dow != SUNDAY
        b_hour = self.hour(self.time, "UTC")
        b_min = self.minute(self.time, "UTC")
        is_or_period = is_wkd and b_hour == 13
        is_entry_win = is_wkd and b_hour >= 14 and (b_hour < 16 or (b_hour == 16 and b_min <= 30))
        is_session_end = is_wkd and b_hour == 20 and b_min == 0
        atr = ta.atr(14)
        vol_avg = ta.sma(self.volume, 20)
        atr_avg20 = ta.sma(atr, 20)
        regime_ok = atr <= atr_avg20 * 2.0
        chg = ta.change(self.time_fn("D"))
        is_new_day = (not na(chg)) and chg != 0
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
        or_ok = self.or_ready and (not na(or_range)) and or_range <= atr * 2.5
        long_break = (in_date and is_entry_win and or_ok and regime_ok and not self.long_fired
                      and self.close > self.or_high and self.close[1] <= self.or_high
                      and self.close > self.open and self.volume > vol_avg * 1.5)
        st = self.strategy
        if long_break:
            st.entry("Long", st.long)
            st.exit("LongX", "Long", stop=self.close - or_range, limit=self.close + or_range * 2.5)
            self.long_fired = True
        if is_session_end and st.position_size > 0:
            st.close_all("Session End")
        self.plot(self.or_high if self.or_ready else NA, "OR High", linewidth=1)
        self.plot(self.or_low if self.or_ready else NA, "OR Low", linewidth=1)
        self.plotshape(long_break, "Long Entry")
