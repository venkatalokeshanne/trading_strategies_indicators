"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fracture Threshold Strategy [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/NwMwuyA5-Fracture-Threshold-Strategy-JOAT
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A seven-point trend score (EMA4 vs EMA5, RSI 14, close vs EMA21, EMA21 / SMA50 / EMA55 / EMA89 stack, close vs EMA750) must reach the minimum, the smoothed volume ratio must pass its floor and the bar must be inside the London or New York window (hour of the chosen time zone); the EMA4 / EMA5 cross (or the first bar of EMA4 beyond EMA5) opens a position while flat. A stop of ATR x multiplier and a target of reward / risk times that distance are measured from the signal close and placed with the entry.

Deviations from the original: none.
Not carried over: TP / SL boxes and labels, the dashboard, the session win-rate counters and the bar tint (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, pmath, ta


class FractureThreshold(Script):
    TITLE = "Fracture Threshold Strategy [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=2.0, commission_type="percent", commission_value=0.05, slippage=2, pyramiding=0)
    SOURCE = {"id": "NwMwuyA5", "author": "officialjackofalltrades", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/NwMwuyA5-Fracture-Threshold-Strategy-JOAT"}

    def init(self):
        i = self.input
        g = "MasterTrend EMA Stack"
        self.e4 = i.int(4, "EMA 4", minval=1, group=g)
        self.e5 = i.int(5, "EMA 5", minval=1, group=g)
        self.e21 = i.int(21, "EMA 21", minval=5, group=g)
        self.s50 = i.int(50, "SMA 50", minval=5, group=g)
        self.e55 = i.int(55, "EMA 55", minval=5, group=g)
        self.e89 = i.int(89, "EMA 89", minval=5, group=g)
        self.e750 = i.int(750, "EMA 750", minval=50, group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=2, group=g)
        g = "Volume Regime Filter"
        self.short_vol = i.int(10, "Short Vol MA", minval=2, group=g)
        self.long_vol = i.int(40, "Long Vol MA", minval=5, group=g)
        self.vol_smth = i.int(3, "Vol Smooth", minval=1, group=g)
        self.vol_min = i.float(0.90, "Min Vol Ratio", minval=0.1, step=0.05, group=g)
        g = "Session Filter"
        self.tz = i.string("America/New_York", "Timezone", options=["America/New_York", "America/Chicago", "Europe/London", "Asia/Tokyo", "UTC"], group=g)
        self.sess_on = i.bool(True, "Session Filter", group=g)
        self.london_on = i.bool(True, "Allow London (08:00-17:00)", group=g)
        self.ny_on = i.bool(True, "Allow NY (14:00-21:00)", group=g)
        g = "Entry Trigger"
        self.ema_cross = i.bool(True, "EMA4/5 Cross Entry", group=g)
        self.min_score = i.int(5, "Min MasterTrend Score", minval=3, maxval=7, group=g)
        g = "Risk Management"
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        self.atr_mult = i.float(1.5, "ATR SL Multiplier", minval=0.5, step=0.1, group=g)
        self.rr = i.float(3.0, "Reward:Risk Ratio", minval=1.0, step=0.5, group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema4 = ta.ema(close, self.e4)
        ema5 = ta.ema(close, self.e5)
        ema21 = ta.ema(close, self.e21)
        sma50 = ta.sma(close, self.s50)
        ema55 = ta.ema(close, self.e55)
        ema89 = ta.ema(close, self.e89)
        ema750 = ta.ema(close, self.e750)
        rsi_val = ta.rsi(close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        vol_short = ta.sma(self.volume, self.short_vol)
        vol_long = ta.sma(self.volume, self.long_vol)
        vol_ratio = ta.ema(div(vol_short, pmath.max(vol_long, 1.0)), self.vol_smth)
        vol_ok = vol_ratio >= self.vol_min
        c1_bull = ema4 > ema5
        c1_bear = ema4 < ema5
        bull_score = int(c1_bull) + int(rsi_val > 50.0) + int(close > ema21) + int(ema21 > sma50) + int(sma50 > ema55) + int(ema55 > ema89) + int(close > ema750)
        bear_score = int(c1_bear) + int(rsi_val < 50.0) + int(close < ema21) + int(ema21 < sma50) + int(sma50 < ema55) + int(ema55 < ema89) + int(close < ema750)
        bar_min = self.hour(self.time, self.tz) * 60 + self.minute(self.time, self.tz)
        in_london = bar_min >= 480 and bar_min < 1020
        in_ny = bar_min >= 840 and bar_min < 1260
        sess_ok = (not self.sess_on) or (self.london_on and in_london) or (self.ny_on and in_ny)
        cross_up = ta.crossover(ema4, ema5)
        cross_dn = ta.crossunder(ema4, ema5)
        b1_h, s1_h = self.H("c1_bull"), self.H("c1_bear")
        c1_bull_1 = (not na(b1_h[1])) and bool(b1_h[1])
        c1_bear_1 = (not na(s1_h[1])) and bool(s1_h[1])
        b1_h.set(c1_bull)
        s1_h.set(c1_bear)
        bull_trigger = cross_up if self.ema_cross else (c1_bull and not c1_bull_1)
        bear_trigger = cross_dn if self.ema_cross else (c1_bear and not c1_bear_1)
        long_entry = bool(bull_trigger and bull_score >= self.min_score and vol_ok and sess_ok and st.position_size == 0)
        short_entry = bool(bear_trigger and bear_score >= self.min_score and vol_ok and sess_ok and st.position_size == 0)
        if long_entry:
            sl_dist = atr_val * self.atr_mult
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=close - sl_dist, limit=close + sl_dist * self.rr)
        if short_entry:
            sl_dist = atr_val * self.atr_mult
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=close + sl_dist, limit=close - sl_dist * self.rr)
