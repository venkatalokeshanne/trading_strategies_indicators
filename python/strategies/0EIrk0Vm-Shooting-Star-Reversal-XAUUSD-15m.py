"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Shooting Star Reversal [XAUUSD 15m]
Author       : SAVIOR_HERO
Source URL   : https://www.tradingview.com/script/0EIrk0Vm-Shooting-Star-Reversal-XAUUSD-15m
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A candle with a large upper wick (>= wick ratio x body), a small lower wick, a body of at least the minimum size, after a rise over the lookback, opens a short at the next open while flat;
the stop sits above the candle high by a body multiple and the take-profit below the signal close by a body multiple; both are placed with the entry.

Deviations from the original: none.
Not carried over: the SL / TP / entry lines, labels, signal background, info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, pmath


class ShootingStarReversal(Script):
    TITLE = "Shooting Star Reversal [XAUUSD 15m]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="cash_per_order", commission_value=0.5, slippage=2)
    SOURCE = {"id": "0EIrk0Vm", "author": "SAVIOR_HERO", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0EIrk0Vm-Shooting-Star-Reversal-XAUUSD-15m"}

    def init(self):
        g = "Shooting Star Settings"
        self.wick_multiplier = self.input.float(3.0, "Min Wick-to-Body Ratio", minval=1.5, maxval=10.0, step=0.5, group=g)
        self.max_lower_wick = self.input.float(1.0, "Max Lower Wick (× body)", minval=0.1, maxval=3.0, step=0.1, group=g)
        self.min_body_size = self.input.float(2.0, "Min Body Size ($)", minval=0.1, step=0.5, group=g)
        self.uptrend_bars = self.input.int(5, "Uptrend Lookback (bars)", minval=3, maxval=20, group=g)
        g = "Risk Management"
        self.sl_multiplier = self.input.float(0.5, "SL Buffer (× body above wick high)", minval=0.1, maxval=3.0, step=0.1, group=g)
        self.tp_multiplier = self.input.float(3.0, "TP (× body below entry)", minval=1.0, maxval=10.0, step=0.5, group=g)
        g = "Session Filter (NY Time)"
        self.use_session_filter = self.input.bool(False, "Only trade during session?", group=g)
        self.session_start = self.input.int(7, "Session Start Hour (server time)", minval=0, maxval=23, group=g)
        self.session_end = self.input.int(20, "Session End Hour (server time)", minval=0, maxval=23, group=g)

    def on_bar(self):
        st = self.strategy
        close, open_, high = self.close, self.open, self.high
        body_size = abs(close - open_)
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - self.low
        uptrend = close > close[self.uptrend_bars]
        cond_min_body = body_size >= self.min_body_size
        cond_upper_wick = upper_wick >= body_size * self.wick_multiplier
        cond_lower_wick = lower_wick < body_size * self.max_lower_wick
        in_session = self.hour() >= self.session_start and self.hour() < self.session_end
        cond_session = in_session if self.use_session_filter else True
        is_shooting_star = cond_min_body and cond_upper_wick and cond_lower_wick and uptrend and cond_session
        sl_price = high + (body_size * self.sl_multiplier)
        tp_price = close - (body_size * self.tp_multiplier)
        no_open_trade = st.position_size == 0
        if is_shooting_star and no_open_trade:
            st.entry("SS Short", st.short, comment="▼ SHORT")
            st.exit("SS Exit", from_entry="SS Short", stop=sl_price, limit=tp_price, comment_profit="✔ TP", comment_loss="✖ SL")
