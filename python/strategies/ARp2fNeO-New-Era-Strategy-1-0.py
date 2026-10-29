"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : New Era Strategy 1.0
Author       : bprakaash
Source URL   : https://www.tradingview.com/script/ARp2fNeO-New-Era-Strategy-1-0
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Inside the 09:15-15:00 session a stack of EMA / HMA ordering with RSI(5) and CCI(14) extremes arms a short ("PE") or long ("CE") setup; the setup candle's high / low is re-based on the
following candles while the close stays inside it, and a close through the opposite side of the setup candle enters with the stop at the lower of the last two highs (higher of the last two lows) and a target at
`Target 1` times the stop distance. The stop / target exit is issued together with the entry. Only LONG positions are closed at the day-close window 15:10-15:15 (the original tests position_size > 0).

Deviations from the original: none.
Not carried over: the SL / entry / target line plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class NewEraStrategy(Script):
    TITLE = "New Era Strategy 1.0"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100)
    SOURCE = {"id": "ARp2fNeO", "author": "bprakaash", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ARp2fNeO-New-Era-Strategy-1-0"}

    def init(self):
        self.sl_max_points_percent = self.input.float(0, "SL Max Points %", minval=0)
        self.tgt_ratio = self.input.float(2, "Target 1", minval=0)
        self.sig_low = NA
        self.sig_high = NA
        self.sl = NA
        self.active_pe = False
        self.active_ce = False
        self.running_pe = False
        self.running_ce = False
        self.sl_v = 0.0
        self.entry_v = 0.0
        self.target_v = 0.0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        trade_time = self.time_fn(None, "0915-1500")
        exit_time = self.time_fn(None, "1510-1515")
        rsi = ta.rsi(close, 5)
        rsi_smooth = ta.sma(rsi, 5)
        cci = ta.cci(close, 14)
        cci_smooth = ta.sma(cci, 5)
        ema09 = ta.ema(close, 9)
        ema33 = ta.ema(close, 33)
        ema_smooth = ta.sma(ema33, 9)
        hma18 = ta.hma(close, 18)
        hma22 = ta.hma(close, 22)
        hma27 = ta.hma(close, 27)
        cond_a_pe = ema_smooth < ema33 and ema33 < hma27 and hma27 < hma22 and hma22 < hma18
        cond_b_pe = rsi > 65 and rsi_smooth > 60
        cond_c_pe = cci > 100 and cci_smooth > 80
        cond_a_ce = ema_smooth > ema33 and ema33 > hma27 and hma27 > hma22 and hma22 > hma18
        cond_b_ce = rsi < 25 and rsi_smooth < 30
        cond_c_ce = cci < -50 and cci_smooth < -20
        formation_pe = cond_a_pe and cond_b_pe and cond_c_pe and not na(trade_time)
        formation_ce = cond_a_ce and cond_b_ce and cond_c_ce and not na(trade_time)
        fpe_h, fce_h = self.H("fpe"), self.H("fce")
        fpe_1, fce_1 = fpe_h[1], fce_h[1]
        fpe_h.set(formation_pe)
        fce_h.set(formation_ce)
        high_1, low_1 = high[1], low[1]

        if st.position_size > 0 and not na(exit_time):
            st.close_all("Day Close")
        if st.position_size == 0:
            self.running_pe = False
            self.running_ce = False
            self.sl_v = NA
            self.entry_v = NA
            self.target_v = NA

        if not self.running_pe and not na(trade_time):
            if formation_pe:
                if (not na(fpe_1)) and fpe_1:
                    if (high > self.sig_high or low < self.sig_low) and close > self.sig_low:
                        self.sig_low = float(low)
                        self.sig_high = float(high)
                        self.active_pe = True
                else:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
                    self.active_pe = True
            if self.active_pe and close > self.sig_low:
                if high > self.sig_high:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
                elif low < self.sig_low:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
                elif low > self.sig_low and high < self.sig_high:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
            signal_pe = self.active_pe and close < self.sig_low and not self.running_pe
            if signal_pe:
                self.sl = pmath.min(high_1, high)
                entry = float(close)
                sl_points = self.sl - entry
                if self.sl_max_points_percent > 0:
                    sl_max_points = (entry / 100) * self.sl_max_points_percent
                    if sl_points > sl_max_points:
                        self.sl = float(high)
                        sl_points = self.sl - entry
                        if sl_points > sl_max_points:
                            self.sl = 0
                target = entry - (self.tgt_ratio * sl_points)
                if self.sl > 0:
                    st.entry("Short", st.short, qty=1)
                    self.running_pe = True
                    st.exit("TP/SL 1", "Short", qty=1, stop=self.sl, limit=target)
                    self.sl_v = self.sl
                    self.entry_v = float(close)
                    self.target_v = target
                    self.active_pe = False
                    self.sig_low = NA
                    self.sig_high = NA

        if not self.running_ce and not na(trade_time):
            if formation_ce:
                if (not na(fce_1)) and fce_1:
                    if (low < self.sig_low or high > self.sig_high) and close < self.sig_high:
                        self.sig_low = float(low)
                        self.sig_high = float(high)
                        self.active_ce = True
                else:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
                    self.active_ce = True
            if self.active_ce and close < self.sig_high:
                if low < self.sig_low:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
                elif high > self.sig_high:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
                elif high < self.sig_high and low > self.sig_low:
                    self.sig_low = float(low)
                    self.sig_high = float(high)
            signal_ce = self.active_ce and close > self.sig_high and not self.running_ce
            if signal_ce:
                self.sl = pmath.min(low_1, low)
                entry = float(close)
                sl_points = entry - self.sl
                if self.sl_max_points_percent > 0:
                    sl_max_points = (entry / 100) * self.sl_max_points_percent
                    if sl_points > sl_max_points:
                        self.sl = float(low)
                        sl_points = entry - self.sl
                        if sl_points > sl_max_points:
                            self.sl = 0
                target = entry + (self.tgt_ratio * sl_points)
                if self.sl > 0:
                    st.entry("Long", st.long, qty=1)
                    self.running_ce = True
                    st.exit("TP/SL 1", "Long", qty=1, stop=self.sl, limit=target)
                    self.sl_v = self.sl
                    self.entry_v = float(close)
                    self.target_v = target
                    self.active_ce = False
                    self.sig_low = NA
                    self.sig_high = NA

        self.plot(self.sl_v, "SL", color=color.red, style="linebr", offset=1)
        self.plot(self.entry_v, "Entry", color=color.blue, style="linebr", offset=1)
        self.plot(self.target_v, "Target", color=color.green, style="linebr", offset=1)
