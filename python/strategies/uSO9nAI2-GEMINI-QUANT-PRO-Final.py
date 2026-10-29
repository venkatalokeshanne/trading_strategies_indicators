"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : GEMINI QUANT PRO - Final
Author       : smvdtravelsolutions
Source URL   : https://www.tradingview.com/script/uSO9nAI2-GEMINI-QUANT-PRO-Final
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Trend of a timeframe = +1 when its close is above its EMA 200, otherwise -1 (also while the EMA does not exist yet): daily and 4-hour (request.security, lookahead off) must agree. A bar that retests the EMA 44 from above (low at or under it, close back over it and over the EMA 200) with a volume over its 20-bar average
buys; the mirror image sells. The entry sets the stop (the bar's extreme with a buffer) and three reward multiples, but only the third is used: a stop and limit exit order for each side is re-issued every bar from those stored levels.
Deviations from the original: none.
Not carried over: the information panel (display only); the 1-hour and 15-minute trend values are only shown in that panel and are dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class GeminiQuantPro(Script):
    TITLE = "GEMINI QUANT PRO - Final"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash")
    SOURCE = {"id": "uSO9nAI2", "author": "smvdtravelsolutions", "licence": "not stated", "url": "https://www.tradingview.com/script/uSO9nAI2-GEMINI-QUANT-PRO-Final"}

    def init(self):
        i = self.input
        g = "EMA Settings (Backend)"
        self.ema44_len = i.int(44, "EMA 44 Length", group=g)
        self.ema200_len = i.int(200, "EMA 200 Length", group=g)
        g = "Risk Management (Pro)"
        self.tp1_mult = i.float(1.5, "TP1 Profit Ratio (RR)", group=g)
        self.tp2_mult = i.float(3.0, "TP2 Profit Ratio (RR)", group=g)
        self.tp3_mult = i.float(5.0, "TP3 Profit Ratio (RR)", group=g)
        self.sl_buffer = i.float(0.2, "SL Buffer (%)", group=g) / 100
        self.entry_price = NA
        self.sl = NA
        self.tp1 = NA
        self.tp2 = NA
        self.tp3 = NA

    def trend(self, tf_close, tf_ema):
        return 1 if tf_close > tf_ema else -1

    def on_bar(self):
        st = self.strategy
        close, low, high = self.close, self.low, self.high
        c1d = self.security(None, "D", lambda v: v.close, lookahead=False)
        e1d = self.security(None, "D", lambda v: ta.ema(v.close, self.ema200_len), lookahead=False)
        trend1d = self.trend(c1d, e1d)
        c4h = self.security(None, "240", lambda v: v.close, lookahead=False)
        e4h = self.security(None, "240", lambda v: ta.ema(v.close, self.ema200_len), lookahead=False)
        trend4h = self.trend(c4h, e4h)
        ema44 = ta.ema(close, self.ema44_len)
        ema200 = ta.ema(close, self.ema200_len)
        bull_retest = low <= ema44 and close > ema44 and close > ema200
        bear_retest = high >= ema44 and close < ema44 and close < ema200
        vol_filter = self.volume > ta.sma(self.volume, 20)
        long_condition = bull_retest and trend1d == 1 and trend4h == 1 and vol_filter
        short_condition = bear_retest and trend1d == -1 and trend4h == -1 and vol_filter
        if long_condition and st.position_size == 0:
            self.entry_price = float(close)
            self.sl = low * (1 - self.sl_buffer)
            risk = self.entry_price - self.sl
            self.tp1 = self.entry_price + (risk * self.tp1_mult)
            self.tp2 = self.entry_price + (risk * self.tp2_mult)
            self.tp3 = self.entry_price + (risk * self.tp3_mult)
            st.entry("Long", st.long)
        if short_condition and st.position_size == 0:
            self.entry_price = float(close)
            self.sl = high * (1 + self.sl_buffer)
            risk = self.sl - self.entry_price
            self.tp1 = self.entry_price - (risk * self.tp1_mult)
            self.tp2 = self.entry_price - (risk * self.tp2_mult)
            self.tp3 = self.entry_price - (risk * self.tp3_mult)
            st.entry("Short", st.short)
        st.exit("TP/SL Long", from_entry="Long", stop=self.sl, limit=self.tp3)
        st.exit("TP/SL Short", from_entry="Short", stop=self.sl, limit=self.tp3)
