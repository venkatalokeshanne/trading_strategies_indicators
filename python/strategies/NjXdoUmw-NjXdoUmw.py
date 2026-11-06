"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Market Leader PRO v6 (Supertrend + Structure + Volume)
Author       : jinpin5811
Source URL   : https://www.tradingview.com/script/NjXdoUmw
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend(10, 3) flip to up (direction change < 0) above EMA200 with RSI(14) > 50, a close
above the previous 20-bar highest high and volume above its SMA20 goes long when flat (mirror: short). A flip against the
position closes it at the next open. While a position is open at the close, a 1.2 % target / 0.6 % stop around the average
price is issued, so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: the position backgrounds and the EMA / SuperTrend / level plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class MarketLeaderPro(Script):
    TITLE = "Market Leader PRO v6 (Supertrend + Structure + Volume)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=15)
    SOURCE = {"id": "NjXdoUmw", "author": "jinpin5811", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NjXdoUmw"}

    def init(self):
        self.atr_period = self.input.int(10, "ATR Length")
        self.factor = self.input.float(3.0, "Supertrend Factor")
        self.ema_len = self.input.int(200, "EMA Trend")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_level = self.input.int(50, "RSI Threshold")
        self.vol_len = self.input.int(20, "Volume SMA Length")
        self.lookback = self.input.int(20, "Breakout Lookback")
        self.tp_percent = self.input.float(1.2, "TP (%)")
        self.sl_percent = self.input.float(0.6, "SL (%)")

    def on_bar(self):
        st_line, direction = ta.supertrend(self.factor, self.atr_period)
        ema200 = ta.ema(self.close, self.ema_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        high_vol = self.volume > vol_ma
        highest_high = S(ta.highest(self.high, self.lookback))
        lowest_low = S(ta.lowest(self.low, self.lookback))
        chg = ta.change(direction)
        trend_up = self.close > ema200
        momentum_up = rsi > self.rsi_level
        st_up = chg < 0
        breakout_up = self.close > highest_high[1]
        long_signal = trend_up and momentum_up and st_up and breakout_up and high_vol
        trend_down = self.close < ema200
        momentum_down = rsi < self.rsi_level
        st_down = chg > 0
        breakout_down = self.close < lowest_low[1]
        short_signal = trend_down and momentum_down and st_down and breakout_down and high_vol
        st = self.strategy
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long)
        if short_signal and st.position_size == 0:
            st.entry("Short", st.short)
        if chg > 0 and st.position_size > 0:
            st.close("Long")
        if chg < 0 and st.position_size < 0:
            st.close("Short")
        if st.position_size > 0:
            st.exit("TP/SL Long", from_entry="Long", limit=st.position_avg_price * (1 + self.tp_percent / 100),
                    stop=st.position_avg_price * (1 - self.sl_percent / 100))
        if st.position_size < 0:
            st.exit("TP/SL Short", from_entry="Short", limit=st.position_avg_price * (1 - self.tp_percent / 100),
                    stop=st.position_avg_price * (1 + self.sl_percent / 100))
        self.plot(ema200, "EMA 200", color=color.yellow)
        self.plot(st_line, "Supertrend", color=color.green if direction < 0 else color.red)
