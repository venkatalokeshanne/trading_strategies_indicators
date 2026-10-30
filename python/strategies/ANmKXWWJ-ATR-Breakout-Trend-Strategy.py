"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ATR Breakout Trend Strategy
Author       : Harshal_choudhari
Source URL   : https://www.tradingview.com/script/ANmKXWWJ-ATR-Breakout-Trend-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close crossing the previous N bars' high (low) with the close on the right side of the SMA200 enters at the close (reversing an opposite position), risk-sized by an ATR stop that is
placed with the entry; while in a position the stop is re-issued every bar (optionally trailing with the bar's high / low minus an ATR multiple) and a close beyond the previous exit channel closes the trade at the close.

Deviations from the original: none.
Not carried over: the projected reward / risk boxes, the SMA and stop line plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class AtrBreakoutTrend(Script):
    TITLE = "ATR Breakout Trend Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.06, slippage=2,
                    process_orders_on_close=True)
    SOURCE = {"id": "ANmKXWWJ", "author": "Harshal_choudhari", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ANmKXWWJ-ATR-Breakout-Trend-Strategy"}

    def init(self):
        g = "Breakout Channels"
        self.entry_length = self.input.int(20, "Entry channel length", minval=1, group=g)
        self.exit_length = self.input.int(20, "Exit channel length", minval=1, group=g)
        self.trend_length = self.input.int(200, "Trend SMA length", minval=1, group=g)
        self.allow_shorts = self.input.bool(True, "Enable short trades", group=g)
        g = "Risk Management"
        self.atr_length = self.input.int(20, "ATR length", minval=1, group=g)
        self.stop_atr_multiple = self.input.float(2.0, "Initial stop (ATR multiple)", minval=0.1, step=0.1, group=g)
        self.risk_percent = self.input.float(1.0, "Equity risk per trade (%)", minval=0.1, maxval=10.0, step=0.1, group=g)
        self.max_exposure_percent = self.input.float(100.0, "Maximum exposure (% of equity)", minval=1.0, maxval=1000.0, step=1.0, group=g)
        self.trailing_stop_enabled = self.input.bool(False, "Enable ATR trailing stop", group=g)
        self.trailing_stop_atr = self.input.float(2.0, "Trailing stop distance (ATR)", minval=0.1, step=0.1, group=g)
        self.long_stop_price = NA
        self.short_stop_price = NA

    def on_bar(self):
        eh = self.H("eh")
        el = self.H("el")
        xh = self.H("xh")
        xl = self.H("xl")
        entry_high, entry_low, exit_high, exit_low = eh[1], el[1], xh[1], xl[1]
        eh.set(ta.highest(self.high, self.entry_length))
        el.set(ta.lowest(self.low, self.entry_length))
        xh.set(ta.highest(self.high, self.exit_length))
        xl.set(ta.lowest(self.low, self.exit_length))
        atr_value = ta.sma(ta.tr(True), self.atr_length)
        trend_sma = ta.sma(self.close, self.trend_length)
        stop_distance = atr_value * self.stop_atr_multiple
        st = self.strategy
        risk_cash = st.equity * self.risk_percent / 100.0
        point_value = 1.0 if (na(self.syminfo.pointvalue) or self.syminfo.pointvalue <= 0) else self.syminfo.pointvalue
        risk_per_unit = stop_distance * point_value
        exposure_per_unit = self.close * point_value
        qty_by_risk = div(risk_cash, risk_per_unit) if risk_per_unit > 0 else NA
        qty_by_exposure = div(st.equity * self.max_exposure_percent / 100.0, exposure_per_unit) if exposure_per_unit > 0 else NA
        order_qty = pmath.min(qty_by_risk, qty_by_exposure) if (not na(qty_by_risk) and not na(qty_by_exposure)) else NA
        crossed_up = ta.crossover(self.close, entry_high)
        crossed_down = ta.crossunder(self.close, entry_low)
        long_breakout = self.barstate.isconfirmed and crossed_up and self.close > trend_sma
        short_breakout = self.barstate.isconfirmed and crossed_down and self.close < trend_sma
        if long_breakout and st.position_size <= 0 and not na(order_qty) and order_qty > 0:
            self.long_stop_price = self.close - stop_distance
            self.short_stop_price = NA
            st.entry("Long", st.long, qty=order_qty)
            st.exit("L Exit", from_entry="Long", stop=self.long_stop_price)
        if self.allow_shorts and short_breakout and st.position_size >= 0 and not na(order_qty) and order_qty > 0:
            self.short_stop_price = self.close + stop_distance
            self.long_stop_price = NA
            st.entry("Short", st.short, qty=order_qty)
            st.exit("S Exit", from_entry="Short", stop=self.short_stop_price)
        if st.position_size > 0 and not na(self.long_stop_price):
            if self.trailing_stop_enabled:
                self.long_stop_price = pmath.max(self.long_stop_price, self.high - atr_value * self.trailing_stop_atr)
            if self.close < exit_low:
                st.close("Long", comment="Channel exit")
            else:
                st.exit("L Exit", from_entry="Long", stop=self.long_stop_price)
        if st.position_size < 0 and not na(self.short_stop_price):
            if self.trailing_stop_enabled:
                self.short_stop_price = pmath.min(self.short_stop_price, self.low + atr_value * self.trailing_stop_atr)
            if self.close > exit_high:
                st.close("Short", comment="Channel exit")
            else:
                st.exit("S Exit", from_entry="Short", stop=self.short_stop_price)
        self.plot(trend_sma, "Trend SMA", color=color.blue, linewidth=2)
