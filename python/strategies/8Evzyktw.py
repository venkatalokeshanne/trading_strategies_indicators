"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy 461 - TS M15
Author       : Fran_Pineda
Source URL   : https://www.tradingview.com/script/8Evzyktw
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A "turtle soup" candle - the previous candle against the trade, this one sweeping the previous low (high) without taking the previous high
(low), closing in the trade direction back above the previous low (below the previous high) - enters when flat with the EMA200 bias. Stop is the candle extreme plus / minus a tick buffer, target
the R:R multiple; the same stop / limit orders are re-issued while in the position.

Deviations from the original: none.
Not carried over: the EMA plot, the info table and the alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class Strategy461(Script):
    TITLE = "Strategy 461 - TS M15"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=95, pyramiding=0, commission_type="percent",
                    commission_value=0.02, process_orders_on_close=True)
    SOURCE = {"id": "8Evzyktw", "author": "Fran_Pineda", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8Evzyktw"}

    def init(self):
        self.rr_target = self.input.float(1.0, "RR Target", minval=1.0, step=0.25)
        self.buffer_ticks = self.input.int(20, "Buffer SL en ticks", minval=0)
        self.use_bias = self.input.bool(True, "Usar filtro EMA200")
        self.ema_len = self.input.int(200, "EMA Bias Length", minval=1)
        self.use_session = self.input.bool(False, "Filtrar sesión")
        self.session_inp = self.input.session("0700-1700", "Sesión operativa")
        self.long_sl = NA
        self.long_tp = NA
        self.short_sl = NA
        self.short_tp = NA

    def on_bar(self):
        ema200 = ta.ema(self.close, self.ema_len)
        in_session = (not self.use_session) or not na(self.time_fn(None, self.session_inp))
        prev_bear = self.close[1] < self.open[1]
        prev_bull = self.close[1] > self.open[1]
        takes_prev_low = self.low < self.low[1]
        takes_prev_high = self.high > self.high[1]
        clean_bull_ts = prev_bear and takes_prev_low and not takes_prev_high and self.close > self.open and self.close > self.low[1]
        clean_bear_ts = prev_bull and takes_prev_high and not takes_prev_low and self.close < self.open and self.close < self.high[1]
        bias_long_ok = (not self.use_bias) or self.close > ema200
        bias_short_ok = (not self.use_bias) or self.close < ema200
        st = self.strategy
        flat = st.position_size == 0
        tick_buffer = self.syminfo.mintick * self.buffer_ticks
        long_sl_calc = self.low - tick_buffer
        long_risk_calc = self.close - long_sl_calc
        long_tp_calc = self.close + long_risk_calc * self.rr_target
        short_sl_calc = self.high + tick_buffer
        short_risk_calc = short_sl_calc - self.close
        short_tp_calc = self.close - short_risk_calc * self.rr_target
        long_risk_ok = long_risk_calc > 0
        short_risk_ok = short_risk_calc > 0
        long_entry = flat and in_session and clean_bull_ts and bias_long_ok and long_risk_ok
        short_entry = flat and in_session and clean_bear_ts and bias_short_ok and short_risk_ok
        if long_entry:
            self.long_sl = long_sl_calc
            self.long_tp = long_tp_calc
            self.short_sl = NA
            self.short_tp = NA
            st.entry("Long", st.long, alert_message="ENTRY_LONG")
            st.exit("Long TP/SL", from_entry="Long", stop=self.long_sl, limit=self.long_tp)
        if short_entry:
            self.short_sl = short_sl_calc
            self.short_tp = short_tp_calc
            self.long_sl = NA
            self.long_tp = NA
            st.entry("Short", st.short, alert_message="ENTRY_SHORT")
            st.exit("Short TP/SL", from_entry="Short", stop=self.short_sl, limit=self.short_tp)
        if st.position_size > 0 and not na(self.long_sl) and not na(self.long_tp):
            st.exit("Long TP/SL", from_entry="Long", stop=self.long_sl, limit=self.long_tp)
        if st.position_size < 0 and not na(self.short_sl) and not na(self.short_tp):
            st.exit("Short TP/SL", from_entry="Short", stop=self.short_sl, limit=self.short_tp)
        if st.position_size == 0 and not long_entry and not short_entry:
            self.long_sl = NA
            self.long_tp = NA
            self.short_sl = NA
            self.short_tp = NA
        self.plot(ema200, "EMA 200", color=color.orange, linewidth=2)
