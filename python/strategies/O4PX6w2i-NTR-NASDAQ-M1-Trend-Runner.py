"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NTR: NASDAQ M1 - Trend Runner
Author       : not stated
Source URL   : https://www.tradingview.com/script/O4PX6w2i
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A MACD(12, 26, 9) line-over-signal cross with both lines under 10, the close within 75 pips of the 200 SMA, the 50 SMA slope above its minimum, inside the 07:30-15:00 Mexico City session, with a one-bar re-entry lock after an exit and daily limits (fewer than 3 closed trades and fewer than 2 winners since the Mexico-City day started) enters while flat with 100 % of equity. The initial stop is the lowest low of 30 bars (previous bar's value) minus 2 pips (a fallback of 20 pips when that is not below the close); once the open profit reaches 100 pips a trailing stop 100 pips under the close, only ever moving up, replaces it. One exit order carries the stop.
Deviations from the original: none. A pip is ten ticks.
Not carried over: plots, shapes and diagnostic labels.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class NtrTrendRunner(Script):
    TITLE = "NTR: NASDAQ M1 - Trend Runner"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=10)
    SOURCE = {"id": "O4PX6w2i", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/O4PX6w2i"}

    def init(self):
        i = self.input
        self.fast_len = i.int(12, "MACD Fast Length", group="MACD")
        self.slow_len = i.int(26, "MACD Slow Length", group="MACD")
        self.signal_len = i.int(9, "MACD Signal Length", group="MACD")
        self.sma_len = i.int(200, "SMA 200", group="Filtro SMA")
        self.max_pips_distance = i.float(75.0, "Distancia Máxima Pips", group="Filtro SMA")
        self.ratio = i.float(5.0, "TP Ratio 1:X", group="Gestión")
        self.sl_periods = i.int(30, "Periodos Mínimo Técnico", group="Gestión")
        self.sl_extra_pips = i.float(2.0, "SL Extra debajo Mínimo", group="Gestión")
        self.trailing_stop_pips = i.float(100.0, "Distancia Trailing Stop", group="Trailing Stop")
        self.activate_trailing_pips = i.float(100.0, "Activar Trailing después de profit", group="Trailing Stop")
        self.session = i.session("0730-1500", "Horario Operativo", group="Horario")
        self.slope_periods = i.int(10, "Velas Pendiente SMA", group="Filtro SMA")
        self.min_slope = i.float(-2.5, "Pendiente mínima SMA50", group="Filtro SMA")
        self.last_exit_bar = 0
        self.trades_today = 0
        self.losses_today = 0
        self.wins_today = 0
        self.price_sl = NA
        self.trailing_sl = NA
        self.risk = NA
        self.stop_actual = NA

    def on_bar(self):
        st = self.strategy
        close, low = self.close, self.low
        h_pos, h_closed, h_sma50, h_low30, h_dom, h_trail = (self.H(n) for n in ("pos", "closed", "sma50", "low30", "dom", "trail"))
        pos_prev, closed_prev, sma50_slope_ref, low30_prev, dom_prev, trail_prev = h_pos[1], h_closed[1], h_sma50[self.slope_periods], h_low30[1], h_dom[1], h_trail[1]
        macd_line, signal_line, hist_line = ta.macd(close, self.fast_len, self.slow_len, self.signal_len)
        macd_below_zero = macd_line < 10 and signal_line < 10
        macd_cross_up = ta.crossover(macd_line, signal_line)
        sma200 = ta.sma(close, self.sma_len)
        sma50 = ta.sma(close, 50)
        pip_value = self.syminfo.mintick * 10
        distance_in_pips = div(abs(close - sma200), pip_value)
        slope = div(sma50 - sma50_slope_ref, self.slope_periods)
        entry_filter_ma = slope >= self.min_slope
        near_sma = distance_in_pips <= self.max_pips_distance
        low30 = ta.lowest(low, self.sl_periods)
        technical_min = low30_prev
        in_hours = self.time_in_session(self.session, "America/Mexico_City")
        pos = st.position_size
        position_change = nz(pos - pos_prev) if not na(pos_prev) else 0
        position_closed = position_change != 0 and pos == 0
        if position_closed:
            self.last_exit_bar = self.bar_index
        reentry_lock = self.bar_index > self.last_exit_bar
        t_day = self.time_fn("D", "0000-2359", "America/Mexico_City")
        dom = self.dayofmonth(t_day) if not na(t_day) else NA
        new_day = (not na(dom)) and (not na(dom_prev)) and dom != dom_prev
        if new_day:
            self.trades_today = 0
            self.losses_today = 0
            self.wins_today = 0
        closed = st.closedtrades
        if (not na(closed_prev)) and closed > closed_prev:
            self.trades_today += 1
            last_profit = st.closedtrades_profit(closed - 1)
            if last_profit < 0:
                self.losses_today += 1
            if last_profit > 0:
                self.wins_today += 1
        limit_trades = self.trades_today < 3
        limit_wins = self.wins_today < 2
        no_position = pos == 0
        potential = macd_cross_up and macd_below_zero and near_sma and reentry_lock and in_hours and entry_filter_ma
        buy_signal = potential and limit_trades and limit_wins and no_position
        if buy_signal:
            self.price_sl = technical_min - (self.sl_extra_pips * pip_value)
            self.risk = close - self.price_sl
            if self.risk <= 0:
                self.risk = 20 * pip_value
                self.price_sl = close - self.risk
            st.entry("Compra", st.long)
            self.stop_actual = self.price_sl
        if pos > 0:
            profit_now = close - st.position_avg_price
            if profit_now >= (self.activate_trailing_pips * pip_value):
                new_trailing = close - (self.trailing_stop_pips * pip_value)
                self.trailing_sl = pmath.max(new_trailing, nz(trail_prev))
                self.stop_actual = self.trailing_sl
            st.exit("Salida", "Compra", stop=self.stop_actual)
        if pos == 0:
            self.price_sl = NA
            self.trailing_sl = NA
            self.risk = NA
        h_pos.set(pos)
        h_closed.set(closed)
        h_sma50.set(sma50)
        h_low30.set(low30)
        h_dom.set(dom)
        h_trail.set(self.trailing_sl)
