"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NASDAQ ORB Strategy - Strict Exec (RRR 2.0) Fixed
Author       : drakkhon
Source URL   : https://www.tradingview.com/script/eWkFVSVF-NASDAQ-ORB-Strategy-Strict-Exec-RRR-2-0-Fixed
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of the trading logic; process_orders_on_close=true, so market orders
fill at the close of the signal bar. The opening range is built from the bars that START between
09:30 and 09:44 New York and is locked on the bar that starts at 09:45, so a timeframe that has no
bar at 09:45 (10 min) never locks and never trades, exactly as in Pine. The exit bracket is placed
on the signal bar and works from the next bar.

Deviations from the original: none for trades.
Not carried over: the RVOL table, the profit/risk boxes and the plots (cosmetic, no feedback into
the logic); the alert() JSON messages.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class NasdaqOrbStrict(Script):
    TITLE = "NASDAQ ORB Strategy - Strict Exec (RRR 2.0) Fixed"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1,
                    process_orders_on_close=True)
    SOURCE = {"id": "eWkFVSVF", "author": "drakkhon", "licence": "not stated",
              "url": "https://www.tradingview.com/script/eWkFVSVF-NASDAQ-ORB-Strategy-Strict-Exec-RRR-2-0-Fixed"}

    def init(self):
        self.rvol_threshold = self.input.float(1.5, "Minimálne RVOL pre vstup", step=0.1)
        self.rrr = self.input.float(2.0, "Risk Reward Ratio (RRR)", step=0.1)
        self.orb_high = NA
        self.orb_low = NA
        self.orb_mid = NA
        self.orb_locked = False
        self.trade_taken_today = False

    def on_bar(self):
        ny_hour = self.hour(self.time, "America/New_York")
        ny_minute = self.minute(self.time, "America/New_York")
        is_orb_window = ny_hour == 9 and ny_minute >= 30 and ny_minute < 45
        is_trade_window = (ny_hour == 9 and ny_minute >= 45) or (ny_hour > 9 and ny_hour < 16)
        if ny_hour == 9 and ny_minute == 30:
            self.orb_high = float(self.high)
            self.orb_low = float(self.low)
            self.orb_mid = NA
            self.orb_locked = False
            self.trade_taken_today = False
        elif is_orb_window:
            self.orb_high = pmath.max(self.high, self.orb_high)
            self.orb_low = pmath.min(self.low, self.orb_low)
        if ny_hour == 9 and ny_minute == 45 and not self.orb_locked:
            self.orb_mid = (self.orb_high + self.orb_low) / 2
            self.orb_locked = True
        vol_sma = ta.sma(self.volume, 20)
        rvol = div(self.volume, vol_sma) if (not na(vol_sma) and vol_sma > 0) else 1.0
        st = self.strategy
        can_trade = is_trade_window and self.orb_locked and not self.trade_taken_today and st.position_size == 0
        is_breaking_high = ta.crossover(self.close, self.orb_high)
        is_breaking_low = ta.crossunder(self.close, self.orb_low)
        if can_trade:
            if is_breaking_high:
                if rvol >= self.rvol_threshold:
                    long_sl = self.orb_mid
                    long_risk = self.close - long_sl
                    long_tp = self.close + (long_risk * self.rrr)
                    st.entry("Long ORB", st.long)
                    st.exit("Exit Long", "Long ORB", stop=long_sl, limit=long_tp)
                    self.trade_taken_today = True
            elif is_breaking_low:
                if rvol >= self.rvol_threshold:
                    short_sl = self.orb_mid
                    short_risk = short_sl - self.close
                    short_tp = self.close - (short_risk * self.rrr)
                    st.entry("Short ORB", st.short)
                    st.exit("Exit Short", "Short ORB", stop=short_sl, limit=short_tp)
                    self.trade_taken_today = True
        if ny_hour == 16 and ny_minute == 0:
            st.close_all("EOD Close")
