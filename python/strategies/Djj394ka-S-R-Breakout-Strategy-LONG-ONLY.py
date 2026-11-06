"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : S/R Breakout Strategy LONG ONLY Independent TP + Cooldown
Author       : One_punchcoin
Source URL   : https://www.tradingview.com/script/Djj394ka-S-R-Breakout-Strategy-LONG-ONLY
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The latest confirmed pivot high / low are the resistance / support; when the channel between them is at most
the maximum width, a close crossing over resistance on the right side of the (previous bar's) SMA, far enough from it, opens another lot (up to the open-trade limit
and with a bar cooldown). Every open lot gets its own take-profit limit, re-issued each bar from the lot's entry price (opentrades loop).

Deviations from the original: none.
Not carried over: the SMA / resistance / support plots and the entry shape (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, pmath, ta


class SRBreakoutLongOnly(Script):
    TITLE = "S/R Breakout Strategy LONG ONLY Independent TP + Cooldown"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=100, process_orders_on_close=True)
    SOURCE = {"id": "Djj394ka", "author": "One_punchcoin", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Djj394ka-S-R-Breakout-Strategy-LONG-ONLY"}

    def init(self):
        g = "Настройки S/R Вход"
        self.left_bars = self.input.int(15, "Entry Left Bars", group=g, minval=1)
        self.right_bars = self.input.int(15, "Entry Right Bars", group=g, minval=1)
        g = "Управление сделками"
        self.allow_long = self.input.bool(True, "Активировать LONG?", group=g)
        self.max_range_perc = self.input.float(2.0, "Макс. ширина канала (%)", minval=0.1, step=0.1, group=g)
        self.tp_percent = self.input.float(1.0, "Take Profit (%)", minval=0.1, step=0.1, group=g)
        self.max_open_trades = self.input.int(20, "Макс. количество одновременных сделок", minval=1, group=g)
        self.cooldown_bars = self.input.int(10, "Cooldown bars после каждого входа", minval=0, group=g)
        g = "Фильтр SMA (Мульти-Таймфрейм)"
        self.use_sma_filter = self.input.bool(True, "Использовать SMA фильтр?", group=g)
        self.sma_length = self.input.int(200, "Период SMA", minval=1, group=g)
        self.sma_tf = self.input.timeframe("", "Таймфрейм SMA", group=g)
        self.min_distance_perc = self.input.float(1.0, "Мин. расстояние от SMA (%)", minval=0.1, step=0.1, group=g)
        self.resistance = NA
        self.support = NA
        self.last_entry_bar = NA
        self.trade_counter = 0

    def on_bar(self):
        sma_n = self.sma_length
        sma_value = self.security(None, self.sma_tf, lambda v: S(ta.sma(v.close, sma_n))[1], lookahead=False)
        ph = ta.pivothigh(self.left_bars, self.right_bars)
        pl = ta.pivotlow(self.left_bars, self.right_bars)
        if not na(ph):
            self.resistance = ph
        if not na(pl):
            self.support = pl
        channel_range = NA
        if not na(self.resistance) and not na(self.support) and self.support != 0:
            channel_range = div(self.resistance - self.support, self.support) * 100
        is_range_valid = (not na(channel_range)) and channel_range <= self.max_range_perc
        breakout_long = (not na(self.resistance)) and ta.crossover(self.close, self.resistance)
        sma_cond_long = (not self.use_sma_filter) or ((not na(sma_value)) and self.close > sma_value)
        dist_perc = div(pmath.abs(self.close - sma_value), sma_value) * 100 if not na(sma_value) else NA
        far_enough = (not self.use_sma_filter) or ((not na(dist_perc)) and dist_perc > self.min_distance_perc)
        st = self.strategy
        can_open_more = st.opentrades < self.max_open_trades
        bars_since = 1000000 if na(self.last_entry_bar) else (self.bar_index - self.last_entry_bar)
        cooldown_passed = self.cooldown_bars <= 0 or bars_since >= self.cooldown_bars
        long_condition = (self.barstate.isconfirmed and self.allow_long and breakout_long and is_range_valid and sma_cond_long and far_enough
                          and can_open_more and cooldown_passed)
        if long_condition:
            self.trade_counter += 1
            entry_id = "Long_" + str(self.trade_counter)
            st.entry(entry_id, st.long, comment=entry_id)
            self.last_entry_bar = self.bar_index
        n_open = st.opentrades
        if n_open > 0:
            for i in range(n_open):
                cur_id = st.opentrades_entry_id(i)
                cur_price = st.opentrades_entry_price(i)
                st.exit("TP_" + cur_id, from_entry=cur_id, limit=cur_price * (1 + self.tp_percent / 100), comment="Independent TP")
        self.plot(self.resistance, "Entry Resistance", color=color.red, linewidth=2)
        self.plot(self.support, "Entry Support", color=color.blue, linewidth=2)
