"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : LuxAlgo SMC Pro Ultimate
Author       : not stated
Source URL   : https://www.tradingview.com/script/mEHJ2lCm
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market entries at the next open, 10 % of equity, pyramiding 1). Swing highs / lows are pivots with a
look-back of 9 (internal) and 50 (swing) bars, found by comparing the bar that many bars back with the highest high / lowest
low of the surrounding window. A close crossing the last internal and/or swing high (low) is a market-structure shift; a long
needs a shift up in the discount half of the 100-bar range and a bullish fair-value gap on this or the previous bar (a short is
the mirror image). Entry from flat only. The stop is 3 ATR(9) beyond the entry bar and trails the bar's low (high) at 3 ATR; once
the high (low) reaches the 1.5 R target a 50 % limit exit at the target is placed and the stop moves to the average entry price.
Deviations from the original: none.
Not carried over: labels, boxes, HUD table, background, the confluence score (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


def _na(x):
    return x != x


class LuxAlgoSmcPro(Script):
    TITLE = "LuxAlgo SMC Pro Ultimate"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, margin_long=100,
                    margin_short=100, currency="USD")
    SOURCE = {"id": "mEHJ2lCm", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/mEHJ2lCm"}

    def init(self):
        i = self.input
        self.structure_mode = i.string("All", "Structure Mode", options=["Internal", "Swing", "All"], group="Market Structure (MSS/BOS/CHoCH)")
        self.internal_lb = i.int(9, "Internal Lookback", minval=2, group="Market Structure (MSS/BOS/CHoCH)")
        self.swing_lb = i.int(50, "Swing Lookback", minval=2, group="Market Structure (MSS/BOS/CHoCH)")
        self.trade_direction = i.string("Both", "Trade Direction", options=["Both", "Long Only", "Short Only"], group="Market Structure (MSS/BOS/CHoCH)")
        self.use_fvg = i.bool(True, "Require FVG Presence", group="Order Blocks & FVGs")
        self.require_pd = i.bool(True, "Only Buy in Discount / Sell in Premium", group="Premium & Discount Zones")
        self.pd_lookback = i.int(100, "PD Range Lookback", minval=10, group="Premium & Discount Zones")
        self.use_div = i.bool(False, "Use Reversal Divergence Filter", group="Confirmation Filters")
        self.use_bb = i.bool(False, "Use Bollinger Band Filter", group="Confirmation Filters")
        self.vol_mult = i.float(1.2, "Volume Strength Multiplier", group="Signal Ranking & Volume")
        self.vol_candles = i.int(3, "Volume Momentum Check", minval=1, group="Signal Ranking & Volume")
        self.tp1_rr = i.float(1.5, "TP1 Risk:Reward", group="Risk Management")
        self.atr_mult = i.float(3.0, "ATR Stop Multiplier", group="Risk Management")
        self.atr_len = i.int(9, "ATR Length", group="Risk Management")
        # var state
        self.last_ish = NA
        self.last_isl = NA
        self.last_ssh = NA
        self.last_ssl = NA
        self.sl = NA
        self.tp1 = NA
        self.tp1_hit = False

    def on_bar(self):
        close, high, low = float(self.close), float(self.high), float(self.low)
        atr = ta.atr(self.atr_len)
        ta.sma(self.volume, 20)
        rsi = ta.rsi(self.close, 14)
        bb_mid, _, _ = ta.bb(self.close, 20, 2.0)
        range_high = ta.highest(self.high, self.pd_lookback)
        range_low = ta.lowest(self.low, self.pd_lookback)
        equilibrium = (range_high + range_low) / 2
        in_discount = close < equilibrium
        in_premium = close > equilibrium

        high_2, low_2, close_1 = self.high[2], self.low[2], self.close[1]
        b_fvg = low > high_2 and close_1 > high_2
        s_fvg = high < low_2 and close_1 < low_2
        b_fvg_prev = self.H("bfvg")[1] == 1
        s_fvg_prev = self.H("sfvg")[1] == 1
        self.H("bfvg").set(1.0 if b_fvg else 0.0)
        self.H("sfvg").set(1.0 if s_fvg else 0.0)

        ilb, slb = self.internal_lb, self.swing_lb
        hi_i = ta.highest(self.high, ilb * 2 + 1)
        lo_i = ta.lowest(self.low, ilb * 2 + 1)
        hi_s = ta.highest(self.high, slb * 2 + 1)
        lo_s = ta.lowest(self.low, slb * 2 + 1)
        i_sh = self.high[ilb] == hi_i
        i_sl = self.low[ilb] == lo_i
        if i_sh:
            self.last_ish = float(self.high[ilb])
        if i_sl:
            self.last_isl = float(self.low[ilb])
        s_sh = self.high[slb] == hi_s
        s_sl = self.low[slb] == lo_s
        if s_sh:
            self.last_ssh = float(self.high[slb])
        if s_sl:
            self.last_ssl = float(self.low[slb])

        xo_i = ta.crossover(self.close, self.last_ish)
        xu_i = ta.crossunder(self.close, self.last_isl)
        xo_s = ta.crossover(self.close, self.last_ssh)
        xu_s = ta.crossunder(self.close, self.last_ssl)
        mode = self.structure_mode
        mss_l = (mode == "Internal" and xo_i) or (mode == "Swing" and xo_s) or (mode == "All" and (xo_i or xo_s))
        mss_s = (mode == "Internal" and xu_i) or (mode == "Swing" and xu_s) or (mode == "All" and (xu_i or xu_s))

        rsi_prev, low_prev, high_prev = self.H("rsi")[1], self.low[1], self.high[1]
        self.H("rsi").set(rsi)
        bull_div = rsi > rsi_prev and low < low_prev
        bear_div = rsi < rsi_prev and high > high_prev

        b_trigger = mss_l and ((not self.require_pd) or in_discount) and ((not self.use_fvg) or b_fvg_prev or b_fvg) \
            and ((not self.use_div) or bull_div) and ((not self.use_bb) or close > bb_mid)
        s_trigger = mss_s and ((not self.require_pd) or in_premium) and ((not self.use_fvg) or s_fvg_prev or s_fvg) \
            and ((not self.use_div) or bear_div) and ((not self.use_bb) or close < bb_mid)

        st = self.strategy
        if b_trigger and st.position_size == 0 and self.trade_direction in ("Both", "Long Only"):
            self.sl = low - atr * self.atr_mult
            self.tp1 = close + (close - self.sl) * self.tp1_rr
            self.tp1_hit = False
            st.entry("Long", st.long, comment="SMC BUY")
        if s_trigger and st.position_size == 0 and self.trade_direction in ("Both", "Short Only"):
            self.sl = high + atr * self.atr_mult
            self.tp1 = close - (self.sl - close) * self.tp1_rr
            self.tp1_hit = False
            st.entry("Short", st.short, comment="SMC SELL")

        if st.position_size > 0:
            if not self.tp1_hit and high >= self.tp1:
                st.exit("TP1_L", "Long", qty_percent=50, limit=self.tp1, comment="TP1 Hit")
                self.tp1_hit = True
                self.sl = st.position_avg_price
            trail = low - atr * self.atr_mult
            if trail > self.sl:
                self.sl = trail
            st.exit("Exit_L", "Long", stop=self.sl, comment="SL/Trail")
        if st.position_size < 0:
            if not self.tp1_hit and low <= self.tp1:
                st.exit("TP1_S", "Short", qty_percent=50, limit=self.tp1, comment="TP1 Hit")
                self.tp1_hit = True
                self.sl = st.position_avg_price
            trail = high + atr * self.atr_mult
            if trail < self.sl:
                self.sl = trail
            st.exit("Exit_S", "Short", stop=self.sl, comment="SL/Trail")

        self.plot(self.sl if st.position_size != 0 else NA, title="Stop Loss")
