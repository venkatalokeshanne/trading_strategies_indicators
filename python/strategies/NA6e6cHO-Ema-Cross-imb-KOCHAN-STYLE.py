"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ema Cross + imb KOCHAN STYLE
Author       : myemailcauseicare
Source URL   : https://www.tradingview.com/script/NA6e6cHO-Ema-Cross-imb-KOCHAN-STYLE
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; the entries are pending STOP orders). Everything is read from the previous bar: an up-trend (the previous 9 EMA over the 21 EMA and the previous close over the 9 EMA), a bullish fair-value gap (the previous low above the high three bars back, at least the minimum ticks),
a bullish imbalance candle (the previous body over 65 % of its range, closing up, with above-average volume) that broke the high before it. Between 07:30 and 10:00 (UTC-6) while flat, a buy-stop a buffer of ticks above the signal close is placed together with an exit order whose stop is a fixed number of points below it and a trailing stop
(activation and offset in ticks derived from the break-even and trail point inputs); shorts mirror it. A pending stop is replaced by the next signal, never cancelled, and an exit order waits for its entry.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, pmath, ta


class EmaCrossImb(Script):
    TITLE = "Ema Cross + imb"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(fill_orders_on_standard_ohlc=True)
    SOURCE = {"id": "NA6e6cHO", "author": "myemailcauseicare", "licence": "not stated", "url": "https://www.tradingview.com/script/NA6e6cHO-Ema-Cross-imb-KOCHAN-STYLE"}

    def init(self):
        i = self.input
        g = "EMA Settings"
        self.fast_len = i.int(9, "Fast EMA Length", group=g)
        self.slow_len = i.int(21, "Slow EMA Length", group=g)
        self.trail_len = i.int(3, "Points to trail", group="Trail Settings")
        g = "Risk Settings"
        self.stop_pt = i.int(5, "Stop loss points", group=g)
        self.be_pt = i.int(3, "Breakeven at x points", group=g)
        self.trail_pt = i.int(5, "Trail by x points", group=g)
        self.buffer = i.int(1, "Buffer ticks on stop order", group=g)
        self.min_gap = i.int(2, "Min FVG tol in ticks", group="FVG settings")

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        mintick = self.syminfo.mintick
        avg_vol = ta.sma(volume, 20)
        range_candle = self.high[1] - self.low[1]
        body_length = abs(self.close[1] - self.open[1])
        ratio = div(body_length, range_candle)
        ema_fast = ta.ema(close, self.fast_len)
        ema_slow = ta.ema(close, self.slow_len)
        hf, hs, hv, hav = self.H("ema_fast"), self.H("ema_slow"), self.H("volume"), self.H("avg_vol")
        ema_fast_1, ema_slow_1, volume_1, avg_vol_1 = hf[1], hs[1], hv[1], hav[1]
        hf.set(ema_fast)
        hs.set(ema_slow)
        hv.set(volume)
        hav.set(avg_vol)
        time_now = self.hour(self.time, "UTC-6") * 100 + self.minute(self.time, "UTC-6")
        trad_time = time_now >= 730 and time_now <= 1000
        trend_up = ema_fast_1 > ema_slow_1 and self.close[1] > ema_fast_1
        trend_down = ema_fast_1 < ema_slow_1 and self.close[1] < ema_fast_1
        bull_fvg = self.low[1] > self.high[3]
        bear_fvg = self.high[1] < self.low[3]
        bull_gap = self.low[1] - self.high[3]
        if bull_gap < 0:
            bull_gap = 0
        bear_gap = self.low[3] - self.high[1]
        if bear_gap < 0:
            bear_gap = 0
        bullish_imb = self.close[1] > self.open[1] and ratio > 0.65 and volume_1 > avg_vol_1
        bearish_imb = self.close[1] < self.open[1] and ratio > 0.65 and volume_1 > avg_vol_1
        broke_high = self.high[1] > self.high[2]
        broke_low = self.low[1] < self.low[2]
        order_long = trend_up and bull_fvg and div(bull_gap, mintick) >= self.min_gap and bullish_imb and broke_high
        order_short = trend_down and bear_fvg and div(bear_gap, mintick) >= self.min_gap and bearish_imb and broke_low
        if order_long and st.position_size == 0 and trad_time:
            st.entry("Long Entry", st.long, stop=close + self.buffer * mintick, comment="Bullish order")
            st.exit("Long Exit", "Long Entry", stop=close + self.buffer * mintick - self.stop_pt, comment_loss="Stop Loss",
                    trail_points=div(self.be_pt, mintick), trail_offset=div(self.trail_pt, mintick))
        if order_short and st.position_size == 0 and trad_time:
            st.entry("Short Entry", st.short, stop=close - self.buffer * mintick, comment="Bearish order")
            st.exit("Short Exit", "Short Entry", stop=close + self.buffer * mintick + self.stop_pt, comment_loss="Stop Loss",
                    trail_points=div(self.be_pt, mintick), trail_offset=div(self.trail_pt, mintick))
