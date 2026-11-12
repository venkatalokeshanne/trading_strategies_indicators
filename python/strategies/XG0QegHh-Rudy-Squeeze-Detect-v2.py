"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rudy Squeeze Detect v2
Author       : bigboo407
Source URL   : https://www.tradingview.com/script/XG0QegHh-Rudy-Squeeze-Detect-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A score (volume ratio, one-bar gap, EMA21 > EMA50, close > EMA21, narrow Bollinger width, 5-bar
momentum) of at least 3 with the close above EMA21 and RSI below 80 buys when flat. While a position is open at the close a
trailing exit (trail_points = 4 % and trail_offset = 0.5 % of the close, in ticks) is issued, so it first works on the bar after the
fill with the previous close's amounts. A close under EMA21 with 5-bar momentum under -3 % closes the long at the next open.

Deviations from the original: none.
Not carried over: the EMA plots, bar colour, background, shapes and dashboard table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class RudySqueezeDetect(Script):
    TITLE = "Rudy Squeeze Detect v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=20, initial_capital=10000,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "XG0QegHh", "author": "bigboo407", "licence": "not stated",
              "url": "https://www.tradingview.com/script/XG0QegHh-Rudy-Squeeze-Detect-v2"}

    def init(self):
        self.p_short = self.input.int(21, "Short MA Period")
        self.p_mid = self.input.int(50, "Mid MA Period")
        self.p_rsi = self.input.int(14, "RSI Period")
        self.p_rsi_max = self.input.int(80, "RSI Maximum")
        self.p_vol_avg = self.input.int(20, "Volume Average Bars")
        self.p_bb = self.input.int(20, "BB Period")
        self.p_min = self.input.int(3, "Min Signal Score")
        self.p_trail = self.input.float(4.0, "Trail Pct") / 100
        self.p_off = self.input.float(0.5, "Offset Pct") / 100

    def on_bar(self):
        short_ma = ta.ema(self.close, self.p_short)
        mid_ma = ta.ema(self.close, self.p_mid)
        rsi_val = ta.rsi(self.close, self.p_rsi)
        vol_avg = ta.sma(self.volume, self.p_vol_avg)
        vol_ratio = div(self.volume, vol_avg)
        day_gap = div(self.close - self.close[1], self.close[1]) * 100
        bb_m, bb_u, bb_l = ta.bb(self.close, self.p_bb, 2)
        bb_w = div(bb_u - bb_l, bb_m) * 100
        mom5 = div(self.close - self.close[5], self.close[5]) * 100
        sig = 0
        sig += 2 if vol_ratio > 1.5 else (1 if vol_ratio > 1.2 else 0)
        sig += 2 if day_gap > 3.0 else (1 if day_gap > 1.0 else 0)
        sig += 1 if short_ma > mid_ma else 0
        sig += 1 if self.close > short_ma else 0
        sig += 1 if bb_w < 5.0 else 0
        sig += 1 if mom5 > 2.0 else 0
        price_ok = self.close > short_ma
        rsi_ok = rsi_val < self.p_rsi_max
        squeeze_buy = price_ok and rsi_ok and sig >= self.p_min
        squeeze_fade = self.close < short_ma and mom5 < -3.0
        st = self.strategy
        if squeeze_buy and st.position_size == 0:
            st.entry("SQ_Long", st.long)
        if st.position_size > 0:
            t_pts = div(self.close * self.p_trail, self.syminfo.mintick)
            t_off = div(self.close * self.p_off, self.syminfo.mintick)
            st.exit("SQ_Trail", "SQ_Long", trail_points=t_pts, trail_offset=t_off)
        if squeeze_fade and st.position_size > 0:
            st.close("SQ_Long", comment="Fade Out")
        self.plot(short_ma, "Short MA", color=color.blue, linewidth=2)
        self.plot(mid_ma, "Mid MA", color=color.purple)
