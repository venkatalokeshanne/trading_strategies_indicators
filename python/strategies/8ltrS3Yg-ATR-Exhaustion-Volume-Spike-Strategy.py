"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ATR Exhaustion & Volume Spike Strategy
Author       : MyStrategyHub
Source URL   : https://www.tradingview.com/script/8ltrS3Yg-ATR-Exhaustion-Volume-Spike-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Pivots (5 bars each side) keep the last pivot high / low. A long needs the low within 0.5 % of the last
pivot low, price stretched from the last pivot high by more than 2 ATR (high - low distance), volume 1.5x its SMA20 and a bullish
trigger bar (green or above the previous high); the short is the mirror. The stop is the pivot level or the bar extreme,
whichever is further, the target 2 R; the quantity risks 0.5 % of equity over that distance. Entry and strategy.exit are issued
together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the level plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, ta


class AtrExhaustionVolume(Script):
    TITLE = "ATR Exhaustion & Volume Spike Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash")
    SOURCE = {"id": "8ltrS3Yg", "author": "MyStrategyHub", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8ltrS3Yg-ATR-Exhaustion-Volume-Spike-Strategy"}

    def init(self):
        self.pivot_len_l = self.input.int(5, "Pivot Left Shoulder", minval=1)
        self.pivot_len_r = self.input.int(5, "Pivot Right Shoulder", minval=1)
        self.level_diff_per = self.input.float(0.5, "Level Proximity (%)", step=0.1) / 100
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_multiplier = self.input.float(2.0, "ATR Exhaustion Multiplier", step=0.1)
        self.vol_sma_len = self.input.int(20, "Volume SMA Length")
        self.vol_multiplier = self.input.float(1.5, "Volume Spike Multiplier", step=0.1)
        self.risk_per_trade = self.input.float(0.5, "Risk per Trade (%)", step=0.1) / 100
        self.rr_ratio = self.input.float(2.0, "Risk:Reward Ratio", step=0.1)
        self.last_ph = NA
        self.last_pl = NA

    def on_bar(self):
        ph = ta.pivothigh(self.pivot_len_l, self.pivot_len_r)
        pl = ta.pivotlow(self.pivot_len_l, self.pivot_len_r)
        if not na(ph):
            self.last_ph = ph
        if not na(pl):
            self.last_pl = pl
        atr = ta.atr(self.atr_length)
        dist_from_high = self.last_ph - self.low
        dist_from_low = self.close - self.last_pl
        is_exhausted_long = dist_from_high > (atr * self.atr_multiplier)
        is_exhausted_short = dist_from_low > (atr * self.atr_multiplier)
        vol_sma = ta.sma(self.volume, self.vol_sma_len)
        is_vol_spike = self.volume > vol_sma * self.vol_multiplier
        near_pl = self.low <= self.last_pl * (1 + self.level_diff_per) and self.low >= self.last_pl * (1 - self.level_diff_per)
        near_ph = self.high >= self.last_ph * (1 - self.level_diff_per) and self.high <= self.last_ph * (1 + self.level_diff_per)
        bullish_trigger = self.close > self.open or self.close > self.high[1]
        bearish_trigger = self.close < self.open or self.close < self.low[1]
        long_condition = near_pl and is_exhausted_long and is_vol_spike and bullish_trigger
        short_condition = near_ph and is_exhausted_short and is_vol_spike and bearish_trigger
        st = self.strategy
        if long_condition and st.position_size == 0:
            sl = self.last_pl if self.last_pl < self.low else float(self.low)
            risk_points = self.close - sl
            if risk_points > 0:
                tp = self.close + (risk_points * self.rr_ratio)
                amount_to_risk = st.equity * self.risk_per_trade
                qty = div(amount_to_risk, risk_points)
                st.entry("Long", st.long, qty=qty)
                st.exit("Exit Long", "Long", stop=sl, limit=tp)
        if short_condition and st.position_size == 0:
            sl = self.last_ph if self.last_ph > self.high else float(self.high)
            risk_points = sl - self.close
            if risk_points > 0:
                tp = self.close - (risk_points * self.rr_ratio)
                amount_to_risk = st.equity * self.risk_per_trade
                qty = div(amount_to_risk, risk_points)
                st.entry("Short", st.short, qty=qty)
                st.exit("Exit Short", "Short", stop=sl, limit=tp)
        self.plot(self.last_ph, "Resistance Level", color=color.red)
        self.plot(self.last_pl, "Support Level", color=color.green)
