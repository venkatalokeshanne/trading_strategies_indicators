"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MNQ Prop Firm Execution System (Final)
Author       : not stated
Source URL   : https://www.tradingview.com/script/qmvY3luY
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Swing highs / lows are 3-bar pivots; a liquidity sweep is a bar whose low (high) breaks the last swing low (high) and closes back inside; it must agree with the 200 EMA side, fall in the 13:00-16:00 session and pass the daily risk engine (fewer than 3 trades counted today and today's equity change above -300). The size is 1 contract, 2 once today's equity change exceeds +150.
A signal enters at the next open and issues two exit orders at once: half the position at a 1 : 1 target and the rest at a 1.8 : 1 target with the swing level as stop. The daily counter is incremented on every signal, also when pyramiding 0 makes the entry itself a no-op (as the source does); a repeated signal in an open position moves the existing exit levels.
Deviations from the original: none.
Not carried over: the three plots.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class IrvineMomentum(Script):
    TITLE = "MNQ Prop Firm Execution System (Final)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "qmvY3luY", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/qmvY3luY"}

    def init(self):
        self.swing_high = NA
        self.swing_low = NA
        self.equity_start = NA
        self.trades = 0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        ph = ta.pivothigh(high, 3, 3)
        pl = ta.pivotlow(low, 3, 3)
        if not na(ph):
            self.swing_high = float(ph)
        if not na(pl):
            self.swing_low = float(pl)
        sh, sl_ = float(self.swing_high), float(self.swing_low)
        sweep_low = (not na(sl_)) and low < sl_ and close > sl_
        sweep_high = (not na(sh)) and high > sh and close < sh
        ema = ta.ema(close, 200)
        trend_up = close > ema
        trend_down = close < ema
        in_session = self.time_in_session("1300-1600")
        if self.bar_index == 0:
            self.equity_start = float(st.equity)
        day_chg = ta.change(self.time_fn("D"))
        if (not na(day_chg)) and day_chg != 0:
            self.equity_start = float(st.equity)
            self.trades = 0
        daily_pnl = st.equity - self.equity_start
        can_trade = self.trades < 3 and daily_pnl > -300
        long_signal = in_session and can_trade and sweep_low and trend_up
        short_signal = in_session and can_trade and sweep_high and trend_down
        qty = 1 * (2 if daily_pnl > 150 else 1)
        if long_signal:
            sl = sl_
            tp1 = close + (close - sl) * 1.0
            tp2 = close + (close - sl) * 1.8
            st.entry("BUY", st.long, qty=qty)
            st.exit("BUY TP1", "BUY", limit=tp1, qty_percent=50)
            st.exit("BUY TP2", "BUY", limit=tp2, stop=sl)
            self.trades += 1
        if short_signal:
            sl = sh
            tp1 = close - (sl - close) * 1.0
            tp2 = close - (sl - close) * 1.8
            st.entry("SELL", st.short, qty=qty)
            st.exit("SELL TP1", "SELL", limit=tp1, qty_percent=50)
            st.exit("SELL TP2", "SELL", limit=tp2, stop=sl)
            self.trades += 1
