"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 3策略自动切换综合版 - Range + Trend + Breakout
Author       : vrhzytr
Source URL   : https://www.tradingview.com/script/MoL1SwLE
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Three long-only entry regimes, any of which buys when flat: range (ADX < 25 inside the Bollinger
bands, RSI < 35, close within 1 % of the lower band, volume 1.2x average), trend (EMA50 crossing over EMA200 with ADX > 25,
RSI > 50, close above the Bollinger basis) and breakout (volume 1.8x average, close crossing over the upper band, ADX > 20,
RSI > 50, previous close under the previous upper band). While a position is open at the close a stop 1.5 ATR below
the average price and a target 2.5 R above it are issued, so they first work on the bar after the fill and always use the
previous bar's ATR.

Deviations from the original: none.
Not carried over: the regime background and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class ThreeStrategySwitch(Script):
    TITLE = "3策略自动切换综合版 - Range + Trend + Breakout"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=8, initial_capital=10000,
                    commission_type="percent", commission_value=0.07)
    SOURCE = {"id": "MoL1SwLE", "author": "vrhzytr", "licence": "not stated",
              "url": "https://www.tradingview.com/script/MoL1SwLE"}

    def init(self):
        self.rsi_len = self.input.int(14, "RSI长度")
        self.adx_len = self.input.int(14, "ADX长度")
        self.bb_len = self.input.int(20, "布林带长度")
        self.bb_mult = self.input.float(2.0, "布林带倍数")
        self.atr_len = self.input.int(14, "ATR长度")
        self.risk_pct = self.input.float(1.0, "单笔风险%", minval=0.5, step=0.1)
        self.rr_ratio = self.input.float(2.5, "止盈风险比", minval=1.5, step=0.1)

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_len)
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_len)
        bb_mid, bb_upper, bb_lower = ta.bb(self.close, self.bb_len, self.bb_mult)
        bb_upper_h = S(bb_upper)
        atr = ta.atr(self.atr_len)
        vol_ma = ta.sma(self.volume, 20)
        ema50 = ta.ema(self.close, 50)
        ema200 = ta.ema(self.close, 200)
        is_ranging = adx < 25 and self.close > bb_lower and self.close < bb_upper
        is_trending = adx > 25 and self.close > ema50 and ema50 > ema200
        cross_bb = ta.crossover(self.close, bb_upper)
        is_breakout = self.volume > vol_ma * 1.8 and cross_bb and adx > 20
        cross_ema = ta.crossover(ema50, ema200)
        range_long = is_ranging and rsi < 35 and self.close <= bb_lower * 1.01 and self.volume > vol_ma * 1.2
        trend_long = is_trending and cross_ema and rsi > 50 and self.close > bb_mid
        breakout_long = is_breakout and rsi > 50 and self.close[1] < bb_upper_h[1]
        st = self.strategy
        if range_long and st.position_size == 0:
            st.entry("Long", st.long)
        if trend_long and st.position_size == 0:
            st.entry("Long", st.long)
        if breakout_long and st.position_size == 0:
            st.entry("Long", st.long)
        if st.position_size > 0:
            stop_loss = st.position_avg_price - atr * 1.5
            take_profit = st.position_avg_price + (st.position_avg_price - stop_loss) * self.rr_ratio
            st.exit("Exit", "Long", stop=stop_loss, limit=take_profit)
