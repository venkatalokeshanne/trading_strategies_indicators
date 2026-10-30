"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Volume Ladder
Author       : wielkieef
Source URL   : https://www.tradingview.com/script/XuywwObg
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. RSI below the oversold level on above-average volume buys at the close (process_orders_on_close); up to 3 lots, each needing a
fall of at least the drop % from the previous lot. While long a stop (below the lowest lot) and limit (above the average price) are issued. The bar a trade exits
the script looks at the last closed trade's exit price to classify TP vs SL (nearest of the previous bar's levels), resets the ladder and starts a cooldown (SL: 3 bars,
TP: 0 bars, which still blocks entry on the exit bar itself).

Deviations from the original: none.
Not carried over: the TP/SL/entry plots and arrow shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class RSIVolumeLadder(Script):
    TITLE = "RSI Volume Ladder"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=3, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=2,
                    commission_type="percent", commission_value=0.05, process_orders_on_close=True)
    SOURCE = {"id": "XuywwObg", "author": "wielkieef", "licence": "not stated",
              "url": "https://www.tradingview.com/script/XuywwObg"}

    def init(self):
        g = "RSI"
        self.rsi_length = self.input.int(14, "RSI długość", group=g)
        self.rsi_oversold = self.input.int(30, "RSI wyprzedanie", group=g)
        g = "Wolumen"
        self.vol_length = self.input.int(20, "Volume SMA długość", group=g)
        self.vol_multiplier = self.input.float(1.5, "Mnożnik wysokiego wolumenu", step=0.1, minval=1.0, group=g)
        g = "Piramidowanie"
        self.drop_percent = self.input.float(1.5, "Min spadek od ostatniego wejścia (%)", step=0.1, group=g)
        self.max_positions = self.input.int(3, "Max liczba pozycji", minval=1, maxval=3, group=g)
        g = "Exit"
        self.tp_percent = self.input.float(4.0, "Take Profit od śr. ceny (%)", step=0.1, group=g)
        self.sl_percent = self.input.float(3.0, "Stop Loss od najniższej pozycji (%)", step=0.1, group=g)
        g = "Cooldown"
        self.cooldown_sl = self.input.int(3, "Cooldown po SL (świece)", minval=0, group=g)
        self.cooldown_tp = self.input.int(0, "Cooldown po TP (świece)", minval=0, group=g)
        self.lowest_entry = NA
        self.last_entry = NA
        self.open_entries = 0
        self.tp_price = NA
        self.sl_price = NA
        self.last_exit_bar = -9999
        self.last_exit_was_sl = False

    def on_bar(self):
        rsi_value = ta.rsi(self.close, self.rsi_length)
        vol_sma = ta.sma(self.volume, self.vol_length)
        high_volume = self.volume > vol_sma * self.vol_multiplier
        oversold = rsi_value < self.rsi_oversold
        entry_signal = oversold and high_volume
        st = self.strategy
        bar_index = self.bar_index
        prev_tp = self.H("tp")[1]
        prev_sl = self.H("sl")[1]
        exited_this_bar = (st.closedtrades > 0 and st.closedtrades_exit_bar_index(st.closedtrades - 1) == bar_index and st.position_size == 0)
        sl_hit = False
        if exited_this_bar:
            real_exit_price = st.closedtrades_exit_price(st.closedtrades - 1)
            if not na(prev_tp) and not na(prev_sl):
                if pmath.abs(real_exit_price - prev_tp) > pmath.abs(real_exit_price - prev_sl):
                    sl_hit = True
            self.last_exit_bar = bar_index
            self.last_exit_was_sl = sl_hit
            self.tp_price = NA
            self.sl_price = NA
            self.lowest_entry = NA
            self.last_entry = NA
            self.open_entries = 0
        bars_since_exit = bar_index - self.last_exit_bar
        required_cooldown = self.cooldown_sl if self.last_exit_was_sl else self.cooldown_tp
        cooldown_active = bars_since_exit <= required_cooldown
        price_dropped = na(self.last_entry) or self.close < self.last_entry * (1 - self.drop_percent / 100)
        can_enter = self.open_entries < self.max_positions and entry_signal and price_dropped and not cooldown_active
        if can_enter:
            st.entry("Long_" + str(self.open_entries + 1), st.long)
            self.lowest_entry = float(self.close) if na(self.lowest_entry) else pmath.min(self.lowest_entry, self.close)
            self.last_entry = float(self.close)
            self.open_entries += 1
        if st.position_size > 0:
            self.tp_price = st.position_avg_price * (1 + self.tp_percent / 100)
            self.sl_price = self.lowest_entry * (1 - self.sl_percent / 100)
            st.exit("Exit", stop=self.sl_price, limit=self.tp_price)
        self.H("tp").set(self.tp_price)
        self.H("sl").set(self.sl_price)
        self.plot(self.tp_price if st.position_size > 0 else NA, "Take Profit", color=color.fuchsia, linewidth=2)
        self.plot(self.sl_price if st.position_size > 0 else NA, "Stop Loss", color=color.red, linewidth=2)
