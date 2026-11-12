"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Nils Version
Author       : not stated
Source URL   : https://www.tradingview.com/script/fFXP7nmK
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market entries at the next open, 2 contracts). Opening-range breakout: the high / low of the first
15 minutes after 09:30 New York is the range; from the first bar after it until 11:00 a bar closing beyond the range (and, by default,
above the 200 / 50 EMAs for longs, volume over its 20-bar average, ADX over 20, RSI under 70 for longs / over 30 for shorts) enters
once the position is flat and fewer than two trades were taken that day. Each entry places, at the same time, a stop 0.5 % from the
signal close, a limit at 2 R (R = 0.5 % of the close) and a trailing exit that activates at 1 R and follows by 1.5 ATR. Anything
still open on the 11:00 bar is closed.
Deviations from the original: none.
Not carried over: range box, plots, dashboard table.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class NilsVersion(Script):
    TITLE = "Nils Version"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=2, initial_capital=100000, currency="USD", margin_long=100,
                    margin_short=100)
    SOURCE = {"id": "fFXP7nmK", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/fFXP7nmK"}

    def init(self):
        i = self.input
        self.range_duration = i.int(15, "Opening Range (min)", minval=1, maxval=60, group="Entry Settings")
        self.entry_window = i.session("0930-1100", "Trade Window", group="Entry Settings")
        self.session_end = i.session("1100-1105", "Session Exit", group="Entry Settings")
        self.tz = i.string("America/New_York", "Timezone", group="Entry Settings")
        self.rr = i.float(2.0, "Risk/Reward Ratio", minval=0.1, step=0.1, group="Entry Settings")
        self.stop_loss_type = i.string("Mid Range", "Stop Loss Placement", options=["Full Range", "Mid Range", "Tight (ATR)"], group="Risk Management")
        self.use_close_confirm = i.bool(True, "Close Confirmation (candle must CLOSE beyond range)", group="Anti Fakeout")
        self.use_adx = i.bool(True, "ADX Trend Filter (min strength)", group="Anti Fakeout")
        self.adx_threshold = i.int(20, "ADX Threshold", minval=10, maxval=50, group="Anti Fakeout")
        self.adx_rising_only = i.bool(False, "Require Rising ADX", group="Anti Fakeout")
        self.adx_len = i.int(14, "ADX Length", minval=5, maxval=30, group="Anti Fakeout")
        self.use_rsi = i.bool(True, "RSI Filter (Avoid Overextended)", group="Anti Fakeout")
        self.use_trend = i.bool(True, "EMA 200 Trend Filter", group="Anti Fakeout")
        self.use_trend_micro = i.bool(True, "EMA 50 Micro Trend Filter", group="Anti Fakeout")
        self.use_volume = i.bool(True, "Volume Filter (> 20 SMA)", group="Anti Fakeout")
        self.use_vwap = i.bool(False, "VWAP Bias Filter", group="Anti Fakeout")
        self.use_trailing = i.bool(True, "Enable Trailing Stop", group="Trailing Stop")
        self.trail_activate_r = i.float(1.0, "Activate after R:", minval=0.1, step=0.1, group="Trailing Stop")
        self.trail_atr_mult = i.float(1.5, "Trail distance (× ATR)", minval=0.1, step=0.1, group="Trailing Stop")
        self.atr_len = i.int(14, "ATR Length", minval=1, group="Trailing Stop")
        self.use_reentry = i.bool(True, "Enable Re-Entry", group="Re-Entry")
        self.max_trades_per_day = i.int(2, "Max Trades per Day", minval=1, maxval=3, group="Re-Entry")
        # var state
        self.or_high = NA
        self.or_low = NA
        self.range_set = False
        self.trades_count = 0

    def on_bar(self):
        close, high, low = float(self.close), float(self.high), float(self.low)
        tz = self.tz
        t = float(self.time)
        ny_year, ny_month, ny_day = self.year(t, tz), self.month(t, tz), self.dayofmonth(t, tz)
        range_start = self.timestamp(tz, ny_year, ny_month, ny_day, 9, 30)
        range_end = range_start + self.range_duration * 60 * 1000
        time_prev = self.H("t")[1]
        self.H("t").set(t)
        is_opening_range = t >= range_start and t < range_end
        is_start_of_range = is_opening_range and not (time_prev >= range_start and time_prev < range_end)
        in_entry_window = not na(self.time_fn(self.timeframe.period, self.entry_window, tz))
        is_end_of_day = not na(self.time_fn(self.timeframe.period, self.session_end, tz))

        day_chg = ta.change(self.time_fn("D", "", tz))
        new_day = (not na(day_chg)) and day_chg != 0
        if new_day:
            self.or_high = NA
            self.or_low = NA
            self.range_set = False
            self.trades_count = 0
        if is_start_of_range:
            self.or_high = high
            self.or_low = low
            self.range_set = False
            self.trades_count = 0
        if is_opening_range:
            self.or_high = pmath.max(self.or_high, high)
            self.or_low = pmath.min(self.or_low, low)
        elif t >= range_end and not na(self.or_high):
            self.range_set = True

        ema200 = ta.ema(self.close, 200)
        ema50 = ta.ema(self.close, 50)
        avg_vol = ta.sma(self.volume, 20)
        vwap_val = ta.vwap(self.hlc3)
        atr_val = ta.atr(self.atr_len)
        rsi_val = ta.rsi(self.close, 14)
        _, _, adx_val = ta.dmi(self.adx_len, self.adx_len)
        adx_prev = self.H("adx")[1]
        self.H("adx").set(adx_val)
        adx_rising = adx_val > adx_prev

        adx_ok = (not self.use_adx) or (adx_val > self.adx_threshold and ((not self.adx_rising_only) or adx_rising))
        vol_confirm = (not self.use_volume) or float(self.volume) > avg_vol
        trend_long = ((not self.use_trend) or close > ema200) and ((not self.use_trend_micro) or close > ema50)
        trend_short = ((not self.use_trend) or close < ema200) and ((not self.use_trend_micro) or close < ema50)
        vwap_long = (not self.use_vwap) or close > vwap_val
        vwap_short = (not self.use_vwap) or close < vwap_val
        rsi_ok_long = (not self.use_rsi) or rsi_val < 70
        rsi_ok_short = (not self.use_rsi) or rsi_val > 30

        close_1 = self.close[1]
        cross_up = ta.crossover(self.close, self.or_high)
        cross_dn = ta.crossunder(self.close, self.or_low)
        long_signal = (close > self.or_high and close_1 <= self.or_high) if self.use_close_confirm else cross_up
        short_signal = (close < self.or_low and close_1 >= self.or_low) if self.use_close_confirm else cross_dn

        trail_offset_price = self.trail_atr_mult * atr_val

        st = self.strategy
        can_enter = in_entry_window and self.range_set and (not is_opening_range) and st.position_size == 0 \
            and self.trades_count < self.max_trades_per_day
        if can_enter:
            long_stop = close * 0.995
            short_stop = close * 1.005
            long_risk = close * 0.005
            short_risk = close * 0.005
            if long_signal and vol_confirm and adx_ok and trend_long and vwap_long and rsi_ok_long:
                st.entry("Long", st.long, comment="ORB Long ▲")
                if self.use_trailing:
                    st.exit("Exit Long", "Long", stop=long_stop, limit=close + long_risk * self.rr,
                            trail_price=close + long_risk * self.trail_activate_r,
                            trail_offset=div(trail_offset_price, self.syminfo.mintick),
                            comment_loss="SL ✗", comment_profit="TP ✓")
                else:
                    st.exit("Exit Long", "Long", stop=long_stop, limit=close + long_risk * self.rr,
                            comment_loss="SL ✗", comment_profit="TP ✓")
                self.trades_count += 1
            if short_signal and vol_confirm and adx_ok and trend_short and vwap_short and rsi_ok_short:
                st.entry("Short", st.short, comment="ORB Short ▼")
                if self.use_trailing:
                    st.exit("Exit Short", "Short", stop=short_stop, limit=close - short_risk * self.rr,
                            trail_price=close - short_risk * self.trail_activate_r,
                            trail_offset=div(trail_offset_price, self.syminfo.mintick),
                            comment_loss="SL ✗", comment_profit="TP ✓")
                else:
                    st.exit("Exit Short", "Short", stop=short_stop, limit=close - short_risk * self.rr,
                            comment_loss="SL ✗", comment_profit="TP ✓")
                self.trades_count += 1

        if is_end_of_day and st.position_size != 0:
            st.close_all(comment="EOD ⏱")

        self.plot(ema200, title="EMA 200")
        self.plot(vwap_val, title="VWAP")
