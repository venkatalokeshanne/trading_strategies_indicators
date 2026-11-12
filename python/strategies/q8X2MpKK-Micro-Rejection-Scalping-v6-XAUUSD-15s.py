"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Micro Rejection Scalping v6 - XAUUSD 15s
Author       : Keralatraderpro
Source URL   : https://www.tradingview.com/script/q8X2MpKK-Micro-Rejection-Scalping-v6-XAUUSD-15s
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of the trading logic. The EMA9 crossing under the EMA21 inside the New York 07:00-11:00 session, after a bar cooldown and while flat, goes short with a stop an ATR
multiple above the bar high and a limit at least the stop distance (or the profit multiple of ATR) below the close, both placed with the entry. The pivot support / resistance line arrays in the original only
feed the drawings and are not carried over.

Deviations from the original: none for trading.
Not carried over: the pivot S/R lines and their arrays, the stop / target lines, the entry shape and the session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, pmath, ta


class MicroRejectionScalping(Script):
    TITLE = "Micro Rejection Scalping v6 - XAUUSD 15s"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0)
    SOURCE = {"id": "q8X2MpKK", "author": "Keralatraderpro", "licence": "not stated",
              "url": "https://www.tradingview.com/script/q8X2MpKK-Micro-Rejection-Scalping-v6-XAUUSD-15s"}

    def init(self):
        g = "Trend"
        self.ema_fast_len = self.input.int(9, "Fast EMA Length", group=g)
        self.ema_slow_len = self.input.int(21, "Slow EMA Length", group=g)
        g = "Exit"
        self.sl_atr_mult = self.input.float(0.8, "Stop Loss (x ATR)", minval=0.1, step=0.1, group=g)
        self.profit_mult = self.input.float(2.0, "Take Profit (x ATR)", minval=0.5, step=0.1, group=g)
        g = "Filters"
        self.cooldown_bars = self.input.int(12, "Cooldown Between Trades (bars)", minval=1, maxval=50, group=g)
        self.use_session = self.input.bool(True, "Use Session Filter (New York ET)", group=g)
        self.ses_start = self.input.int(7, "Session Start Hour (ET)", minval=0, maxval=23, group=g)
        self.ses_end = self.input.int(11, "Session End Hour (ET)", minval=0, maxval=23, group=g)
        self.last_trade_bar = 0

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        atr14 = ta.atr(14)
        safe_atr = 1.0 if na(atr14) else atr14
        h_et = self.hour(self.time, "America/New_York")
        in_session = h_et >= self.ses_start and h_et < self.ses_end
        session_ok = (not self.use_session) or in_session
        cool_ok = (self.bar_index - self.last_trade_bar) >= self.cooldown_bars
        cross = ta.crossunder(ema_fast, ema_slow)
        st = self.strategy
        sell_signal = cross and session_ok and cool_ok and st.position_size == 0
        sell_sl = self.high + safe_atr * self.sl_atr_mult
        sell_sl_dist = pmath.max(sell_sl - self.close, safe_atr * 0.1)
        sell_lmt = self.close - pmath.max(safe_atr * self.profit_mult, sell_sl_dist)
        if sell_signal:
            self.last_trade_bar = self.bar_index
            st.entry("Short", st.short)
            st.exit("SX", from_entry="Short", stop=sell_sl, limit=sell_lmt)
        self.plot(ema_fast, "EMA Fast", color=color.orange)
        self.plot(ema_slow, "EMA Slow", color=color.yellow, linewidth=2)
