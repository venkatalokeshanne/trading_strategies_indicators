"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SuperTrend + EMA Strategy [BTC-USD]
Author       : not stated
Source URL   : https://www.tradingview.com/script/sNFXyA3m
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, one contract, pyramiding 0). A SuperTrend (hl2 +/- 3 ATR(10), the old
close[1]-based band rule) is requested with lookahead on from the chosen timeframe (blank = chart); the function hands back the
PREVIOUS bar's bands and trend, so on the chart timeframe the trend is one bar late. A long needs a trend flip to up with EMA50 over
EMA200, or an EMA50/EMA200 cross up while the trend is up, and the "market is trending" filter: ADX >= 20, EMA separation >= 0.5 %
and Choppiness Index <= 61.8. Shorts mirror. A flip against the position closes it, unfiltered.
Deviations from the original: none.
Not carried over: plots, fills, background colours, the status label.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


class SuperTrendEmaBtc(Script):
    TITLE = "SuperTrend + EMA Strategy [BTC-USD]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=100000, currency="USD", pyramiding=0)
    SOURCE = {"id": "sNFXyA3m", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/sNFXyA3m"}

    def init(self):
        i = self.input
        self.periods = i.int(10, "ATR Period", group="SuperTrend Settings")
        self.multiplier = i.float(3.0, "ATR Multiplier", step=0.1, group="SuperTrend Settings")
        self.change_atr = i.bool(True, "Use ATR (vs SMA of TR)?", group="SuperTrend Settings")
        self.st_tf = i.timeframe("", "SuperTrend Timeframe (blank = chart TF)", group="SuperTrend Settings")
        self.ema50_period = i.int(50, "EMA Fast Period", group="EMA Settings")
        self.ema200_period = i.int(200, "EMA Slow Period", group="EMA Settings")
        self.use_adx = i.bool(True, "Enable ADX Filter", group="Chop Filters")
        self.adx_period = i.int(14, "ADX Period", minval=1, group="Chop Filters")
        self.adx_min = i.int(20, "ADX Minimum Level", minval=1, group="Chop Filters")
        self.use_ema_sep = i.bool(True, "Enable EMA Separation Filter", group="Chop Filters")
        self.ema_sep_min = i.float(0.5, "Min EMA Separation %", step=0.1, minval=0.0, group="Chop Filters")
        self.use_chop = i.bool(True, "Enable Choppiness Index Filter", group="Chop Filters")
        self.chop_period = i.int(14, "Choppiness Period", minval=2, group="Chop Filters")
        self.chop_max = i.float(61.8, "Max CHOP Level (above = choppy)", step=0.1, group="Chop Filters")
        # SuperTrend state, advanced once per requested bar: previous bar's final up / dn / trend
        self.stst = {"up": NA, "dn": NA, "trend": NA}

    def _supertrend_confirmed(self, v):
        """f_supertrend_confirmed: returns the previous bar's [up, dn, trend]."""
        s = self.stst
        prev = (s["up"], s["dn"], s["trend"])
        src = float(v.hl2)
        atr = ta.atr(self.periods) if self.change_atr else ta.sma(ta.tr(), self.periods)
        close = float(v.close)
        close1 = v.close[1]
        up = src - self.multiplier * atr
        up1 = up if s["up"] != s["up"] else s["up"]
        if close1 > up1:
            up = max(up, up1)
        dn = src + self.multiplier * atr
        dn1 = dn if s["dn"] != s["dn"] else s["dn"]
        if close1 < dn1:
            dn = min(dn, dn1)
        trend = 1 if s["trend"] != s["trend"] else s["trend"]
        if trend == -1 and close > dn1:
            trend = 1
        elif trend == 1 and close < up1:
            trend = -1
        s["up"], s["dn"], s["trend"] = up, dn, trend
        return prev

    def on_bar(self):
        use_mtf = self.st_tf != ""
        resolved_tf = self.st_tf if use_mtf else self.timeframe.period
        up_htf, dn_htf, trend_htf = self.security(self.syminfo.tickerid, resolved_tf, self._supertrend_confirmed, lookahead=True)
        trend_prev = self.H("trend")[1]
        self.H("trend").set(trend_htf)

        ema50 = ta.ema(self.close, self.ema50_period)
        ema200 = ta.ema(self.close, self.ema200_period)

        _, _, adx_value = ta.dmi(self.adx_period, self.adx_period)
        adx_pass = (not self.use_adx) or (adx_value >= self.adx_min)

        ema_sep_pct = div(pmath.abs(ema50 - ema200), ema200) * 100
        ema_sep_pass = (not self.use_ema_sep) or (ema_sep_pct >= self.ema_sep_min)

        chop_atr = ta.atr(1)
        chop_hh = ta.highest(self.high, self.chop_period)
        chop_ll = ta.lowest(self.low, self.chop_period)
        chop_sum = ta.msum(chop_atr, self.chop_period)
        chop_range = chop_hh - chop_ll
        if chop_range > 0:
            chop_index = div(100.0 * pmath.log10(div(chop_sum, chop_range)), pmath.log10(self.chop_period))
        else:
            chop_index = 50.0
        chop_pass = (not self.use_chop) or (chop_index <= self.chop_max)

        market_is_trending = adx_pass and ema_sep_pass and chop_pass

        st_bullish = trend_htf == 1
        st_bearish = trend_htf == -1
        st_flip_buy = trend_htf == 1 and trend_prev == -1
        st_flip_sell = trend_htf == -1 and trend_prev == 1

        ema_bullish = ema50 > ema200
        ema_bearish = ema50 < ema200
        ema_cross_bull = ta.crossover(ema50, ema200)
        ema_cross_bear = ta.crossunder(ema50, ema200)

        fresh_buy = ((st_flip_buy and ema_bullish) or (ema_cross_bull and st_bullish)) and market_is_trending
        fresh_sell = ((st_flip_sell and ema_bearish) or (ema_cross_bear and st_bearish)) and market_is_trending

        st = self.strategy
        if st_flip_sell:
            st.close("Long", comment="BUY Exit")
        if st_flip_buy:
            st.close("Short", comment="SELL Exit")
        if fresh_buy:
            st.entry("Long", st.long, comment="BUY: ST↑ + EMA50>EMA200")
        if fresh_sell:
            st.entry("Short", st.short, comment="SELL: ST↓ + EMA50<EMA200")

        self.plot(ema50, title="EMA 50")
        self.plot(ema200, title="EMA 200")
