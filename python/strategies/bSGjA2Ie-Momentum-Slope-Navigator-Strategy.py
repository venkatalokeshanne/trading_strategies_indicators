"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Momentum Slope Navigator Strategy v1.1.1 - Exit/Risk Layer
Author       : not stated
Source URL   : https://www.tradingview.com/script/bSGjA2Ie
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation, orders fill at the bar close (process_orders_on_close), pyramiding 0, 0.04 % commission, 1 tick of
slippage. The signal is a squeeze-momentum histogram (linear regression of close minus the mean of the 20-bar channel middle and
SMA) rising (falling) for N consecutive bars for the first time; the opposite position is closed and the new one entered. Exits
are re-issued every bar from the position's average price: a hard stop (2 % by default, or ATR based), an optional break-even
stop, an optional partial take profit, and a trailing exit that activates at `trail_price` with a distance of `trail_offset`.
Quirk kept: `trail_offset` is given in price units (entry price x 1 %), but Pine reads it in TICKS, so the trail follows the best
price by that many ticks, i.e. by about 1 % of the entry price expressed in ticks (~0.01 x price in price units for a 0.01 tick).
Deviations from the original: none.
Not carried over: language selector (labels only), plots, shapes.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


def _na(x):
    return x != x


def _nz(x, y=0.0):
    return y if x != x else x


class MomentumSlopeNavigator(Script):
    TITLE = "Momentum Slope Navigator Strategy v1.1.1 - Exit/Risk Layer"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, currency="USD", commission_type="percent", commission_value=0.04, slippage=1,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "bSGjA2Ie", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/bSGjA2Ie"}

    def init(self):
        i = self.input
        self.lang = i.string("English", "Language / Dil", options=["English", "Türkçe"])
        self.length = i.int(20, "BB Length", minval=1)
        self.mult_kc = i.float(1.5, "KC MultFactor", minval=0.1, step=0.1)
        self.length_kc = i.int(20, "KC Length", minval=1)
        self.use_true_range = i.bool(True, "Use TrueRange / TrueRange Kullan")
        self.trade_mode = i.string("Both", "Trade Direction / İşlem Yönü", options=["Both", "Long Only", "Short Only"])
        self.confirm_bars = i.int(2, "Consecutive Histogram Bars / Ardışık Histogram Barı", minval=1, maxval=20)
        self.use_ema_filter = i.bool(False, "EMA Trend Filter / EMA Trend Filtresi")
        self.ema_length = i.int(200, "EMA Length / EMA Uzunluğu", minval=1)
        self.use_adx_filter = i.bool(False, "ADX Strength Filter / ADX Güç Filtresi")
        self.adx_preset = i.string("Normal", "ADX Mode / ADX Modu", options=["Soft", "Normal", "Aggressive"])
        self.exit_mode = i.string("Fixed Percent", "Exit Mode / Çıkış Modu", options=["Fixed Percent", "ATR Based"])
        self.use_hard_stop = i.bool(True, "Use Hard Stop / Sabit Stop Kullan")
        self.use_trail_stop = i.bool(True, "Use Trailing Stop / Trailing Stop Kullan")
        self.use_break_even = i.bool(False, "Use Break-Even / Başa Baş Kullan")
        self.use_partial_tp = i.bool(False, "Use Partial TP / Kısmi Kar Al Kullan")
        self.use_time_exit = i.bool(False, "Use Time Exit / Süre Çıkışı Kullan")
        self.use_max_stop_filter = i.bool(False, "Use Max Stop Filter / Maksimum Stop Filtresi")
        self.max_stop_allowed_pct = i.float(5.0, "Max Stop Allowed %", minval=0.1, step=0.1)
        self.fixed_hard_stop_pct = i.float(2.0, "Fixed Hard Stop %", minval=0.1, step=0.1)
        self.fixed_activation_pct = i.float(3.0, "Fixed Trail Activation %", minval=0.1, step=0.1)
        self.fixed_callback_pct = i.float(1.0, "Fixed Trail Follow Distance %", minval=0.1, step=0.1)
        self.fixed_be_activation_pct = i.float(1.5, "Fixed Break-Even Activation %", minval=0.1, step=0.1)
        self.fixed_be_offset_pct = i.float(0.1, "Fixed Break-Even Offset %", minval=0.0, step=0.1)
        self.fixed_partial_tp_pct = i.float(2.0, "Fixed Partial TP %", minval=0.1, step=0.1)
        self.partial_tp_qty_pct = i.float(50.0, "Partial TP Quantity %", minval=1.0, maxval=99.0, step=1.0)
        self.time_exit_bars = i.int(50, "Time Exit Bars / Süre Çıkışı Bar", minval=1)
        self.atr_length = i.int(14, "ATR Length", minval=1)
        self.atr_hard_stop_mult = i.float(2.0, "ATR Hard Stop Mult", minval=0.1, step=0.1)
        self.atr_activation_mult = i.float(3.0, "ATR Trail Activation Mult", minval=0.1, step=0.1)
        self.atr_callback_mult = i.float(1.0, "ATR Trail Follow Distance Mult", minval=0.1, step=0.1)
        self.atr_be_activation_mult = i.float(1.5, "ATR Break-Even Activation Mult", minval=0.1, step=0.1)
        self.atr_be_offset_mult = i.float(0.1, "ATR Break-Even Offset Mult", minval=0.0, step=0.1)
        self.atr_partial_tp_mult = i.float(2.0, "ATR Partial TP Mult", minval=0.1, step=0.1)
        # var state
        self.highest_since = NA
        self.lowest_since = NA
        self.entry_bar_index = NA

    def on_bar(self):
        close, high, low = float(self.close), float(self.high), float(self.low)
        n = self.confirm_bars

        basis = ta.sma(self.close, self.length)
        dev = self.mult_kc * ta.stdev(self.close, self.length)
        ma = ta.sma(self.close, self.length_kc)
        price_range = ta.tr() if self.use_true_range else high - low
        rangema = ta.sma(price_range, self.length_kc)
        mid = pmath.avg(pmath.avg(ta.highest(self.high, self.length_kc), ta.lowest(self.low, self.length_kc)),
                        ta.sma(self.close, self.length_kc))
        val = ta.linreg(self.close - mid, self.length_kc, 0)

        # val history: val[0..n+1]; read the past before recording this bar
        hv = self.H("val")
        vals = [val] + [hv[k] for k in range(1, n + 2)]
        hv.set(val)

        def rising(off):
            return all(vals[off + k] > vals[off + k + 1] for k in range(n))

        def falling(off):
            return all(vals[off + k] < vals[off + k + 1] for k in range(n))

        rising_now, falling_now = rising(0), falling(0)
        rising_prev, falling_prev = rising(1), falling(1)
        raw_long = rising_now and not rising_prev
        raw_short = falling_now and not falling_prev

        ema_value = ta.ema(self.close, self.ema_length)
        _, _, adx_value = ta.dmi(14, 14)
        adx_threshold = 18.0 if self.adx_preset == "Soft" else 20.0 if self.adx_preset == "Normal" else 25.0
        ema_long_ok = (not self.use_ema_filter) or close > ema_value
        ema_short_ok = (not self.use_ema_filter) or close < ema_value
        adx_ok = (not self.use_adx_filter) or adx_value > adx_threshold
        long_allowed = self.trade_mode != "Short Only"
        short_allowed = self.trade_mode != "Long Only"

        atr_value = ta.atr(self.atr_length)
        pre_atr_hs = div(atr_value, close) * 100 * self.atr_hard_stop_mult
        pre_hs = self.fixed_hard_stop_pct if self.exit_mode == "Fixed Percent" else pre_atr_hs
        stop_filter_ok = (not self.use_max_stop_filter) or pre_hs <= self.max_stop_allowed_pct

        final_long = raw_long and long_allowed and ema_long_ok and adx_ok and stop_filter_ok
        final_short = raw_short and short_allowed and ema_short_ok and adx_ok and stop_filter_ok

        st = self.strategy
        if final_long:
            st.close("Short")
            st.entry("Long", st.long)
        if final_short:
            st.close("Long")
            st.entry("Short", st.short)

        entry_price = st.position_avg_price
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        long_prev = self.H("in_long")[1] == 1
        short_prev = self.H("in_short")[1] == 1
        self.H("in_long").set(1.0 if in_long else 0.0)
        self.H("in_short").set(1.0 if in_short else 0.0)
        new_long = in_long and not long_prev
        new_short = in_short and not short_prev

        if new_long or new_short:
            self.highest_since = high
            self.lowest_since = low
            self.entry_bar_index = self.bar_index
        elif in_long or in_short:
            self.highest_since = max(_nz(self.highest_since, high), high)
            self.lowest_since = min(_nz(self.lowest_since, low), low)
        else:
            self.highest_since = NA
            self.lowest_since = NA
            self.entry_bar_index = NA
        bars_in_trade = NA if _na(self.entry_bar_index) else self.bar_index - self.entry_bar_index

        def atr_pct(mult):
            return div(atr_value, entry_price) * 100 * mult if entry_price != 0 else NA

        fixed = self.exit_mode == "Fixed Percent"
        hard_stop_pct = self.fixed_hard_stop_pct if fixed else atr_pct(self.atr_hard_stop_mult)
        activation_pct = self.fixed_activation_pct if fixed else atr_pct(self.atr_activation_mult)
        callback_pct = self.fixed_callback_pct if fixed else atr_pct(self.atr_callback_mult)
        be_activation_pct = self.fixed_be_activation_pct if fixed else atr_pct(self.atr_be_activation_mult)
        be_offset_pct = self.fixed_be_offset_pct if fixed else atr_pct(self.atr_be_offset_mult)
        partial_tp_pct = self.fixed_partial_tp_pct if fixed else atr_pct(self.atr_partial_tp_mult)

        long_be_active = in_long and self.use_break_even and self.highest_since >= entry_price * (1 + be_activation_pct / 100)
        short_be_active = in_short and self.use_break_even and self.lowest_since <= entry_price * (1 - be_activation_pct / 100)

        long_hard_stop = entry_price * (1 - hard_stop_pct / 100)
        short_hard_stop = entry_price * (1 + hard_stop_pct / 100)
        long_be_stop = entry_price * (1 + be_offset_pct / 100)
        short_be_stop = entry_price * (1 - be_offset_pct / 100)
        long_protective = long_hard_stop if self.use_hard_stop else NA
        short_protective = short_hard_stop if self.use_hard_stop else NA
        long_final = max(_nz(long_protective, long_be_stop), long_be_stop) if long_be_active else long_protective
        short_final = min(_nz(short_protective, short_be_stop), short_be_stop) if short_be_active else short_protective

        if in_long and self.use_partial_tp:
            st.exit("Long Partial TP", from_entry="Long", qty_percent=self.partial_tp_qty_pct,
                    limit=entry_price * (1 + partial_tp_pct / 100))
        if in_short and self.use_partial_tp:
            st.exit("Short Partial TP", from_entry="Short", qty_percent=self.partial_tp_qty_pct,
                    limit=entry_price * (1 - partial_tp_pct / 100))
        if in_long:
            if self.use_trail_stop:
                st.exit("Long Protective Trail", from_entry="Long", stop=long_final,
                        trail_price=entry_price * (1 + activation_pct / 100), trail_offset=entry_price * (callback_pct / 100))
            else:
                st.exit("Long Protective Stop", from_entry="Long", stop=long_final)
        if in_short:
            if self.use_trail_stop:
                st.exit("Short Protective Trail", from_entry="Short", stop=short_final,
                        trail_price=entry_price * (1 - activation_pct / 100), trail_offset=entry_price * (callback_pct / 100))
            else:
                st.exit("Short Protective Stop", from_entry="Short", stop=short_final)
        if self.use_time_exit and in_long and bars_in_trade >= self.time_exit_bars:
            st.close("Long", comment="Long Time Exit")
        if self.use_time_exit and in_short and bars_in_trade >= self.time_exit_bars:
            st.close("Short", comment="Short Time Exit")

        self.plot(val, title="Histogram")
