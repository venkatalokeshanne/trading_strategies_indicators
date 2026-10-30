"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Yuri Garcia Narrow State Strategy
Author       : YGD_CONSULTING_LLC
Source URL   : https://www.tradingview.com/script/x39mKkAp-Yuri-Garcia-Narrow-State-Strategy-YGILS
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A "narrow state" is EMA20 within 1.5 % of SMA200. In an uptrend (close and EMA20 above SMA200) a big
green bar (body over 1.5 ATR) or a green bar engulfing the previous red bar's high enters long when not already long
(downtrend mirror: short), subject to the Trade Direction setting. Both strategy.exit calls are unconditional with levels from the
current close (stop 2 ATR, target 4 ATR, rounded to the tick), so bar i works with the previous bar's levels - also on a fill bar.

Deviations from the original: none.
Not carried over: the EMA / SMA plots, narrow-state background, signal shapes, alertconditions and alert() JSON texts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class NarrowState(Script):
    TITLE = "Yuri Garcia Narrow State Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=2)
    SOURCE = {"id": "x39mKkAp", "author": "YGD_CONSULTING_LLC", "licence": "not stated",
              "url": "https://www.tradingview.com/script/x39mKkAp-Yuri-Garcia-Narrow-State-Strategy-YGILS"}

    def init(self):
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(2.0, "Stop Mult xATR")
        self.rrr = self.input.float(2.0, "RRR")
        self.trade_direction = self.input.string("Both", "Trade Direction", options=["Both", "Buy Only", "Sell Only"])
        self.ema_fast_len = self.input.int(20, "Fast EMA Length")
        self.sma_slow_len = self.input.int(200, "Slow SMA Length")
        self.mult_elephant = self.input.float(1.5, "Elephant Bar Multiplier")
        self.max_distance_pct = self.input.float(1.5, "Narrow State Max Distance Percent")

    def round_price(self, p):
        tick = self.syminfo.mintick
        return pmath.round(div(p, tick)) * tick

    def on_bar(self):
        can_buy = self.trade_direction == "Both" or self.trade_direction == "Buy Only"
        can_sell = self.trade_direction == "Both" or self.trade_direction == "Sell Only"
        atr = ta.atr(self.atr_len)
        ema20 = ta.ema(self.close, self.ema_fast_len)
        sma200 = ta.sma(self.close, self.sma_slow_len)
        ma_distance_pct = div(pmath.abs(ema20 - sma200), sma200) * 100
        is_narrow_state = ma_distance_pct <= self.max_distance_pct
        bullish_trend = self.close > sma200 and ema20 > sma200
        bearish_trend = self.close < sma200 and ema20 < sma200
        candle_body = pmath.abs(self.close - self.open)
        is_elephant = candle_body > atr * self.mult_elephant
        bullish_elephant = is_elephant and self.close > self.open and bullish_trend
        bearish_elephant = is_elephant and self.close < self.open and bearish_trend
        rbi_buy = bullish_trend and self.close[1] < self.open[1] and self.close > self.open and self.close > self.high[1]
        gbi_sell = bearish_trend and self.close[1] > self.open[1] and self.close < self.open and self.close < self.low[1]
        cond_long = (bullish_elephant or rbi_buy) and is_narrow_state
        cond_short = (bearish_elephant or gbi_sell) and is_narrow_state
        st = self.strategy
        new_long = cond_long and can_buy and st.position_size <= 0
        new_short = cond_short and can_sell and st.position_size >= 0
        long_sl = self.round_price(self.close - atr * self.atr_mult)
        short_sl = self.round_price(self.close + atr * self.atr_mult)
        long_tp = self.round_price(self.close + atr * self.atr_mult * self.rrr)
        short_tp = self.round_price(self.close - atr * self.atr_mult * self.rrr)
        if new_long:
            st.entry("LONG", st.long)
        if new_short:
            st.entry("SHORT", st.short)
        st.exit("TP SL LONG", from_entry="LONG", stop=long_sl, limit=long_tp)
        st.exit("TP SL SHORT", from_entry="SHORT", stop=short_sl, limit=short_tp)
        self.plot(ema20, title="20 EMA", color=color.lime if ema20 > sma200 else color.red, linewidth=2)
        self.plot(sma200, title="200 SMA", color=color.white, linewidth=3)
