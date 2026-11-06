"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [3Commas] BCH Heikin Ashi RSI Fade — Short Strategy
Author       : 3Commas
Source URL   : https://www.tradingview.com/script/nuqVC5F7-3Commas-BCH-Heikin-Ashi-RSI-Fade-Short-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation of a 3Commas bot template (orders processed at the bar close, process_orders_on_close). A short base order (market, or a limit at the close) opens when a higher-timeframe RSI is above (below) its level and the Heikin Ashi candles of the HA timeframe
have run for at least N bars in one direction (request.security, lookahead off); one position only, closed by a take-profit limit and a stop-loss stop around the average entry price, issued while the trade is open.
Deviations from the original: ticker.heikinashi(syminfo.tickerid) is emulated: the Heikin Ashi candles are built from the requested bars with the standard formula (close = ohlc4, open = average of the previous HA open and close, the first open = (open + close) / 2) inside each request.security call.
Not carried over: fill labels, plots, status table, watermark and the webhook alert text (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


def make_ha_streak(bull):
    """ta.barssince(close <= open) (bull) / ta.barssince(close >= open) (bear) on the Heikin Ashi candles of the requested bars."""
    state = dict(o=None, c=None)

    def streak(v):
        o, h, l, c = float(v.open), float(v.high), float(v.low), float(v.close)
        ha_close = (o + h + l + c) / 4
        ha_open = (o + c) / 2 if state["o"] is None else (state["o"] + state["c"]) / 2
        state["o"], state["c"] = ha_open, ha_close
        if bull:
            return ta.barssince(ha_close <= ha_open)
        return ta.barssince(ha_close >= ha_open)
    return streak


FROM_DATE = 1763510400000     # timestamp("19 Nov 2025 00:00 +0000")
TO_DATE = 1780531140000       # timestamp("03 Jun 2026 23:59 +0000")


class HeikinAshiRsiFadeShortBch(Script):
    TITLE = "[3Commas] BCH Heikin Ashi RSI Fade — Short Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=280, pyramiding=1, commission_type="percent",
                    commission_value=0.055, slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "nuqVC5F7", "author": "3Commas", "licence": "not stated", "url": "https://www.tradingview.com/script/nuqVC5F7-3Commas-BCH-Heikin-Ashi-RSI-Fade-Short-Strategy"}

    def init(self):
        i = self.input
        g = "Base Order"
        self.base_order_size = i.float(280.0, "Base Order Size (USDT)", minval=1, group=g)
        self.use_limit_base = i.bool(False, "Use LIMIT for Base (else Market)", group=g)
        g = "RSI Filter"
        self.rsi_tf = i.timeframe("15", "RSI Timeframe", group=g)
        self.rsi_len = i.int(100, "RSI Length", minval=2, group=g)
        self.rsi_condition = i.string("Greater Than", "RSI Condition", options=["Greater Than", "Less Than"], group=g)
        self.rsi_level = i.float(46.0, "RSI Level", minval=1, maxval=100, group=g)
        g = "Heikin Ashi Filter"
        self.ha_tf = i.timeframe("15", "HA Timeframe", group=g)
        self.ha_streak = i.int(7, "Consecutive Candles", minval=2, maxval=30, group=g)
        self.ha_direction = i.string("Bullish", "HA Streak Direction", options=["Bullish", "Bearish"], group=g)
        g = "Exit"
        self.tp_pct = i.float(2.1, "Take Profit (%)", minval=0.1, step=0.1, group=g)
        self.sl_pct = i.float(2.5, "Stop Loss (%)", minval=0.1, step=0.1, group=g)
        g = "Backtest Window"
        self.use_date_filter = i.bool(True, "Limit Backtest Period", group=g)
        self.from_date = i.time(FROM_DATE, "From", group=g)
        self.to_date = i.time(TO_DATE, "To", group=g)
        self.ha_bull = make_ha_streak(True)
        self.ha_bear = make_ha_streak(False)

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_window = (not self.use_date_filter) or (self.time >= self.from_date and self.time <= self.to_date)
        rsi_ltf = self.security(None, self.rsi_tf, lambda v: ta.rsi(v.close, self.rsi_len), lookahead=False)
        ha_bull_count = self.security(None, self.ha_tf, self.ha_bull, lookahead=False)
        ha_bear_count = self.security(None, self.ha_tf, self.ha_bear, lookahead=False)
        cond_rsi = rsi_ltf > self.rsi_level if self.rsi_condition == "Greater Than" else rsi_ltf < self.rsi_level
        ha_count = ha_bull_count if self.ha_direction == "Bullish" else ha_bear_count
        cond_ha = ha_count >= self.ha_streak
        entry_signal = bool(cond_rsi and cond_ha)
        in_position = st.position_size != 0
        open_entry = in_window and (not in_position) and st.opentrades == 0 and entry_signal
        if open_entry:
            qty = div(self.base_order_size, close)
            if self.use_limit_base:
                st.entry("Short_Base", st.short, qty=qty, limit=close, comment="Short_Base")
            else:
                st.entry("Short_Base", st.short, qty=qty, comment="Short_Base")
        if in_position:
            avg_px = st.position_avg_price
            tp_px = avg_px * (1.0 - self.tp_pct / 100.0)
            sl_px = avg_px * (1.0 + self.sl_pct / 100.0)
            st.exit("Exit", from_entry="Short_Base", limit=tp_px, stop=sl_px, comment_profit="TP", comment_loss="SL")
