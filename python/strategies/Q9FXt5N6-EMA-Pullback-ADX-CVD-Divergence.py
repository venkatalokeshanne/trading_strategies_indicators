"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Pullback + ADX + CVD Divergence
Author       : ravishankarbridge
Source URL   : https://www.tradingview.com/script/Q9FXt5N6-EMA-Pullback-ADX-CVD-Divergence
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An EMA9 / EMA20 cross arms a buy (bull cross) or sell (bear cross) wait flag; the entry fires
on a pullback to either EMA with ADX above the threshold, a price/CVD divergence versus the previous 10 bars
(ta.lowest(low[1], n) is the lowest of the n bars BEFORE this one, so it is read from the history of ta.lowest) and a
candle of the right colour, then clears the flag. Entry and strategy.exit (stop = lowest low / highest high of 5 bars,
limit = RR times the risk) are issued on the signal bar, so the bracket also works on the fill bar; a repeat signal on
the open side re-issues the exit.

Deviations from the original: none.
Not carried over: the EMA plots, BUY / SELL shapes and the alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class EmaPullbackAdxCvd(Script):
    TITLE = "EMA Pullback + ADX + CVD Divergence"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "Q9FXt5N6", "author": "ravishankarbridge", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Q9FXt5N6-EMA-Pullback-ADX-CVD-Divergence"}

    def init(self):
        self.adx_len = self.input.int(14, "ADX Length")
        self.adx_threshold = self.input.int(25, "ADX Threshold")
        self.rr = self.input.float(3.0, "RR")
        self.lookback = self.input.int(10, "Divergence Lookback")
        self.wait_buy = False
        self.wait_sell = False

    def on_bar(self):
        ema9 = ta.ema(self.close, 9)
        ema20 = ta.ema(self.close, 20)
        plus_di, minus_di, adx = ta.dmi(self.adx_len, self.adx_len)
        delta = self.volume if self.close > self.open else (-self.volume if self.close < self.open else 0)
        cvd = S(ta.cum(delta))
        low_lo = S(ta.lowest(self.low, self.lookback))
        high_hi = S(ta.highest(self.high, self.lookback))
        cvd_lo = S(ta.lowest(cvd, self.lookback))
        cvd_hi = S(ta.highest(cvd, self.lookback))
        price_ll = self.low < low_lo[1]
        cvd_hl = cvd > cvd_lo[1]
        bull_div = price_ll and cvd_hl
        price_hh = self.high > high_hi[1]
        cvd_lh = cvd < cvd_hi[1]
        bear_div = price_hh and cvd_lh
        bull_cross = ta.crossover(ema9, ema20)
        bear_cross = ta.crossunder(ema9, ema20)
        if bull_cross:
            self.wait_buy = True
            self.wait_sell = False
        if bear_cross:
            self.wait_sell = True
            self.wait_buy = False
        pullback_buy = self.wait_buy and (self.low <= ema9 or self.low <= ema20)
        pullback_sell = self.wait_sell and (self.high >= ema9 or self.high >= ema20)
        strong_trend = adx > self.adx_threshold
        buy_signal = pullback_buy and strong_trend and bull_div and self.close > self.open
        sell_signal = pullback_sell and strong_trend and bear_div and self.close < self.open
        if buy_signal:
            self.wait_buy = False
        if sell_signal:
            self.wait_sell = False
        swing_low = ta.lowest(self.low, 5)
        swing_high = ta.highest(self.high, 5)
        buy_sl = swing_low
        sell_sl = swing_high
        buy_risk = self.close - buy_sl
        sell_risk = sell_sl - self.close
        buy_tp = self.close + (buy_risk * self.rr)
        sell_tp = self.close - (sell_risk * self.rr)
        st = self.strategy
        if buy_signal:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", from_entry="BUY", stop=buy_sl, limit=buy_tp)
        if sell_signal:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", from_entry="SELL", stop=sell_sl, limit=sell_tp)
        self.plot(ema9, color=color.green)
        self.plot(ema20, color=color.red)
