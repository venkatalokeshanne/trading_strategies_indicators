"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : El Doble Double Bollinger [Artillery]
Author       : ArtilleryTrades
Source URL   : https://www.tradingview.com/script/IY9twKzM-El-Doble-Double-Bollinger-Artillery
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A touch of the outer Bollinger band within the last 1-10 bars followed by a candle that closes back past the fast (4-bar) Bollinger basis, with EMA55 trend and ADX
above its floor, inside the 02:00-09:00 New York window, enters when flat (max 3 a day). The stop and target (points) are fixed on the signal bar; a trade is closed after 20 bars.

Deviations from the original: none.
Not carried over: band / EMA plots, fills and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, na, ta


class ElDoble(Script):
    TITLE = "El Doble Double Bollinger [Artillery]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=5, margin_short=5, initial_capital=50000, default_qty_type="fixed", default_qty_value=1,
                    commission_type="cash_per_contract", commission_value=0.62, slippage=1)
    SOURCE = {"id": "IY9twKzM", "author": "ArtilleryTrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/IY9twKzM-El-Doble-Double-Bollinger-Artillery"}

    def init(self):
        g = "Bollinger Bands"
        self.bb_len = self.input.int(20, "BB Length", minval=5, group=g)
        self.bb_mult = self.input.float(2.0, "BB Multiplier", step=0.1, group=g)
        self.fast_bb_len = self.input.int(4, "Fast BB Length", minval=2, group=g)
        self.fast_bb_mult = self.input.float(2.0, "Fast BB Mult", step=0.1, group=g)
        g = "Trend Filter"
        self.ema_len = self.input.int(55, "EMA Length", minval=10, group=g)
        self.adx_len = self.input.int(14, "ADX Length", minval=5, group=g)
        self.adx_thresh = self.input.float(18.0, "ADX Min", step=1.0, group=g)
        g = "Exits"
        self.sl_pts = self.input.float(15.0, "Stop Loss Points", step=1.0, group=g)
        self.tp_pts = self.input.float(25.0, "Take Profit Points", step=1.0, group=g)
        self.time_stop = self.input.int(20, "Time Stop Bars", minval=5, group=g)
        g = "Trade Mgmt"
        self.max_trades = self.input.int(3, "Max Trades/Day", minval=1, group=g)
        self.cd_bars = self.input.int(1, "Cooldown Bars", minval=1, group=g)
        self.touch_age = self.input.int(10, "Max Touch Age", minval=3, group=g)
        g = "Session"
        self.sess_start = self.input.int(2, "Start Hour ET", minval=0, maxval=23, group=g)
        self.sess_end = self.input.int(9, "End Hour ET", minval=0, maxval=23, group=g)
        self.trades_today = 0
        self.entry_bar = NA

    def on_bar(self):
        bb_basis = ta.sma(self.close, self.bb_len)
        bb_dev = self.bb_mult * ta.stdev(self.close, self.bb_len)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        fast_basis = ta.sma(self.close, self.fast_bb_len)
        ema_h = S(ta.ema(self.close, self.ema_len))
        ema55 = ema_h[0]
        ema_slope = ema_h[0] - ema_h[5]
        di_plus, di_minus, adx_val = ta.dmi(self.adx_len, self.adx_len)
        et_hour = self.hour(self.time, "America/New_York")
        in_session = et_hour >= self.sess_start and et_hour < self.sess_end
        bull_touch = self.low <= bb_lower
        bear_touch = self.high >= bb_upper
        bs_since_bull = ta.barssince(bull_touch)
        bs_since_bear = ta.barssince(bear_touch)
        bull_setup = bs_since_bull >= self.cd_bars and bs_since_bull <= self.touch_age
        bear_setup = bs_since_bear >= self.cd_bars and bs_since_bear <= self.touch_age
        bull_rev = self.close > self.open and self.close > fast_basis
        bear_rev = self.close < self.open and self.close < fast_basis
        bull_trend = self.close > ema55 or ema_slope > 0
        bear_trend = self.close < ema55 or ema_slope < 0
        adx_ok = adx_val > self.adx_thresh
        change = ta.change(self.time_fn("D"))
        if (not na(change)) and change != 0:
            self.trades_today = 0
        st = self.strategy
        no_pos = st.position_size == 0
        can_trade = self.trades_today < self.max_trades and in_session and no_pos
        long_sig = can_trade and bull_setup and bull_rev and bull_trend and adx_ok
        short_sig = can_trade and bear_setup and bear_rev and bear_trend and adx_ok
        if long_sig:
            self.entry_bar = self.bar_index
            self.trades_today += 1
            st.entry("Long", st.long)
            st.exit("LX", "Long", stop=self.close - self.sl_pts, limit=self.close + self.tp_pts)
        if short_sig:
            self.entry_bar = self.bar_index
            self.trades_today += 1
            st.entry("Short", st.short)
            st.exit("SX", "Short", stop=self.close + self.sl_pts, limit=self.close - self.tp_pts)
        if st.position_size != 0 and not na(self.entry_bar):
            if self.bar_index - self.entry_bar >= self.time_stop:
                st.close_all("TS")
