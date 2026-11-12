"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Kit Bot v1.2 - Silver
Author       : Benny_Steele
Source URL   : https://www.tradingview.com/script/ts9uZztj-Kit-Bot-v1-2-Silver
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Three entry gates (RSI turning in the 18-50 zone, close above the 9 EMA, a bar in the last five that touched the lower band) must all pass and at least `Min Bonus Confirmations` of five bonus conditions (band re-entry, hammer / engulfing / doji, pivot-based RSI divergence,
volume above its average, close above the 50 EMA) inside an enabled GMT session, at most `Max Trades Per Day` per trading day and while flat; shorts mirror it. A stop of ATR x multiplier and a target of the minimum reward / risk are placed with the entry.

Deviations from the original: none.
Not carried over: the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class KitBotSilverV12(Script):
    TITLE = "Kit Bot v1.2 - Silver"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=15, initial_capital=1000, commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "ts9uZztj", "author": "Benny_Steele", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ts9uZztj-Kit-Bot-v1-2-Silver"}

    def init(self):
        i = self.input
        g = "Strategy"
        self.min_confirmations = i.int(2, "Min Bonus Confirmations (on top of gates)", minval=1, maxval=4, group=g)
        self.max_trades_per_day = i.int(3, "Max Trades Per Day", minval=1, maxval=5, group=g)
        self.leverage = i.float(2.0, "Leverage", minval=1.0, maxval=5.0, step=0.5, group=g)
        self.min_rr = i.float(2.0, "Min Risk:Reward", minval=1.0, maxval=5.0, step=0.5, group=g)
        g = "Indicators"
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.bb_len = i.int(20, "BB Length", group=g)
        self.bb_mult = i.float(2.0, "BB Multiplier", group=g)
        self.ema_len = i.int(9, "EMA Length", group=g)
        self.ema50_len = i.int(50, "EMA 50 Length (trend)", group=g)
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.vol_mult = i.float(1.2, "Min Volume vs Average", minval=0.5, maxval=3.0, step=0.1, group=g)
        self.atr_mult = i.float(1.5, "ATR Stop Multiplier", minval=0.5, maxval=3.0, step=0.25, group=g)
        g = "Sessions"
        self.use_london = i.bool(True, "Trade London Session (07:00-16:00 GMT)", group=g)
        self.use_nyc = i.bool(True, "Trade NYC Session (13:30-21:00 GMT)", group=g)
        self.use_asian = i.bool(False, "Trade Asian Session (21:00-01:30 GMT) - Caution", group=g)
        self.trades_today = 0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        rsi = ta.rsi(close, self.rsi_len)
        bb_mid, bb_upper, bb_lower = ta.bb(close, self.bb_len, self.bb_mult)
        ema9 = ta.ema(close, self.ema_len)
        ema50 = ta.ema(close, self.ema50_len)
        atr = ta.atr(self.atr_len)
        avg_vol = ta.sma(self.volume, 20)
        rsi_h = self.H("rsi")
        rsi_1, rsi_3, rsi_6 = rsi_h[1], rsi_h[3], rsi_h[6]
        rsi_h.set(rsi)
        swing_high = ta.pivothigh(high, 3, 3)
        swing_low = ta.pivotlow(low, 3, 3)
        bearish_div = (not na(swing_high)) and high[3] > high[6] and rsi_3 < rsi_6 and rsi_3 > 60
        bullish_div = (not na(swing_low)) and low[3] < low[6] and rsi_3 > rsi_6 and rsi_3 < 40
        body_size = abs(close - open_)
        upper_wick = high - pmath.max(close, open_)
        lower_wick = pmath.min(close, open_) - low
        candle_range = high - low
        is_gravestone = candle_range > 0 and upper_wick > body_size * 2.5 and lower_wick < body_size * 0.3 and body_size > 0
        is_hammer = candle_range > 0 and lower_wick > body_size * 2.5 and upper_wick < body_size * 0.3 and body_size > 0
        is_doji = candle_range > 0 and body_size < candle_range * 0.08
        close_1, open_1 = close[1], open_[1]
        is_bullish_engulf = close > open_ and close_1 < open_1 and close > open_1 and open_ < close_1
        is_bearish_engulf = close < open_ and close_1 > open_1 and close < open_1 and open_ > close_1
        time_gmt = self.hour(self.time, "GMT") * 100 + self.minute(self.time, "GMT")
        in_london = self.use_london and (time_gmt >= 700 and time_gmt < 1600)
        in_nyc = self.use_nyc and (time_gmt >= 1330 and time_gmt < 2100)
        in_asian = self.use_asian and (time_gmt >= 2100 or time_gmt < 130)
        in_session = in_london or in_nyc or in_asian
        day_change = ta.change(self.time_fn("D"))
        if (not na(day_change)) and day_change != 0:
            self.trades_today = 0
        can_trade = self.trades_today < self.max_trades_per_day and in_session
        lowest5 = ta.lowest(low, 5)
        highest5 = ta.highest(high, 5)
        long_gate1 = rsi > rsi_1 and rsi < 50 and rsi > 18
        long_gate2 = close > ema9
        long_gate3 = lowest5 <= bb_lower
        long_gates_pass = long_gate1 and long_gate2 and long_gate3
        long_b1 = close > bb_lower and close_1 <= bb_lower
        long_b2 = is_hammer or is_bullish_engulf or (is_doji and close > open_ and lower_wick > upper_wick)
        long_b3 = bullish_div
        long_b4 = self.volume > avg_vol * self.vol_mult
        long_b5 = close > ema50
        long_bonus = (1 if long_b1 else 0) + (1 if long_b2 else 0) + (1 if long_b3 else 0) + (1 if long_b4 else 0) + (1 if long_b5 else 0)
        long_signal = long_gates_pass and long_bonus >= self.min_confirmations and can_trade and st.position_size == 0
        short_gate1 = rsi < rsi_1 and rsi > 55 and rsi < 82
        short_gate2 = close < ema9
        short_gate3 = highest5 >= bb_upper
        short_gates_pass = short_gate1 and short_gate2 and short_gate3
        short_b1 = close < bb_upper and close_1 >= bb_upper
        short_b2 = is_gravestone or is_bearish_engulf or (is_doji and close < open_ and upper_wick > lower_wick)
        short_b3 = bearish_div
        short_b4 = self.volume > avg_vol * self.vol_mult
        short_b5 = close < ema50
        short_bonus = (1 if short_b1 else 0) + (1 if short_b2 else 0) + (1 if short_b3 else 0) + (1 if short_b4 else 0) + (1 if short_b5 else 0)
        short_signal = short_gates_pass and short_bonus >= self.min_confirmations and can_trade and st.position_size == 0
        long_stop = close - (atr * self.atr_mult)
        long_target = close + (atr * self.atr_mult * self.min_rr)
        short_stop = close + (atr * self.atr_mult)
        short_target = close - (atr * self.atr_mult * self.min_rr)
        if long_signal:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=long_stop, limit=long_target)
            self.trades_today += 1
        if short_signal:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=short_stop, limit=short_target)
            self.trades_today += 1
