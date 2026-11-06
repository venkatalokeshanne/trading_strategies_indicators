"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Liquidity Sweep & RSI Divergence (Fixed $ Risk)
Author       : riipperz
Source URL   : https://www.tradingview.com/script/zCYYilCg-Liquidity-Sweep-RSI-Divergence-Fixed-Risk
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A dragonfly doji (body at most 10 % of the range, lower wick at least 70 %, upper wick at most 10 %)
whose low sweeps the lowest low of the previous 50 bars while RSI is above its own previous-50-bar low goes long when flat
(a gravestone doji sweeping the highest high with RSI below its previous high goes short). ta.lowest(low[1], n) is the lowest
of the n bars BEFORE this one, so it is read from the history of ta.lowest. The quantity is risk / distance to the stop (the
bar's extreme); entry and strategy.exit (stop at the extreme, 2.5 R target) are issued together on the signal bar, so the
bracket also works on the fill bar. No order when the distance is 0.

Deviations from the original: none.
Not carried over: the liquidity-level plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, pmath, ta


class LiquiditySweepRsiDiv(Script):
    TITLE = "Liquidity Sweep & RSI Divergence (Fixed $ Risk)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash")
    SOURCE = {"id": "zCYYilCg", "author": "riipperz", "licence": "not stated",
              "url": "https://www.tradingview.com/script/zCYYilCg-Liquidity-Sweep-RSI-Divergence-Fixed-Risk"}

    def init(self):
        self.risk_per_trade = self.input.float(50.0, "Risk Per Trade ($)")
        self.rr_ratio = self.input.float(2.5, "Risk:Reward Ratio")
        self.body_percent = self.input.float(10.0, "Max Body % of Range")
        self.wick_percent = self.input.float(70.0, "Min Wick % of Range")
        self.liquidity_lookback = self.input.int(50, "Liquidity Lookback")
        self.rsi_length = self.input.int(14, "RSI Length")

    def get_qty(self, sl_price):
        risk_per_share = pmath.abs(self.close - sl_price)
        return div(self.risk_per_trade, risk_per_share) if risk_per_share > 0 else 0

    def on_bar(self):
        rsi_value = ta.rsi(self.close, self.rsi_length)
        candle_range = self.high - self.low
        body_size = pmath.abs(self.open - self.close)
        upper_wick = self.high - pmath.max(self.open, self.close)
        lower_wick = pmath.min(self.open, self.close) - self.low
        is_doji = candle_range > 0 and body_size <= (candle_range * (self.body_percent / 100))
        is_dragonfly = is_doji and lower_wick >= (candle_range * (self.wick_percent / 100)) and upper_wick <= (candle_range * 0.1)
        is_gravestone = is_doji and upper_wick >= (candle_range * (self.wick_percent / 100)) and lower_wick <= (candle_range * 0.1)
        prev_low_level = S(ta.lowest(self.low, self.liquidity_lookback))[1]
        long_sweep = self.low < prev_low_level
        prev_rsi_low = S(ta.lowest(rsi_value, self.liquidity_lookback))[1]
        bull_divergence = rsi_value > prev_rsi_low
        prev_high_level = S(ta.highest(self.high, self.liquidity_lookback))[1]
        short_sweep = self.high > prev_high_level
        prev_rsi_high = S(ta.highest(rsi_value, self.liquidity_lookback))[1]
        bear_divergence = rsi_value < prev_rsi_high
        st = self.strategy
        if is_dragonfly and long_sweep and bull_divergence and st.position_size == 0:
            sl = float(self.low)
            qty = self.get_qty(sl)
            if qty > 0:
                tp = self.close + (pmath.abs(self.close - sl) * self.rr_ratio)
                st.entry("Long", st.long, qty=qty, comment="Risk $50")
                st.exit("Exit Long", "Long", stop=sl, limit=tp, comment_loss="SL -50", comment_profit="TP +125")
        if is_gravestone and short_sweep and bear_divergence and st.position_size == 0:
            sl = float(self.high)
            qty = self.get_qty(sl)
            if qty > 0:
                tp = self.close - (pmath.abs(sl - self.close) * self.rr_ratio)
                st.entry("Short", st.short, qty=qty, comment="Risk $50")
                st.exit("Exit Short", "Short", stop=sl, limit=tp, comment_loss="SL -50", comment_profit="TP +125")
        self.plot(prev_low_level, color=color.blue, title="Liquidity Low")
        self.plot(prev_high_level, color=color.red, title="Liquidity High")
