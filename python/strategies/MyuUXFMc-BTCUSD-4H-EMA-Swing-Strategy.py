"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Crypto Swing EMA Colour Strategy Plus
Author       : not stated
Source URL   : https://www.tradingview.com/script/MyuUXFMc
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Trades are taken only inside the date window. With the anti-whipsaw option on (default) the EMA(200) colour change is confirmed when the close has stayed beyond the EMA +/- an ATR buffer for the required number of bars (first bar of the run), with a minimum number of bars since the last entry; a green change opens a long (or reverses a short), a red change a short (or reverses a long) with 95 % of equity. A long also closes on the red change; a short also closes on the "sell" setup (EMA below, MACD histogram cross-under, RSI 50-80, MFI over 50). ATR emergency stops are attached to longs and shorts, shorts also get two ATR take-profit legs (50 % each) and close on a capitulation signal (large move, oversold RSI / stochastic and a stochastic cross-over). Everything is closed outside the window.
Deviations from the original: none.
Not carried over: plots and shapes.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class CryptoSwingEma(Script):
    TITLE = "Crypto Swing EMA Colour Strategy Plus"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=95, commission_type="percent", commission_value=0.06, slippage=1, pyramiding=0)
    SOURCE = {"id": "MyuUXFMc", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/MyuUXFMc"}

    def init(self):
        i = self.input
        g = "Date Window"
        self.start_date = i.time(self.timestamp("UTC", 2021, 1, 1), "Backtest start", group=g)
        self.end_date = i.time(self.timestamp("UTC", 2030, 1, 1), "Backtest end", group=g)
        self.allow_long = i.bool(True, "Allow longs", group="Direction")
        self.allow_short = i.bool(True, "Allow shorts", group="Direction")
        g = "Indicator"
        self.len_rsi = i.int(14, "RSI Length", group=g)
        self.len_mfi = i.int(14, "MFI Length", group=g)
        self.fast_len = i.int(12, "MACD Fast", group=g)
        self.slow_len = i.int(26, "MACD Slow", group=g)
        self.sig_len = i.int(9, "MACD Signal", group=g)
        self.ema_len = i.int(200, "EMA Length", group=g)
        self.atr_len = i.int(14, "ATR length", group="Risk")
        g = "Anti-Whipsaw"
        self.use_anti_whipsaw = i.bool(True, "Use anti-whipsaw EMA buffer", group=g)
        self.buffer_type = i.string("ATR", "Buffer type", options=["ATR", "Percent"], group=g)
        self.buffer_atr_mult = i.float(0.35, "EMA buffer ATR multiplier", step=0.05, group=g)
        self.buffer_pct = i.float(0.6, "EMA buffer %", step=0.1, group=g)
        self.confirm_bars = i.int(2, "Confirmation bars beyond EMA", minval=1, group=g)
        self.min_bars_between = i.int(8, "Minimum bars between trades", minval=0, group=g)
        g = "Capitulation Exit"
        self.stoch_len = i.int(14, "Stoch length", group=g)
        self.stoch_smooth = i.int(3, "Stoch smoothing", group=g)
        self.use_short_cap_exit = i.bool(True, "Use short capitulation exit", group=g)
        self.short_cap_atr = i.float(5.0, "Short capitulation ATR move", step=0.1, group=g)
        self.short_oversold_rsi = i.float(28, "Short oversold RSI", step=1, group=g)
        self.short_oversold_stoch = i.float(20, "Short oversold Stoch", step=1, group=g)
        g = "Risk"
        self.use_atr_stop = i.bool(True, "Use ATR emergency stop", group=g)
        self.atr_mult = i.float(4.0, "ATR stop multiplier", step=0.1, group=g)
        g = "Short Profit Taking"
        self.use_short_tp = i.bool(True, "Use short take profits", group=g)
        self.short_tp1_atr = i.float(4.0, "Short TP1 ATR", step=0.1, group=g)
        self.short_tp2_atr = i.float(7.0, "Short TP2 ATR", step=0.1, group=g)
        self.short_tp1_qty = i.float(50, "Short TP1 qty %", minval=1, maxval=100, step=5, group=g)
        self.short_tp2_qty = i.float(50, "Short TP2 qty %", minval=1, maxval=100, step=5, group=g)
        self.last_trade_bar = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_ca, h_cb = self.H("ca"), self.H("cb")
        ca_1, cb_1 = h_ca[1], h_cb[1]
        in_window = self.time >= self.start_date and self.time <= self.end_date
        ema200 = ta.ema(close, self.ema_len)
        rsi_val = ta.rsi(close, self.len_rsi)
        mfi_val = ta.mfi(self.hlc3, self.len_mfi)
        macd_line, signal_line, hist_line = ta.macd(close, self.fast_len, self.slow_len, self.sig_len)
        ema_bull = close > ema200
        ema_bear = close < ema200
        macd_bull_cross = ta.crossover(hist_line, 0)
        macd_bear_cross = ta.crossunder(hist_line, 0)
        sell_signal = ema_bear and macd_bear_cross and rsi_val > 50 and rsi_val < 80 and mfi_val > 50
        atr_val = ta.atr(self.atr_len)
        ema_buffer = atr_val * self.buffer_atr_mult if self.buffer_type == "ATR" else ema200 * self.buffer_pct / 100
        upper_band = ema200 + ema_buffer
        lower_band = ema200 - ema_buffer
        above_upper = close > upper_band
        below_lower = close < lower_band
        confirmed_above = ta.barssince(not above_upper) >= self.confirm_bars - 1
        confirmed_below = ta.barssince(not below_lower) >= self.confirm_bars - 1
        raw_green = ta.crossover(close, ema200)
        raw_red = ta.crossunder(close, ema200)
        enough = na(self.last_trade_bar) or self.bar_index - self.last_trade_bar >= self.min_bars_between
        if self.use_anti_whipsaw:
            ema_turns_green = confirmed_above and not (ca_1 == 1) and enough
            ema_turns_red = confirmed_below and not (cb_1 == 1) and enough
        else:
            ema_turns_green = raw_green and enough
            ema_turns_red = raw_red and enough
        raw_stoch = ta.stoch(close, high, low, self.stoch_len)
        stoch_k = ta.sma(raw_stoch, self.stoch_smooth)
        stoch_d = ta.sma(stoch_k, self.stoch_smooth)
        stoch_bull_cross = ta.crossover(stoch_k, stoch_d)
        pos = st.position_size
        long_entry = in_window and self.allow_long and pos <= 0 and ema_turns_green
        short_entry = in_window and self.allow_short and pos >= 0 and ema_turns_red
        long_exit = pos > 0 and ema_turns_red
        short_exit_by_signal = pos < 0 and sell_signal
        if long_entry:
            st.entry("Long", st.long)
            self.last_trade_bar = self.bar_index
        if short_entry:
            st.entry("Short", st.short)
            self.last_trade_bar = self.bar_index
        if long_exit:
            st.close("Long", comment="EMA turned red")
        if short_exit_by_signal:
            st.close("Short", comment="SELL exit")
        if not in_window:
            st.close_all(comment="Out of window")
        in_long = pos > 0
        in_short = pos < 0
        avg = st.position_avg_price
        short_move_atr = div(avg - close, atr_val) if in_short else 0.0
        short_cap_exit = in_short and self.use_short_cap_exit and short_move_atr >= self.short_cap_atr and (rsi_val <= self.short_oversold_rsi or stoch_k <= self.short_oversold_stoch) and stoch_bull_cross
        if in_long and self.use_atr_stop:
            st.exit("Long ATR Stop", from_entry="Long", stop=avg - atr_val * self.atr_mult)
        if in_short:
            short_stop = avg + atr_val * self.atr_mult
            short_tp1 = avg - atr_val * self.short_tp1_atr
            short_tp2 = avg - atr_val * self.short_tp2_atr
            if self.use_short_tp and self.use_atr_stop:
                st.exit("Short TP1/SL", from_entry="Short", limit=short_tp1, stop=short_stop, qty_percent=self.short_tp1_qty)
                st.exit("Short TP2/SL", from_entry="Short", limit=short_tp2, stop=short_stop, qty_percent=self.short_tp2_qty)
            elif self.use_short_tp:
                st.exit("Short TP1", from_entry="Short", limit=short_tp1, qty_percent=self.short_tp1_qty)
                st.exit("Short TP2", from_entry="Short", limit=short_tp2, qty_percent=self.short_tp2_qty)
            elif self.use_atr_stop:
                st.exit("Short ATR Stop", from_entry="Short", stop=short_stop)
            if short_cap_exit:
                st.close("Short", comment="Short capitulation exit")
        h_ca.set(1 if confirmed_above else 0)
        h_cb.set(1 if confirmed_below else 0)
