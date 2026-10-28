"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : PRO Investing - Nasdaq Silver Bullet (%) Strategy (1hr)
Author       : PRO-Investing
Source URL   : https://www.tradingview.com/script/gRKaz4L6-PRO-Investing-Nasdaq-Silver-Bullet-Strategy-1hr
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Inside the 10:00-11:00 New York window, N consecutive same-colour candles in the EMA200 direction enter when flat. The percentage stop / target around position_avg_price are
issued while a position exists (they first work on the bar after the fill) and any open trade is closed on the first bar outside the window.

Deviations from the original: none.
Not carried over: EMA plot, window background and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class SilverBullet(Script):
    TITLE = "PRO Investing - Nasdaq Silver Bullet (%) Strategy (1hr)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "gRKaz4L6", "author": "PRO-Investing", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gRKaz4L6-PRO-Investing-Nasdaq-Silver-Bullet-Strategy-1hr"}

    def init(self):
        self.sb_time = self.input.session("1000-1100", "Silver Bullet Window (EST/New York)")
        self.count_needed = self.input.int(2, "Candle Count Confirmation", minval=1)
        self.use_ema = self.input.bool(True, "Use 200 EMA Filter?")
        self.sl_percent = self.input.float(0.3, "Stop Loss (%)", minval=0.01, step=0.1)
        self.tp_percent = self.input.float(0.6, "Take Profit (%)", minval=0.01, step=0.1)
        self.up_count = 0
        self.dn_count = 0

    def on_bar(self):
        is_sb_window = not na(self.time_fn(None, self.sb_time, "America/New_York"))
        ema200 = ta.ema(self.close, 200)
        if self.close > self.open:
            self.up_count += 1
            self.dn_count = 0
        elif self.close < self.open:
            self.dn_count += 1
            self.up_count = 0
        else:
            self.up_count = 0
            self.dn_count = 0
        long_cond = is_sb_window and self.up_count >= self.count_needed and ((not self.use_ema) or self.close > ema200)
        short_cond = is_sb_window and self.dn_count >= self.count_needed and ((not self.use_ema) or self.close < ema200)
        st = self.strategy
        if long_cond and st.position_size == 0:
            st.entry("SB-Long", st.long, comment="SB Long")
        if short_cond and st.position_size == 0:
            st.entry("SB-Short", st.short, comment="SB Short")
        if st.position_size > 0:
            long_sl = st.position_avg_price * (1 - self.sl_percent / 100)
            long_tp = st.position_avg_price * (1 + self.tp_percent / 100)
            st.exit("Exit Long", "SB-Long", stop=long_sl, limit=long_tp, comment_loss="SL %", comment_profit="TP %")
        if st.position_size < 0:
            short_sl = st.position_avg_price * (1 + self.sl_percent / 100)
            short_tp = st.position_avg_price * (1 - self.tp_percent / 100)
            st.exit("Exit Short", "SB-Short", stop=short_sl, limit=short_tp, comment_loss="SL %", comment_profit="TP %")
        if (not is_sb_window) and st.position_size != 0:
            st.close_all(comment="End of Window")
        self.plot(ema200 if self.use_ema else NA, "Trend Filter (200 EMA)", color=color.yellow)
