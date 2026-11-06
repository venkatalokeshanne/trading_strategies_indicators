"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD Quant SMC (D1-4H-15M-5M)  (short title XAU_XAG_5min)
Author       : not stated
Source URL   : https://www.tradingview.com/script/qWRZMcV0
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The daily and 4-hour closes vs their EMA(50) must agree (up / down); on 15-minute data a break of structure (the 15-minute close crossing over the previous 10-bar high in an up-trend, under the previous 10-bar low in a down-trend) records the impulse range, reset every new weekday. When the chart low crosses under (high crosses over) the 0.618 retracement of that range, inside 07-13 exchange hours, with the daily (-1 %), weekly (-3 %, +3 % target) loss limits respected and no trade yet today, a trade is entered sized to risk 1 % of equity to the impulse origin, with the origin as stop and the range extended by half as target.
The scripts qWRZMcV0 (5-minute) and yid8vrVZ (10-minute) differ only in the short title.
Deviations from the original: none.
Not carried over: plots, shading and shapes.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class XauQuantSmc(Script):
    TITLE = "XAUUSD Quant SMC (D1-4H-15M-5M)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash")
    SOURCE = {"id": "qWRZMcV0", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/qWRZMcV0"}

    def init(self):
        i = self.input
        g = "Análisis Multi-Timeframe"
        self.tf_d = i.timeframe("D", "Tendencia Diaria", group=g)
        self.tf_4h = i.timeframe("240", "Tendencia 4H", group=g)
        self.tf_15m = i.timeframe("15", "Estructura BOS (15M)", group=g)
        g = "Sesión de Trading (GMT+1)"
        self.sess_start = i.int(7, "Hora Inicio", minval=0, maxval=23, group=g)
        self.sess_end = i.int(13, "Hora Fin", minval=0, maxval=23, group=g)
        self.bos_occurred = False
        self.fib_high = NA
        self.fib_low = NA
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trades_today = 0

    def _trend(self, tf):
        ema50 = self.security(None, tf, lambda v: ta.ema(v.close, 50))
        c = self.security(None, tf, lambda v: float(v.close))
        return 1 if c > ema50 else -1

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_dow, h_h15, h_cl = self.H("dow"), self.H("h15"), self.H("closed")
        dow_1, h15_1, closed_1 = h_dow[1], h_h15[1], h_cl[1]
        trend_d = self._trend(self.tf_d)
        trend_4h = self._trend(self.tf_4h)
        trend_aligned = (trend_d == 1 and trend_4h == 1) or (trend_d == -1 and trend_4h == -1)
        is_bullish = trend_d == 1 and trend_4h == 1
        high_15m = self.security(None, self.tf_15m, lambda v: ta.highest(v.high, 10))
        low_15m = self.security(None, self.tf_15m, lambda v: ta.lowest(v.low, 10))
        close_15m = self.security(None, self.tf_15m, lambda v: float(v.close))
        # low_15m[1] is the chart-bar previous value of the requested low
        h_l15 = self.H("l15")
        l15_1 = h_l15[1]
        dow = self.dayofweek()
        dow_change = (not na(dow_1)) and dow != dow_1
        if dow_change:
            self.bos_occurred = False
        cross_up = ta.crossover(close_15m, h15_1)
        cross_dn = ta.crossunder(close_15m, l15_1)
        if is_bullish and cross_up:
            self.bos_occurred = True
            self.fib_high = high_15m
            self.fib_low = low_15m
        elif (not is_bullish) and cross_dn:
            self.bos_occurred = True
            self.fib_high = high_15m
            self.fib_low = low_15m
        fib_618 = self.fib_high - (self.fib_high - self.fib_low) * 0.618 if is_bullish else self.fib_low + (self.fib_high - self.fib_low) * 0.618
        if dow_change:
            self.daily_pnl = 0.0
            self.trades_today = 0
        week_chg = ta.change(self.time_fn("W"))
        if (not na(week_chg)) and week_chg != 0:
            self.weekly_pnl = 0.0
        closed = st.closedtrades
        if (not na(closed_1)) and closed > closed_1:
            last_pnl = div(st.closedtrades_profit(closed - 1), st.initial_capital) * 100
            self.daily_pnl += last_pnl
            self.weekly_pnl += last_pnl
        can_trade = self.daily_pnl > -1.0 and self.weekly_pnl > -3.0 and self.weekly_pnl < 3.0 and self.trades_today < 1
        hour = self.hour()
        in_session = hour >= self.sess_start and hour < self.sess_end
        cu_low = ta.crossunder(low, fib_618)
        co_high = ta.crossover(high, fib_618)
        long_condition = trend_aligned and is_bullish and self.bos_occurred and cu_low and in_session and can_trade
        short_condition = trend_aligned and (not is_bullish) and self.bos_occurred and co_high and in_session and can_trade
        risk_amount = st.equity * (1.0 / 100)
        if long_condition:
            sl = self.fib_low
            tp = self.fib_high + (self.fib_high - self.fib_low) * 0.5
            qty = div(risk_amount, abs(close - sl))
            st.entry("Long", st.long, qty=qty)
            st.exit("Exit Long", "Long", stop=sl, limit=tp)
            self.bos_occurred = False
            self.trades_today = 1
        if short_condition:
            sl = self.fib_high
            tp = self.fib_low - (self.fib_high - self.fib_low) * 0.5
            qty = div(risk_amount, abs(close - sl))
            st.entry("Short", st.short, qty=qty)
            st.exit("Exit Short", "Short", stop=sl, limit=tp)
            self.bos_occurred = False
            self.trades_today = 1
        h_dow.set(dow)
        h_h15.set(high_15m)
        h_l15.set(low_15m)
        h_cl.set(closed)
