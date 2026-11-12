"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA 5/13/26 Cross + Volume + Dynamic SL + Smart RR + Intraday Exit
Author       : chinmayp5394
Source URL   : https://www.tradingview.com/script/aKf0t6Mz-GoldenCrossover-CP5394
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA5 crossing above (below) both EMA13 and EMA26 on above-average volume goes long (short) at the bar close
(process_orders_on_close), closing the opposite side first. The stop/target are rebuilt every bar from position_avg_price and the
signal-candle size (stop capped at 1% risk, RR 1 for a candle over 1%, else 2); both exit orders run all the time, so they are na (inactive)
while flat and first work one bar after a fill. The signal-candle variables are only refreshed when a signal appears while flat,
as in the source. Everything is closed at 23:10 exchange time.

Deviations from the original: none.
Not carried over: alert() calls and the EMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, pmath, ta


class GoldenCrossoverCp5394(Script):
    TITLE = "EMA 5/13/26 Cross + Volume + Dynamic SL + Smart RR + Intraday Exit"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100, process_orders_on_close=True)
    SOURCE = {"id": "aKf0t6Mz", "author": "chinmayp5394", "licence": "not stated",
              "url": "https://www.tradingview.com/script/aKf0t6Mz-GoldenCrossover-CP5394"}

    def init(self):
        self.ema5_len = self.input.int(5, "EMA 5 Length")
        self.ema13_len = self.input.int(13, "EMA 13 Length")
        self.ema26_len = self.input.int(26, "EMA 26 Length")
        self.vol_len = self.input.int(20, "Volume MA Length")
        self.max_risk_percent = self.input.float(1.0, "Max Risk %")
        self.exit_hour = self.input.int(23, "Exit Hour")
        self.exit_minute = self.input.int(10, "Exit Minute")
        self.src = self.input.source(self.close, "Source")
        self.long_sl = NA
        self.short_sl = NA
        self.long_signal_high = NA
        self.long_signal_low = NA
        self.short_signal_high = NA
        self.short_signal_low = NA

    def on_bar(self):
        ema5 = S(ta.ema(self.src, self.ema5_len))
        ema13 = S(ta.ema(self.src, self.ema13_len))
        ema26 = S(ta.ema(self.src, self.ema26_len))
        avg_volume = ta.sma(self.volume, self.vol_len)
        volume_condition = self.volume > avg_volume
        buy_condition = (ema5[1] < ema13[1] and ema5[1] < ema26[1] and ema5[0] > ema13[0] and ema5[0] > ema26[0] and volume_condition)
        sell_condition = (ema5[1] > ema13[1] and ema5[1] > ema26[1] and ema5[0] < ema13[0] and ema5[0] < ema26[0] and volume_condition)
        st = self.strategy
        if buy_condition and st.position_size == 0:
            self.long_sl = float(self.low)
            self.long_signal_high = float(self.high)
            self.long_signal_low = float(self.low)
        if sell_condition and st.position_size == 0:
            self.short_sl = float(self.high)
            self.short_signal_high = float(self.high)
            self.short_signal_low = float(self.low)
        if buy_condition:
            st.close("Short")
            st.entry("Long", st.long)
        if sell_condition:
            st.close("Long")
            st.entry("Short", st.short)
        long_entry = st.position_avg_price
        long_risk_raw = long_entry - self.long_sl
        max_long_risk = long_entry * self.max_risk_percent / 100
        long_risk = pmath.min(long_risk_raw, max_long_risk)
        long_candle_perc = div(self.long_signal_high - self.long_signal_low, self.long_signal_low) * 100
        long_rr = 1 if long_candle_perc > 1 else 2
        long_sl_final = long_entry - long_risk
        long_target = long_entry + (long_rr * long_risk)
        short_entry = st.position_avg_price
        short_risk_raw = self.short_sl - short_entry
        max_short_risk = short_entry * self.max_risk_percent / 100
        short_risk = pmath.min(short_risk_raw, max_short_risk)
        short_candle_perc = div(self.short_signal_high - self.short_signal_low, self.short_signal_low) * 100
        short_rr = 1 if short_candle_perc > 1 else 2
        short_sl_final = short_entry + short_risk
        short_target = short_entry - (short_rr * short_risk)
        st.exit("Exit Long", from_entry="Long", stop=long_sl_final, limit=long_target)
        st.exit("Exit Short", from_entry="Short", stop=short_sl_final, limit=short_target)
        current_hour = self.hour(self.time)
        current_minute = self.minute(self.time)
        is_exit_time = current_hour == self.exit_hour and current_minute >= self.exit_minute
        if is_exit_time:
            st.close_all(comment="Intraday Exit")
        self.plot(ema5[0], "EMA 5", color=color.red)
        self.plot(ema13[0], "EMA 13", color=color.blue)
        self.plot(ema26[0], "EMA 26", color=color.purple)
