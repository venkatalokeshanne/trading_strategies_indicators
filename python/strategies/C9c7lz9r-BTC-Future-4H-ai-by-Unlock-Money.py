"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Future 4H ai by Unlock Money
Author       : UnlockMoney
Source URL   : https://www.tradingview.com/script/C9c7lz9r-BTC-Future-4H-ai-by-Unlock-Money
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The EMAs 21 > 55 > 200 (or the mirror), the RSI inside its long (45-75) / short (25-55) band, a Supertrend flip in the trend direction and (optionally) a volume above its average, while flat, enter at the next open. The stop is the wider of an ATR multiple
and the swing extreme (lowest low / highest high over the lookback) pushed out by the wick buffer; two exit orders of 50 % each target the first and second risk multiples from the signal close, both with that stop.
Deviations from the original: none.
Not carried over: the signal markers and the information labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, pmath, ta


class BtcFuture4h(Script):
    TITLE = "BTC Future 4H ai by Unlock Money"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.05, slippage=2)
    SOURCE = {"id": "C9c7lz9r", "author": "UnlockMoney", "licence": "not stated", "url": "https://www.tradingview.com/script/C9c7lz9r-BTC-Future-4H-ai-by-Unlock-Money"}

    def init(self):
        i = self.input
        self.ema_fast = i.int(21, "EMA Fast")
        self.ema_mid = i.int(55, "EMA Mid")
        self.ema_slow = i.int(200, "EMA Slow")
        self.rsi_len = i.int(14, "RSI Length")
        self.st_factor = i.float(3.0, "Supertrend Factor")
        self.st_len = i.int(10, "Supertrend Length")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_multi = i.float(2.0, "ATR SL Multiplier", minval=1.5, maxval=4.0, step=0.1)
        self.swing_len = i.int(5, "Swing Lookback (bars)", minval=3, maxval=10)
        self.wick_buffer = i.float(0.3, "Wick Buffer %", minval=0.1, maxval=1.0, step=0.1)
        self.tp1_rr = i.float(1.5, "TP1 RR")
        self.tp2_rr = i.float(2.5, "TP2 RR")
        self.use_vol = i.bool(True, "Volume Filter")
        self.vol_len = i.int(20, "Volume MA Length")
        self.prev_st_bull = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema21 = ta.ema(close, self.ema_fast)
        ema55 = ta.ema(close, self.ema_mid)
        ema200 = ta.ema(close, self.ema_slow)
        rsi = ta.rsi(close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        st_line, st_dir = ta.supertrend(self.st_factor, self.st_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        swing_low = ta.lowest(self.low, self.swing_len)
        swing_high = ta.highest(self.high, self.swing_len)
        trend_bull = ema21 > ema55 and ema55 > ema200
        trend_bear = ema21 < ema55 and ema55 < ema200
        rsi_long_ok = rsi >= 45 and rsi <= 75
        rsi_short_ok = rsi >= 25 and rsi <= 55
        st_bull = st_dir < 0
        st_flip_bull = st_bull and not self.prev_st_bull
        st_flip_bear = (not st_bull) and self.prev_st_bull
        self.prev_st_bull = bool(st_bull)
        vol_ok = (not self.use_vol) or (self.volume > vol_ma)
        long_signal = trend_bull and rsi_long_ok and st_flip_bull and vol_ok
        short_signal = trend_bear and rsi_short_ok and st_flip_bear and vol_ok
        long_entry = close
        short_entry = close
        long_sl_atr = long_entry - atr * self.atr_multi
        long_sl_swing = swing_low * (1 - self.wick_buffer / 100)
        long_sl = pmath.min(long_sl_atr, long_sl_swing)
        short_sl_atr = short_entry + atr * self.atr_multi
        short_sl_swing = swing_high * (1 + self.wick_buffer / 100)
        short_sl = pmath.max(short_sl_atr, short_sl_swing)
        long_risk = long_entry - long_sl
        short_risk = short_sl - short_entry
        long_tp1 = long_entry + long_risk * self.tp1_rr
        long_tp2 = long_entry + long_risk * self.tp2_rr
        short_tp1 = short_entry - short_risk * self.tp1_rr
        short_tp2 = short_entry - short_risk * self.tp2_rr
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long)
            st.exit("Long TP1", "Long", qty_percent=50, limit=long_tp1, stop=long_sl)
            st.exit("Long TP2", "Long", qty_percent=50, limit=long_tp2, stop=long_sl)
        if short_signal and st.position_size == 0:
            st.entry("Short", st.short)
            st.exit("Short TP1", "Short", qty_percent=50, limit=short_tp1, stop=short_sl)
            st.exit("Short TP2", "Short", qty_percent=50, limit=short_tp2, stop=short_sl)
