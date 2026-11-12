"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Kit Bot v1.1 - Silver
Author       : Benny_Steele
Source URL   : https://www.tradingview.com/script/4bOVX7Ol-Kit-Bot-v1-1-Silver
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A score of independent confirmations (RSI turning, Bollinger band re-entry, EMA side, band midline, rejection candle, RSI divergence for longs; the mirrored set for shorts) must reach `Min Confirmations Required` inside an enabled London / New York / Asian session (GMT clock),
at most `Max Trades Per Day` per trading day and while flat; a stop of ATR x multiplier and a target of the minimum reward / risk are placed with the entry (the reward / risk test is evaluated in floating point, as in the original).

Deviations from the original: none.
Not carried over: the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class KitBotSilver(Script):
    TITLE = "Kit Bot v1.1 - Silver"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=15, initial_capital=1000, commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "4bOVX7Ol", "author": "Benny_Steele", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4bOVX7Ol-Kit-Bot-v1-1-Silver"}

    def init(self):
        i = self.input
        g = "Strategy"
        self.min_confirmations = i.int(3, "Min Confirmations Required", minval=2, maxval=6, group=g)
        self.max_trades_per_day = i.int(3, "Max Trades Per Day", minval=1, maxval=5, group=g)
        self.leverage = i.float(2.0, "Leverage", minval=1.0, maxval=5.0, step=0.5, group=g)
        self.min_rr = i.float(2.0, "Min Risk:Reward", minval=1.0, maxval=5.0, step=0.5, group=g)
        g = "Indicators"
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.bb_len = i.int(20, "BB Length", group=g)
        self.bb_mult = i.float(2.0, "BB Multiplier", group=g)
        self.ema_len = i.int(9, "EMA Length", group=g)
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_mult = i.float(1.5, "ATR Stop Multiplier", minval=0.5, maxval=3.0, step=0.25, group=g)
        g = "Sessions"
        self.use_london = i.bool(True, "Trade London Session (07:00-16:00 GMT)", group=g)
        self.use_nyc = i.bool(True, "Trade NYC Session (13:30-21:00 GMT)", group=g)
        self.use_asian = i.bool(False, "Trade Asian Session (21:00-01:30 GMT) !! Caution", group=g)
        self.trades_today = 0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        rsi = ta.rsi(close, self.rsi_len)
        rsi_prev = ta.rsi(close[1], self.rsi_len)
        bb_mid, bb_upper, bb_lower = ta.bb(close, self.bb_len, self.bb_mult)
        ema9 = ta.ema(close, self.ema_len)
        atr = ta.atr(self.atr_len)
        rsi_h = self.H("rsi")
        rsi_1 = rsi_h[1]
        rsi_h.set(rsi)
        close_1, high_1, low_1 = close[1], high[1], low[1]
        price_higher = high > high_1
        rsi_lower = rsi < rsi_1
        price_lower = low < low_1
        rsi_higher = rsi > rsi_1
        bearish_div = price_higher and rsi_lower and rsi_1 > 65
        bullish_div = price_lower and rsi_higher and rsi_1 < 35
        body_size = abs(close - open_)
        upper_wick = high - pmath.max(close, open_)
        lower_wick = pmath.min(close, open_) - low
        is_gravestone = upper_wick > body_size * 2 and lower_wick < body_size * 0.5 and body_size > 0
        is_hammer = lower_wick > body_size * 2 and upper_wick < body_size * 0.5 and body_size > 0
        is_doji = body_size < (high - low) * 0.1 and (high - low) > 0
        time_gmt = self.hour(self.time, "GMT") * 100 + self.minute(self.time, "GMT")
        in_london = self.use_london and (time_gmt >= 700 and time_gmt < 1600)
        in_nyc = self.use_nyc and (time_gmt >= 1330 and time_gmt < 2100)
        in_asian = self.use_asian and (time_gmt >= 2100 or time_gmt < 130)
        in_session = in_london or in_nyc or in_asian
        day_change = ta.change(self.time_fn("D"))
        if (not na(day_change)) and day_change != 0:
            self.trades_today = 0
        can_trade = self.trades_today < self.max_trades_per_day and in_session
        long_c1 = rsi < 55 and rsi > 20 and rsi > rsi_prev
        long_c2 = close > bb_lower and close_1 <= bb_lower
        long_c3 = close > ema9
        long_c4 = close > bb_mid or (close > bb_lower and close < bb_mid and rsi < 40)
        long_c5 = is_hammer or (is_doji and close > open_)
        long_c6 = bullish_div
        long_score = (1 if long_c1 else 0) + (1 if long_c2 else 0) + (1 if long_c3 else 0) + (1 if long_c4 else 0) + (1 if long_c5 else 0) + (1 if long_c6 else 0)
        long_signal = long_score >= self.min_confirmations and can_trade and st.position_size == 0
        short_c1 = rsi > 65 and rsi < rsi_prev
        short_c2 = close < bb_upper and close_1 >= bb_upper
        short_c3 = close < ema9
        short_c4 = is_gravestone or (is_doji and close < open_)
        short_c5 = bearish_div
        short_c6 = rsi_1 > 70 and rsi < 70
        short_score = (1 if short_c1 else 0) + (1 if short_c2 else 0) + (1 if short_c3 else 0) + (1 if short_c4 else 0) + (1 if short_c5 else 0) + (1 if short_c6 else 0)
        short_signal = short_score >= self.min_confirmations and can_trade and st.position_size == 0
        long_stop = close - (atr * self.atr_mult)
        long_target = close + (atr * self.atr_mult * self.min_rr)
        short_stop = close + (atr * self.atr_mult)
        short_target = close - (atr * self.atr_mult * self.min_rr)
        long_rr = div(long_target - close, close - long_stop)
        short_rr = div(close - short_target, short_stop - close)
        if long_signal and long_rr >= self.min_rr:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=long_stop, limit=long_target)
            self.trades_today += 1
        if short_signal and short_rr >= self.min_rr:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=short_stop, limit=short_target)
            self.trades_today += 1
