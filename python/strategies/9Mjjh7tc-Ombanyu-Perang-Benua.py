"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ombanyu Perang Benua
Author       : ardani17
Source URL   : https://www.tradingview.com/script/9Mjjh7tc-Ombanyu-Perang-Benua
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (gold symbols only). The lowest low of the last New York hour (20:00-21:00 UTC) of each day becomes the "final low". When the Asian session (00:00-08:00 UTC) has traded below it, a short is taken at the end of Asia with the stop above the Asian high; when both the Asian and the London
(07:00-16:00 UTC) sessions held above it, a long is taken at the end of London with the stop below that low. Risk-sized (1 % of equity), target at the minimum reward / risk; one position at a time, entries at the next open and the bracket placed with the entry.

Deviations from the original: none.
Not carried over: the final-low line, session backgrounds, status table and signal labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class OmbanyuPerangBenua(Script):
    TITLE = "Ombanyu Perang Benua"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.03)
    SOURCE = {"id": "9Mjjh7tc", "author": "ardani17", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9Mjjh7tc-Ombanyu-Perang-Benua"}

    def init(self):
        g = "Sesi (UTC)"
        self.asia_start_h = self.input.int(0, "Asia mulai (jam UTC)", minval=0, maxval=23, group=g)
        self.asia_end_h = self.input.int(8, "Asia selesai (jam UTC)", minval=1, maxval=24, group=g)
        self.london_start_h = self.input.int(7, "London mulai (jam UTC)", minval=0, maxval=23, group=g)
        self.london_end_h = self.input.int(16, "London selesai (jam UTC)", minval=1, maxval=24, group=g)
        self.ny_start_h = self.input.int(12, "NY mulai (jam UTC)", minval=0, maxval=23, group=g)
        self.ny_end_h = self.input.int(21, "NY selesai (jam UTC)", minval=1, maxval=24, group=g)
        self.ny_last_start_h = self.input.int(20, "NY jam terakhir mulai (UTC)", minval=0, maxval=23, group=g)
        g = "Eksekusi & MM"
        self.enable_long = self.input.bool(True, "Aktifkan LONG (low awet)", group=g)
        self.enable_short = self.input.bool(True, "Aktifkan SHORT (Asia tembus)", group=g)
        self.gold_only = self.input.bool(True, "Hanya Gold (XAU/GOLD)", group=g)
        self.min_rr = self.input.float(2.0, "Min R:R", minval=1.0, step=0.5, group=g)
        self.risk_pct = self.input.float(1.0, "Risk % equity", minval=0.1, maxval=5.0, step=0.1, group=g)
        self.atr_len = self.input.int(14, "ATR length", minval=1, group=g)
        self.atr_sl_pad = self.input.float(0.15, "SL padding (x ATR)", minval=0.0, step=0.05, group=g)
        self.asia_low_day = NA
        self.asia_high_day = NA
        self.london_low_day = NA
        self.ny_last_low_build = NA
        self.ny_final_low = NA
        self.entry_sl = NA
        self.entry_tp = NA

    def in_hour_range(self, h_utc, start_h, end_h):
        return (h_utc >= start_h and h_utc < end_h) if start_h < end_h else (h_utc >= start_h or h_utc < end_h)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_utc = self.hour(self.time, "UTC")
        in_asia = self.in_hour_range(h_utc, self.asia_start_h, self.asia_end_h)
        in_london = self.in_hour_range(h_utc, self.london_start_h, self.london_end_h)
        in_ny_last_hour = self.in_hour_range(h_utc, self.ny_last_start_h, self.ny_end_h)
        flags = self.H("flags")
        prev = flags[1]
        flags.set((1 if in_asia else 0) + (2 if in_london else 0) + (4 if in_ny_last_hour else 0))
        pv = 0 if na(prev) else int(prev)
        asia_1, london_1, ny_last_1 = bool(pv & 1), bool(pv & 2), bool(pv & 4)
        ticker = self.syminfo.ticker.upper()
        gold_ok = (not self.gold_only) or "XAU" in ticker or "GOLD" in ticker
        atr_val = ta.atr(self.atr_len)
        day_change = ta.change(self.time_fn("D"))
        new_day = (not na(day_change)) and day_change != 0
        if new_day:
            self.asia_low_day = NA
            self.asia_high_day = NA
            self.london_low_day = NA
            self.ny_last_low_build = NA
        if in_asia:
            self.asia_low_day = float(low) if na(self.asia_low_day) else pmath.min(self.asia_low_day, low)
            self.asia_high_day = float(high) if na(self.asia_high_day) else pmath.max(self.asia_high_day, high)
        if in_london:
            self.london_low_day = float(low) if na(self.london_low_day) else pmath.min(self.london_low_day, low)
        if in_ny_last_hour:
            self.ny_last_low_build = float(low) if na(self.ny_last_low_build) else pmath.min(self.ny_last_low_build, low)
        ny_last_hour_ended = ny_last_1 and not in_ny_last_hour
        if ny_last_hour_ended and not na(self.ny_last_low_build):
            self.ny_final_low = self.ny_last_low_build
            self.ny_last_low_build = NA
        asia_ended = asia_1 and not in_asia
        london_ended = london_1 and not in_london
        signal_short = False
        signal_long = False
        if self.barstate.isconfirmed and gold_ok and not na(self.ny_final_low):
            if asia_ended and self.enable_short and (not na(self.asia_low_day)) and self.asia_low_day < self.ny_final_low:
                signal_short = True
            if london_ended and self.enable_long and (not na(self.asia_low_day)) and (not na(self.london_low_day)):
                asia_held = self.asia_low_day >= self.ny_final_low
                london_held = self.london_low_day >= self.ny_final_low
                if asia_held and london_held:
                    signal_long = True
        if self.barstate.isconfirmed and st.position_size == 0:
            if signal_short:
                self.entry_sl = self.asia_high_day + atr_val * self.atr_sl_pad
                risk = self.entry_sl - close
                if risk > self.syminfo.mintick:
                    self.entry_tp = close - risk * self.min_rr
                    qty = div(st.equity * self.risk_pct / 100.0, risk)
                    st.entry("Short", st.short, qty=max(qty, 0.01))
                    st.exit("Short Exit", "Short", stop=self.entry_sl, limit=self.entry_tp)
            if signal_long:
                self.entry_sl = self.ny_final_low - atr_val * self.atr_sl_pad
                risk_l = close - self.entry_sl
                if risk_l > self.syminfo.mintick:
                    self.entry_tp = close + risk_l * self.min_rr
                    qty_l = div(st.equity * self.risk_pct / 100.0, risk_l)
                    st.entry("Long", st.long, qty=max(qty_l, 0.01))
                    st.exit("Long Exit", "Long", stop=self.entry_sl, limit=self.entry_tp)
