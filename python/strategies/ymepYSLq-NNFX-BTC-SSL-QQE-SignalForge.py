"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NNFX BTC SSL+QQE - SignalForge
Author       : SignalForge-Ai
Source URL   : https://www.tradingview.com/script/ymepYSLq
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close crossing the SSL EMA baseline, confirmed by the QQE histogram sign (fast QQE EMA minus its
EMA) and a close inside the Keltner channel, enters inside the backtest window; the signals can be inverted. While in a position an ATR stop / target around
the average price is issued; the opposite baseline / QQE state closes the trade at the close.

Deviations from the original: none.
Not carried over: alert_message JSON texts and the plots of the channel (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta

START_DATE = 1577836800000     # 2020-01-01 UTC
END_DATE = 1924905600000       # 2030-12-31 UTC


class NNFXSslQqe(Script):
    TITLE = "NNFX BTC SSL+QQE - SignalForge"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=1, commission_type="percent",
                    commission_value=0.04, slippage=2, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "ymepYSLq", "author": "SignalForge-Ai", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ymepYSLq"}

    def init(self):
        g = "Settings"
        self.src = self.input.source(self.close, "Price Source", group=g)
        self.invert_sig = self.input.bool(False, "Invert Signals", group=g)
        self.ssl_len = self.input.int(20, "SSL Baseline EMA length", group="Baseline")
        g = "Keltner"
        self.kc_len = self.input.int(20, "Keltner EMA length", group=g)
        self.kc_mult = self.input.float(1.5, "Keltner ATR mult", group=g)
        g = "QQE"
        self.qqe_rsi_len = self.input.int(6, "QQE RSI period", group=g)
        self.qqe_smooth = self.input.int(5, "QQE smoothing", group=g)
        g = "Risk"
        self.atr_len = self.input.int(14, "ATR length", group=g)
        self.stop_mult = self.input.float(1.5, "Stop = N x ATR", group=g)
        self.tp_mult = self.input.float(3.0, "Target = N x ATR", group=g)
        g = "Backtest"
        self.start_date = self.input.time(START_DATE, "Backtest start", group=g)
        self.end_date = self.input.time(END_DATE, "Backtest end", group=g)

    def on_bar(self):
        src = self.src
        ssl_line = ta.ema(src, self.ssl_len)
        ssl_bull = src > ssl_line
        kc_atr = ta.atr(self.kc_len)
        kc_mid = ta.ema(src, self.kc_len)
        kc_upper = kc_mid + kc_atr * self.kc_mult
        kc_lower = kc_mid - kc_atr * self.kc_mult
        qqe_rsi = ta.rsi(src, self.qqe_rsi_len)
        qqe_fast = ta.ema(qqe_rsi, self.qqe_smooth)
        qqe_slow = ta.ema(qqe_fast, self.qqe_smooth)
        qqe_hist = qqe_fast - qqe_slow
        qqe_bull = qqe_hist > 0
        inside_kc = src >= kc_lower and src <= kc_upper
        in_date = self.time >= self.start_date and self.time <= self.end_date
        cross_up = ta.crossover(src, ssl_line)
        cross_dn = ta.crossunder(src, ssl_line)
        long_entry = cross_up and qqe_bull and inside_kc and in_date
        short_entry = cross_dn and not qqe_bull and inside_kc and in_date
        st = self.strategy
        if self.invert_sig:
            long_entry = cross_dn and not qqe_bull and inside_kc and in_date
            short_entry = cross_up and qqe_bull and inside_kc and in_date
        exit_long = st.position_size > 0 and ((not qqe_bull) or (not ssl_bull))
        exit_short = st.position_size < 0 and (qqe_bull or ssl_bull)
        if self.invert_sig:
            exit_long = st.position_size > 0 and (qqe_bull or ssl_bull)
            exit_short = st.position_size < 0 and ((not qqe_bull) or (not ssl_bull))
        atr_val = ta.atr(self.atr_len)
        if long_entry:
            st.entry("L", st.long)
        if short_entry:
            st.entry("S", st.short)
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("XL", from_entry="L", stop=avg - atr_val * self.stop_mult, limit=avg + atr_val * self.tp_mult)
        if st.position_size < 0:
            st.exit("XS", from_entry="S", stop=avg + atr_val * self.stop_mult, limit=avg - atr_val * self.tp_mult)
        if exit_long:
            st.close("L")
        if exit_short:
            st.close("S")
        self.plot(ssl_line, "SSL Baseline", color=color.blue if ssl_bull else color.red)
        self.plot(kc_mid, "Keltner Mid", color=color.gray)
        self.plot(kc_upper, "Keltner Upper", color=color.gray)
        self.plot(kc_lower, "Keltner Lower", color=color.gray)
