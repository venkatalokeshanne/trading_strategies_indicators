"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Swing Trend Strategy PRO (Sideways Filtered) | Nifty 500
Author       : DrGunjanPUpadhyay
Source URL   : https://www.tradingview.com/script/dnlM5L6z-Swing-Trend-Strategy-PRO-Sideways-Filtered-Nifty-500
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, process_orders_on_close = true (orders fill at the signal bar's close). Long only: close and
EMA50 above EMA200, ADX(14) above 20, close above EMA20 and RSI(14) crossing over 55. While a position is open at the
close an 8 % stop around the average price is issued (so it works from the next bar); a close under EMA50 exits at the
close. In v6 the `and` chain short-circuits, so ta.crossover only runs on bars where the trend/ADX/EMA20 tests pass and
its "previous bar" is the last bar it ran on (LESSONS P4/P5; pinelib models this).

Deviations from the original: none.
Not carried over: the EMA plots and BUY / SELL label shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SwingTrendPro(Script):
    TITLE = "Swing Trend Strategy PRO (Sideways Filtered) | Nifty 500"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "dnlM5L6z", "author": "DrGunjanPUpadhyay", "licence": "not stated",
              "url": "https://www.tradingview.com/script/dnlM5L6z-Swing-Trend-Strategy-PRO-Sideways-Filtered-Nifty-500"}

    def init(self):
        self.stop_loss_percent = self.input.float(8.0, "Stop Loss %", minval=1)
        self.rsi_length = self.input.int(14, "RSI Length")
        self.ema_fast_length = self.input.int(20, "Fast EMA")
        self.ema_mid_length = self.input.int(50, "Mid EMA")
        self.ema_long_length = self.input.int(200, "Long EMA")
        self.adx_length = self.input.int(14, "ADX Length")
        self.adx_threshold = self.input.float(20, "ADX Minimum Trend Strength")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_length)
        ema_mid = ta.ema(self.close, self.ema_mid_length)
        ema_long = ta.ema(self.close, self.ema_long_length)
        rsi_val = ta.rsi(self.close, self.rsi_length)
        diplus, diminus, adx_val = ta.dmi(self.adx_length, self.adx_length)
        trend_up = self.close > ema_long and ema_mid > ema_long
        strong_trend = adx_val > self.adx_threshold
        entry_condition = trend_up and strong_trend and self.close > ema_fast and ta.crossover(rsi_val, 55)
        st = self.strategy
        if entry_condition:
            st.entry("LONG", st.long)
        stop_price = st.position_avg_price * (1 - self.stop_loss_percent / 100)
        if st.position_size > 0:
            st.exit("SL", from_entry="LONG", stop=stop_price)
        trend_exit = self.close < ema_mid
        if st.position_size > 0 and trend_exit:
            st.close("LONG")
        self.plot(ema_fast, title="20 EMA", color=color.orange, linewidth=2)
        self.plot(ema_mid, title="50 EMA", color=color.blue, linewidth=2)
        self.plot(ema_long, title="200 EMA", color=color.red, linewidth=2)
