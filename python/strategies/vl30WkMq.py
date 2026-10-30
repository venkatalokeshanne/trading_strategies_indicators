"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ADR AsianLS
Author       : adcarcamo
Source URL   : https://www.tradingview.com/script/vl30WkMq
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The Asian session (19:00 - 24:00 at GMT-3) high / low is tracked from the session's first bar. After the session, inside the operating window (00:00 - 12:00 GMT-3) and while no trade was taken in this cycle, a strong-bodied candle (body at least the threshold % of its range) that closes above the session high (up candle)
buys, or closes below the session low (down candle) sells. Each entry issues two exit orders of one contract each: a take-profit at +10 points with a stop 10 points inside the session extreme, and a runner with the same stop and a trailing stop (activation 10 ticks, offset 5 ticks).
Deviations from the original: none.
Not carried over: the session box and the entry / stop / target labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath


class AdrAsianLs(Script):
    TITLE = "ADR AsianLS"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=2100, default_qty_type="fixed", default_qty_value=2)
    SOURCE = {"id": "vl30WkMq", "author": "adcarcamo", "licence": "not stated", "url": "https://www.tradingview.com/script/vl30WkMq"}

    def init(self):
        i = self.input
        self.asia_session = i.session("1900-0000", "Horario Sesión Asia (Chile GMT-3)")
        self.trade_window = i.session("0000-1200", "Ventana Operativa Post-Asia")
        self.body_threshold = i.float(65.0, "% Mínimo de Cuerpo (Sugerido)")
        self.sl_offset = 10.0
        self.tp1_pips = 10.0
        self.session_high = NA
        self.session_low = NA
        self.trades_today = 0
        self.prev_in_session = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        in_session = self.time_in_session(self.asia_session, "GMT-3")
        new_asia = in_session and not self.prev_in_session
        self.prev_in_session = bool(in_session)
        if new_asia:
            self.session_high = float(high)
            self.session_low = float(low)
            self.trades_today = 0
        elif in_session:
            self.session_high = pmath.max(self.session_high, high)
            self.session_low = pmath.min(self.session_low, low)
        rango_vela = high - low
        cuerpo_vela = abs(close - open_)
        es_vela_cuerpo = div(cuerpo_vela, rango_vela if rango_vela > 0 else 1) * 100 >= self.body_threshold
        can_trade = (not in_session) and self.time_in_session(self.trade_window, "GMT-3") and self.trades_today < 1
        long_cond = can_trade and close > self.session_high and open_ < close and es_vela_cuerpo
        short_cond = can_trade and close < self.session_low and open_ > close and es_vela_cuerpo
        if long_cond:
            self.trades_today = 1
            entry_price = close
            sl_price = self.session_high - self.sl_offset
            v_tp1 = entry_price + self.tp1_pips
            st.entry("Buy", st.long, comment="Entry: " + str(pmath.round(entry_price, 2)))
            st.exit("TP1-Buy", "Buy", qty=1, limit=v_tp1, stop=sl_price, comment="TP1 1k")
            st.exit("TP2-Trail-Buy", "Buy", qty=1, stop=sl_price, trail_points=self.tp1_pips, trail_offset=self.tp1_pips / 2, comment="Trailing")
        if short_cond:
            self.trades_today = 1
            entry_price = close
            sl_price = self.session_low + self.sl_offset
            v_tp1 = entry_price - self.tp1_pips
            st.entry("Sell", st.short, comment="Entry: " + str(pmath.round(entry_price, 2)))
            st.exit("TP1-Sell", "Sell", qty=1, limit=v_tp1, stop=sl_price, comment="TP1 1k")
            st.exit("TP2-Trail-Sell", "Sell", qty=1, stop=sl_price, trail_points=self.tp1_pips, trail_offset=self.tp1_pips / 2, comment="Trailing")
