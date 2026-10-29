"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MNQ 15m NY Open ORB Strategy
Author       : Nils123456
Source URL   : https://www.tradingview.com/script/0h0KTxCq-MNQ-15m-NY-Open-ORB-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The first 15 minutes (09:30-09:45 in the chosen timezone) define the opening range, which locks on the first bar after it.
From 09:45 to 16:00 a close beyond the range enters once per day when flat, together with a tick-based profit / loss / trailing exit; any position is closed on the first bar after the
trade session. The "new day" test uses the symbol's exchange day (America/New_York for the default), the same as the default timezone input.

Deviations from the original: the day-change test follows the exchange timezone, not a changed timezone input.
Not carried over: the Tradovate alert JSON strings, ORB plots, shading and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class MnqOrb(Script):
    TITLE = "MNQ 15m NY Open ORB Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=25000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=1.20,
                    slippage=2, pyramiding=0, process_orders_on_close=True, margin_long=1, margin_short=1)
    SOURCE = {"id": "0h0KTxCq", "author": "Nils123456", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0h0KTxCq-MNQ-15m-NY-Open-ORB-Strategy"}

    def init(self):
        self.tz = self.input.string("America/New_York", "Zeitzone")
        self.orb_session = self.input.session("0930-0945", "ORB Session")
        self.trade_session = self.input.session("0945-1600", "Trade Session")
        self.use_close_break = self.input.bool(True, "Breakout nur per Kerzenschluss")
        self.one_trade_per_day = self.input.bool(True, "Max. 1 Trade pro Tag")
        self.allow_long = self.input.bool(True, "Long erlauben")
        self.allow_short = self.input.bool(True, "Short erlauben")
        self.close_eod = self.input.bool(True, "Position zum Session-Ende schliessen")
        self.fixed_contracts = self.input.int(8, "Feste Kontraktanzahl", minval=1)
        self.points_per_price_point = self.input.float(10.0, "Umrechnung: 10 Punkte = 1 Preis-Punkt", minval=1.0)
        self.take_profit_pts = self.input.float(200.0, "Take Profit in Punkten", minval=1.0)
        self.stop_loss_pts = self.input.float(200.0, "Stop Loss in Punkten", minval=1.0)
        self.trail_stop_pts = self.input.float(10.0, "Trailing Stop Loss in Punkten", minval=1.0)
        self.trail_activation_pts = self.input.float(15.0, "Profit vor Trailing-Aktivierung", minval=1.0)
        self.orb_high = NA
        self.orb_low = NA
        self.orb_locked = False
        self.traded_today = False

    def on_bar(self):
        mintick = self.syminfo.mintick
        take_profit_ticks = int(pmath.max(1, pmath.round(div(div(self.take_profit_pts, self.points_per_price_point), mintick))))
        stop_loss_ticks = int(pmath.max(1, pmath.round(div(div(self.stop_loss_pts, self.points_per_price_point), mintick))))
        trail_stop_ticks = int(pmath.max(1, pmath.round(div(div(self.trail_stop_pts, self.points_per_price_point), mintick))))
        trail_activation_ticks = int(pmath.max(1, pmath.round(div(div(self.trail_activation_pts, self.points_per_price_point), mintick))))
        in_orb = not na(self.time_fn(None, self.orb_session, self.tz))
        in_trade_session = not na(self.time_fn(None, self.trade_session, self.tz))
        in_orb_prev = self.H("in_orb")[1]
        in_trade_prev = self.H("in_trade")[1]
        self.H("in_orb").set(in_orb)
        self.H("in_trade").set(in_trade_session)
        new_ny_day = ta.change(self.time_fn("D")) != 0
        if new_ny_day:
            self.orb_high = NA
            self.orb_low = NA
            self.orb_locked = False
            self.traded_today = False
        if in_orb:
            self.orb_high = float(self.high) if na(self.orb_high) else pmath.max(self.orb_high, self.high)
            self.orb_low = float(self.low) if na(self.orb_low) else pmath.min(self.orb_low, self.low)
        if (not in_orb) and in_orb_prev and not na(self.orb_high) and not na(self.orb_low):
            self.orb_locked = True
        st = self.strategy
        can_trade = self.barstate.isconfirmed and self.orb_locked and in_trade_session and st.position_size == 0 and ((not self.one_trade_per_day) or not self.traded_today)
        long_break = self.close > self.orb_high if self.use_close_break else self.high > self.orb_high
        short_break = self.close < self.orb_low if self.use_close_break else self.low < self.orb_low
        if can_trade and self.allow_long and long_break:
            st.entry("ORB Long", st.long, qty=self.fixed_contracts)
            st.exit("L Exit", "ORB Long", profit=take_profit_ticks, loss=stop_loss_ticks, trail_points=trail_activation_ticks, trail_offset=trail_stop_ticks)
            self.traded_today = True
        elif can_trade and self.allow_short and short_break:
            st.entry("ORB Short", st.short, qty=self.fixed_contracts)
            st.exit("S Exit", "ORB Short", profit=take_profit_ticks, loss=stop_loss_ticks, trail_points=trail_activation_ticks, trail_offset=trail_stop_ticks)
            self.traded_today = True
        if self.close_eod and (not in_trade_session) and in_trade_prev:
            st.close_all("NY Session Close")
        self.plot(self.orb_high, "ORB High", color=color.lime, linewidth=2)
        self.plot(self.orb_low, "ORB Low", color=color.red, linewidth=2)
