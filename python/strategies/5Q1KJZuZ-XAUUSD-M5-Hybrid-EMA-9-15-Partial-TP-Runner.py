"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD M5 Hybrid EMA 9/15 (Partial TP + Runner)
Author       : MUHAMMEDIJAZ721
Source URL   : https://www.tradingview.com/script/5Q1KJZuZ-XAUUSD-M5-Hybrid-EMA-9-15-Partial-TP-Runner
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Trend = the 9 EMA above (below) the 15 EMA on the chart AND on the 15-minute timeframe (request.security, lookahead off); a bar with a long lower (upper) wick of more than 1.5x its body that closes up (down) in an up (down) trend
enters long (short). The entry issues two exit orders from it: a partial target (50 % of the quantity) one TP1 away from the signal close, and a runner order for the rest with a take-profit TP2 away, a stop at the slow (fast) EMA -/+ the buffer and a trailing stop
(activates after 1.5 ticks of profit, trails by 1 tick). Entry signals on later bars while the trade is open are ignored by the broker (no pyramiding) but re-issue the exit orders at the new levels.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class XauHybridEma(Script):
    TITLE = "XAUUSD M5 Hybrid EMA 9/15 (Partial TP + Runner)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "5Q1KJZuZ", "author": "MUHAMMEDIJAZ721", "licence": "not stated",
              "url": "https://www.tradingview.com/script/5Q1KJZuZ-XAUUSD-M5-Hybrid-EMA-9-15-Partial-TP-Runner"}

    def init(self):
        i = self.input
        self.ema_fast_len = i.int(9, "EMA 9")
        self.ema_slow_len = i.int(15, "EMA 15")
        self.tp1 = i.float(1.0, "Partial TP (≈10 pips)")
        self.tp2 = i.float(5.0, "Runner TP (≈50 pips)")
        self.sl_buffer = i.float(0.3, "SL Buffer")

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        ema_fast_htf = self.security(None, "15", lambda v: ta.ema(v.close, self.ema_fast_len), lookahead=False)
        ema_slow_htf = self.security(None, "15", lambda v: ta.ema(v.close, self.ema_slow_len), lookahead=False)
        bull_trend = ema_fast > ema_slow and ema_fast_htf > ema_slow_htf
        bear_trend = ema_fast < ema_slow and ema_fast_htf < ema_slow_htf
        body = abs(close - open_)
        upper_wick = high - max(close, open_)
        lower_wick = min(close, open_) - low
        bullish_rejection = lower_wick > body * 1.5 and close > open_
        bearish_rejection = upper_wick > body * 1.5 and close < open_
        buy_condition = bull_trend and bullish_rejection
        sell_condition = bear_trend and bearish_rejection
        long_sl = ema_slow - self.sl_buffer
        short_sl = ema_fast + self.sl_buffer
        if buy_condition:
            st.entry("BUY", st.long)
            st.exit("TP1 BUY", from_entry="BUY", limit=close + self.tp1, qty_percent=50)
            st.exit("TP2 BUY", from_entry="BUY", limit=close + self.tp2, stop=long_sl, trail_points=1.5, trail_offset=1)
        if sell_condition:
            st.entry("SELL", st.short)
            st.exit("TP1 SELL", from_entry="SELL", limit=close - self.tp1, qty_percent=50)
            st.exit("TP2 SELL", from_entry="SELL", limit=close - self.tp2, stop=short_sl, trail_points=1.5, trail_offset=1)
