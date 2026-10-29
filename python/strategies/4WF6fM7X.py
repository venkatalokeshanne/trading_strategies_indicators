"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Naked K 5min Sniper
Author       : wtbm8821
Source URL   : https://www.tradingview.com/script/4WF6fM7X
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). In an up-trend (close over the 9 SMA) a bar whose low is within 0.2 % of the lowest low of the lookback, forming a bullish pin bar (long lower shadow, tiny upper shadow, range over half the ATR) or a bullish engulfing, and closing above the previous high with a volume of at least 1.2 x its 5-bar average,
buys; the mirror image in a down-trend sells. After a signal no new trade is taken for the cooldown bars. Each entry issues a combined stop (previous bar's extreme -/+ ATR x multiple) and take-profit (risk x reward ratio from the close).
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class NakedKSniper(Script):
    TITLE = "Naked K 5min Sniper"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "4WF6fM7X", "author": "wtbm8821", "licence": "not stated", "url": "https://www.tradingview.com/script/4WF6fM7X"}

    def init(self):
        i = self.input
        self.lookback = i.int(6, "支撑/阻力回溯K线数", minval=3, maxval=12)
        self.sma_len = i.int(9, "趋势SMA周期", minval=5, maxval=20)
        self.atr_len = i.int(7, "ATR周期", minval=5)
        self.atr_mult_sl = i.float(1.8, "止损ATR倍数", minval=1.0, step=0.1)
        self.rr_ratio = i.float(1.5, "止盈风险回报比", minval=1.0, step=0.1)
        self.use_volume_filter = i.bool(True, "启用成交量过滤（需有成交量数据）")
        self.cooldown_bars = i.int(3, "交易冷却期（K线数）", minval=0)
        self.last_trade_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        sma_fast = ta.sma(close, self.sma_len)
        uptrend = close > sma_fast
        downtrend = close < sma_fast
        recent_low = ta.lowest(low, self.lookback)
        recent_high = ta.highest(high, self.lookback)
        near_support = low <= recent_low * 1.002
        near_resistance = high >= recent_high * 0.998
        body = abs(open_ - close)
        candle_range = high - low
        lower_shadow = pmath.min(open_, close) - low
        upper_shadow = high - pmath.max(open_, close)
        atr = ta.atr(self.atr_len)
        is_bull_pin = lower_shadow >= 2 * body and upper_shadow <= 0.3 * body and candle_range > atr * 0.5
        is_bear_pin = upper_shadow >= 2 * body and lower_shadow <= 0.3 * body and candle_range > atr * 0.5
        open_1, close_1, high_1, low_1 = self.open[1], self.close[1], self.high[1], self.low[1]
        bull_engulf = open_1 > close_1 and close > open_ and close > open_1 and open_ < close_1
        bear_engulf = open_1 < close_1 and close < open_ and close < open_1 and open_ > close_1
        vol_avg = ta.sma(self.volume, 5)
        vol_ok = (not self.use_volume_filter) or self.volume >= vol_avg * 1.2
        bullish_pattern = is_bull_pin or bull_engulf
        bearish_pattern = is_bear_pin or bear_engulf
        long_signal = uptrend and near_support and bullish_pattern and close > high_1 and vol_ok
        short_signal = downtrend and near_resistance and bearish_pattern and close < low_1 and vol_ok
        in_cooldown = (not na(self.last_trade_bar)) and (self.bar_index - self.last_trade_bar) <= self.cooldown_bars
        if long_signal and not in_cooldown:
            sl = low_1 - self.atr_mult_sl * atr
            tp = close + self.rr_ratio * (close - sl)
            st.entry("Long", st.long)
            st.exit("TP/SL", from_entry="Long", stop=sl, limit=tp)
            self.last_trade_bar = self.bar_index
        if short_signal and not in_cooldown:
            sl = high_1 + self.atr_mult_sl * atr
            tp = close - self.rr_ratio * (sl - close)
            st.entry("Short", st.short)
            st.exit("TP/SL", from_entry="Short", stop=sl, limit=tp)
            self.last_trade_bar = self.bar_index
