"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SENSEX Disciplined Sniper V4
Author       : parekh_maulik0203
Source URL   : https://www.tradingview.com/script/lhrEFuTq-Maa-Ambe
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In the 09:20-12:00 and 13:30-14:30 windows (exchange time), when flat and fewer than 4 trades
were taken in the trading day, a close above EMA200 with RSI > 60, ADX(14) > 20 and volume above its SMA20 buys; the
mirror (close under EMA200, RSI < 40) sells short. The entry and its +/- 80-point bracket around the signal close are
issued together on the signal bar (so the bracket also works on the fill bar). The daily counter resets on the first bar
of each trading day (ta.change(time("D"))).

Deviations from the original: none.
Not carried over: the EMA plot, background and the order comment texts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class SensexSniper(Script):
    TITLE = "SENSEX Disciplined Sniper V4"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "lhrEFuTq", "author": "parekh_maulik0203", "licence": "not stated",
              "url": "https://www.tradingview.com/script/lhrEFuTq-Maa-Ambe"}

    def init(self):
        self.num_lots = self.input.int(5, "Number of Lots")
        self.max_daily = self.input.int(4, "Max Daily Trades")
        self.units_per_lot = 20
        self.total_units = self.num_lots * self.units_per_lot
        self.target_points = 80
        self.stop_points = 80
        self.trades_today = 0

    def on_bar(self):
        if ta.change(self.time_fn("D")):
            self.trades_today = 0
        session1 = self.time_fn(None, "0920-1200")
        session2 = self.time_fn(None, "1330-1430")
        is_trade_window = (not na(session1)) or (not na(session2))
        di_plus, di_minus, adx = ta.dmi(14, 14)
        is_trending = adx > 20
        vol_ma = ta.sma(self.volume, 20)
        is_high_vol = self.volume > vol_ma
        st = self.strategy
        can_trade = is_trade_window and self.trades_today < self.max_daily and st.position_size == 0
        ema200 = ta.ema(self.close, 200)
        rsi_val = ta.rsi(self.close, 14)
        buy_ce = can_trade and self.close > ema200 and rsi_val > 60 and is_trending and is_high_vol
        buy_pe = can_trade and self.close < ema200 and rsi_val < 40 and is_trending and is_high_vol
        if buy_ce:
            entry_p = float(self.close)
            st.entry("CE", st.long, qty=self.total_units)
            self.trades_today = self.trades_today + 1
            st.exit("Exit CE", "CE", limit=entry_p + self.target_points, stop=entry_p - self.stop_points)
        if buy_pe:
            entry_p = float(self.close)
            st.entry("PE", st.short, qty=self.total_units)
            self.trades_today = self.trades_today + 1
            st.exit("Exit PE", "PE", limit=entry_p - self.target_points, stop=entry_p + self.stop_points)
        self.plot(ema200, color=color.yellow, title="EMA 200")
