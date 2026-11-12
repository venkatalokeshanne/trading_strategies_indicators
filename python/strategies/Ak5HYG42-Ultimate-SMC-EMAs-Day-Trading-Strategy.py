"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ultimate SMC + EMAs Day Trading Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/Ak5HYG42
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Pivot highs / lows (10 bars each side) refresh a fib range taken from the high 5 bars before the latest pivot-high detection and the low 5 bars before the latest pivot-low detection; the 0.618 level of that range is the "golden pocket". A long needs close over the 200 SMA with the 9 EMA over the 21 EMA, the close at / under the golden pocket or the low at / under the range low, and either a bullish fair-value gap (low over the high two bars back with the previous close over it) or the close crossing over the 9 EMA; shorts mirror. A flat strategy enters 1 contract with the 4-hour low as stop and the 4-hour high as target (swapped for shorts), both frozen at entry.
Deviations from the original: none.
Not carried over: every line, label, box, array of boxes and colour (the trendline, fair-value-gap and 4-hour structure drawings only feed the chart).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class SmcEmasDayTrading(Script):
    TITLE = "Ultimate SMC + EMAs Day Trading Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "Ak5HYG42", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/Ak5HYG42"}

    def init(self):
        i = self.input
        self.ema9_len = i.int(9, "EMA 9 Length", group="Moving Averages")
        self.ema21_len = i.int(21, "EMA 21 Length", group="Moving Averages")
        self.sma200_len = i.int(200, "SMA 200 Length", group="Moving Averages")
        self.tl_length = i.int(10, "Trendline Pivot Length", minval=2, group="Trendlines & Fractals")
        self.ob_length = i.int(5, "Order Block Pivot Length", group="Order Blocks & Fibs")
        self.ob_top = NA
        self.ob_bot = NA
        self.fib_0618 = NA
        self.trade_sl = NA
        self.trade_tp = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        high_2, close_1, low_2 = self.high[2], self.close[1], self.low[2]
        high_ob, low_ob = self.high[self.ob_length], self.low[self.ob_length]
        ema9 = ta.ema(close, self.ema9_len)
        ema21 = ta.ema(close, self.ema21_len)
        sma200 = ta.sma(close, self.sma200_len)
        htf_high = self.security(None, "240", lambda v: float(v.high))
        htf_low = self.security(None, "240", lambda v: float(v.low))
        up_piv = ta.pivothigh(high, self.tl_length, self.tl_length)
        dn_piv = ta.pivotlow(low, self.tl_length, self.tl_length)
        bull_fvg = low > high_2 and close_1 > high_2
        bear_fvg = high < low_2 and close_1 < low_2
        if not na(up_piv):
            self.ob_top = float(high_ob)
        if not na(dn_piv):
            self.ob_bot = float(low_ob)
        if (not na(up_piv)) or (not na(dn_piv)):
            fib_1 = self.ob_top
            fib_0 = self.ob_bot
            self.fib_0618 = fib_0 + (fib_1 - fib_0) * 0.618
        bullish_trend = close > sma200 and ema9 > ema21
        bearish_trend = close < sma200 and ema9 < ema21
        cross_up = ta.crossover(close, ema9)
        cross_dn = ta.crossunder(close, ema9)
        long_condition = bullish_trend and (close <= self.fib_0618 or low <= self.ob_bot) and (bull_fvg or cross_up)
        short_condition = bearish_trend and (close >= self.fib_0618 or high >= self.ob_top) and (bear_fvg or cross_dn)
        if long_condition and st.position_size == 0:
            self.trade_sl = htf_low
            self.trade_tp = htf_high
            st.entry("Long", st.long)
        if short_condition and st.position_size == 0:
            self.trade_sl = htf_high
            self.trade_tp = htf_low
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=self.trade_sl, limit=self.trade_tp)
        if st.position_size < 0:
            st.exit("Exit Short", "Short", stop=self.trade_sl, limit=self.trade_tp)
