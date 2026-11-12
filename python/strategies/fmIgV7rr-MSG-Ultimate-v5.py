"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MSG Ultimate v5.1
Author       : PRECISION_ALGO
Source URL   : https://www.tradingview.com/script/fmIgV7rr-MSG-Ultimate-v5
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The "mean" of each session (Asia 00:00 - 06:00, London 07:00 - 12:00, New York 13:00 - 17:00, exchange time) is the midpoint of its first bar (recorded while "Show Session Boxes" is on). The previous mean is the latest recorded one (New York, else London, else Asia) and the current mean that of the session the bar is in.
A buy needs the close above both means plus half an ATR and above the 50 EMA (sell mirrored) inside an enabled session, with the probability score at the minimum; one trade per session start (the flag is cleared at each session start). The entry carries an exit order whose ATR stop and target are re-issued from each bar's close.
Deviations from the original: none.
Not carried over: the boxes, labels, bias colours, entry dots, alerts and dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class MsgUltimate(Script):
    TITLE = "MSG Ultimate v5.1"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=0)
    SOURCE = {"id": "fmIgV7rr", "author": "PRECISION_ALGO", "licence": "not stated", "url": "https://www.tradingview.com/script/fmIgV7rr-MSG-Ultimate-v5"}

    def init(self):
        i = self.input
        self.show_sessions = i.bool(True, "Show Session Boxes")
        self.trade_asia = i.bool(False, "Trade Asia")
        self.trade_london = i.bool(True, "Trade London")
        self.trade_ny = i.bool(True, "Trade New York")
        self.ema_len = i.int(50, "EMA Length")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_mult = i.float(1.5, "TP/SL Multiplier")
        self.min_prob = i.int(50, "Min Probability")
        self.asia = i.session("0000-0600", "Asia Session")
        self.london = i.session("0700-1200", "London Session")
        self.ny = i.session("1300-1700", "NY Session")
        self.asia_mean = NA
        self.london_mean = NA
        self.ny_mean = NA
        self.traded = False
        self.prev = [False, False, False]

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        in_asia = self.time_in_session(self.asia)
        in_london = self.time_in_session(self.london)
        in_ny = self.time_in_session(self.ny)
        asia_start = in_asia and not self.prev[0]
        london_start = in_london and not self.prev[1]
        ny_start = in_ny and not self.prev[2]
        self.prev = [bool(in_asia), bool(in_london), bool(in_ny)]
        valid_session = (in_asia and self.trade_asia) or (in_london and self.trade_london) or (in_ny and self.trade_ny)
        ema = ta.ema(close, self.ema_len)
        atr = ta.atr(self.atr_len)
        buffer = atr * 0.5
        if self.show_sessions:
            if asia_start:
                self.asia_mean = (high + low) / 2
            if london_start:
                self.london_mean = (high + low) / 2
            if ny_start:
                self.ny_mean = (high + low) / 2
        prev_mean = self.ny_mean if not na(self.ny_mean) else (self.london_mean if not na(self.london_mean) else self.asia_mean)
        current_mean = self.ny_mean if in_ny else (self.london_mean if in_london else self.asia_mean)
        bias = 1 if close > current_mean else -1
        bull = close > prev_mean + buffer and close > current_mean + buffer and close > ema
        bear = close < prev_mean - buffer and close < current_mean - buffer and close < ema
        score = (1 if bull else 0) + (1 if bear else 0)
        prob = pmath.min(100, 30 + score * 35)
        buy = bull and bias == 1 and prob >= self.min_prob and valid_session
        sell = bear and bias == -1 and prob >= self.min_prob and valid_session
        if asia_start or london_start or ny_start:
            self.traded = False
        if buy and not self.traded:
            st.entry("BUY", st.long)
            self.traded = True
        if sell and not self.traded:
            st.entry("SELL", st.short)
            self.traded = True
        long_tp = close + atr * self.atr_mult
        long_sl = close - atr * self.atr_mult
        short_tp = close - atr * self.atr_mult
        short_sl = close + atr * self.atr_mult
        st.exit("TP BUY", from_entry="BUY", limit=long_tp, stop=long_sl)
        st.exit("TP SELL", from_entry="SELL", limit=short_tp, stop=short_sl)
