"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Z-Score Mean Reversion Pro
Author       : ayusattv
Source URL   : https://www.tradingview.com/script/92rilzXd-Z-Score-Mean-Reversion-Pro
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A z-score of the close over a rolling window beyond the threshold, confirmed by RSI, a Bollinger-width minimum and the EMA trend side, opens a position (reversing an opposite one) after a per-side cooldown. The ATR stop / target are set once when the position goes from flat to open (from the close of the fill bar, and left unchanged on a reversal) and re-issued every bar; with ATR exits off the position leaves on the z-score.

Deviations from the original: none.
Not carried over: signal labels and the dashboard table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, ta


class ZScoreMeanReversionPro(Script):
    TITLE = "Z-Score Mean Reversion Pro"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.04, default_qty_type="percent_of_equity", default_qty_value=20, pyramiding=1)
    SOURCE = {"id": "92rilzXd", "author": "ayusattv", "licence": "not stated",
              "url": "https://www.tradingview.com/script/92rilzXd-Z-Score-Mean-Reversion-Pro"}

    def init(self):
        i = self.input
        g = "Z-Score Settings"
        self.rolling_window = i.int(80, "Rolling Window", minval=10, maxval=500, step=1, group=g)
        self.z_thresh = i.float(2.5, "Z-Score Threshold", minval=1.0, maxval=4.0, step=0.1, group=g)
        self.z_exit_thresh = i.float(0.5, "Z-Score Exit Threshold", minval=0.0, maxval=2.0, step=0.1, group=g)
        g = "RSI Confirmation"
        self.rsi_length = i.int(14, "RSI Length", minval=2, maxval=50, group=g)
        self.rsi_ob = i.int(70, "RSI Overbought", minval=50, maxval=95, group=g)
        self.rsi_os = i.int(30, "RSI Oversold", minval=5, maxval=50, group=g)
        self.use_rsi_filter = i.bool(True, "Use RSI Confirmation", group=g)
        g = "Volatility Filter"
        self.bb_length = i.int(20, "BB Length", minval=5, maxval=100, group=g)
        self.bb_mult = i.float(2.0, "BB Multiplier", minval=1.0, maxval=4.0, step=0.1, group=g)
        self.bb_width_min = i.float(0.02, "Min BB Width %", minval=0.005, maxval=0.1, step=0.005, group=g)
        self.use_bb_filter = i.bool(True, "Use BB Width Filter", group=g)
        g = "Trend Filter"
        self.ema_length = i.int(200, "EMA Trend Length", minval=50, maxval=500, group=g)
        self.use_ema_filter = i.bool(True, "Use EMA Trend Filter", group=g)
        g = "Risk Management"
        self.atr_length = i.int(14, "ATR Length", minval=5, maxval=50, group=g)
        self.sl_atr_mult = i.float(2.0, "Stop Loss ATR Multiplier", minval=0.5, maxval=5.0, step=0.1, group=g)
        self.tp_atr_mult = i.float(3.0, "Take Profit ATR Multiplier", minval=0.5, maxval=10.0, step=0.1, group=g)
        self.use_atr_exit = i.bool(True, "Use ATR Stop/TP", group=g)
        self.cool_down = i.int(5, "Signal Cooldown Period", minval=1, maxval=20, group="Cooldown")
        self.enable_backtest = i.bool(True, "Enable Backtest", group="Backtest")
        self.buy_cd = self.cool_down
        self.sell_cd = self.cool_down
        self.sl_price = NA
        self.tp_price = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        rolling_stdev = ta.stdev(close, self.rolling_window, False)
        rolling_mean = ta.sma(close, self.rolling_window)
        z_score = div(close - rolling_mean, rolling_stdev) if rolling_stdev > 0 else 0.0
        rsi_val = ta.rsi(close, self.rsi_length)
        bb_basis = ta.sma(close, self.bb_length)
        bb_dev = self.bb_mult * ta.stdev(close, self.bb_length)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        bb_width = div(bb_upper - bb_lower, bb_basis) if bb_basis > 0 else 0.0
        ema_trend = ta.ema(close, self.ema_length)
        atr_val = ta.atr(self.atr_length)
        z_oversold = z_score < -self.z_thresh
        z_overbought = z_score > self.z_thresh
        z_long_exit = z_score > self.z_exit_thresh
        z_short_exit = z_score < -self.z_exit_thresh
        rsi_long_ok = rsi_val < self.rsi_os if self.use_rsi_filter else True
        rsi_short_ok = rsi_val > self.rsi_ob if self.use_rsi_filter else True
        bb_wide = bb_width > self.bb_width_min if self.use_bb_filter else True
        ema_long_ok = close > ema_trend if self.use_ema_filter else True
        ema_short_ok = close < ema_trend if self.use_ema_filter else True
        long_signal = z_oversold and rsi_long_ok and bb_wide and ema_long_ok
        short_signal = z_overbought and rsi_short_ok and bb_wide and ema_short_ok
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        self.buy_cd += 1
        self.sell_cd += 1
        if long_signal and self.enable_backtest:
            if self.buy_cd >= self.cool_down:
                if st.position_size < 0:
                    st.close("Short", comment="Close Short for Long")
                st.entry("Long", st.long, comment="Z-Score Long Entry")
                self.buy_cd = 0
                self.sell_cd = self.cool_down
        if short_signal and self.enable_backtest:
            if self.sell_cd >= self.cool_down:
                if st.position_size > 0:
                    st.close("Long", comment="Close Long for Short")
                st.entry("Short", st.short, comment="Z-Score Short Entry")
                self.sell_cd = 0
                self.buy_cd = self.cool_down
        if st.position_size != 0 and pos_prev == 0:
            if st.position_size > 0:
                self.sl_price = close - atr_val * self.sl_atr_mult
                self.tp_price = close + atr_val * self.tp_atr_mult
            elif st.position_size < 0:
                self.sl_price = close + atr_val * self.sl_atr_mult
                self.tp_price = close - atr_val * self.tp_atr_mult
        if self.use_atr_exit and st.position_size != 0:
            if st.position_size > 0:
                st.exit("ATR Exit Long", from_entry="Long", stop=self.sl_price, limit=self.tp_price, comment_loss="SL Hit", comment_profit="TP Hit")
            elif st.position_size < 0:
                st.exit("ATR Exit Short", from_entry="Short", stop=self.sl_price, limit=self.tp_price, comment_loss="SL Hit", comment_profit="TP Hit")
        if self.enable_backtest:
            if st.position_size > 0 and z_long_exit and not self.use_atr_exit:
                st.close("Long", comment="Z-Score Mean Reversion Exit")
            if st.position_size < 0 and z_short_exit and not self.use_atr_exit:
                st.close("Short", comment="Z-Score Mean Reversion Exit")
            if st.position_size > 0 and z_score > 0 and not self.use_atr_exit:
                st.close("Long", comment="Z-Score Cross Zero Exit")
            if st.position_size < 0 and z_score < 0 and not self.use_atr_exit:
                st.close("Short", comment="Z-Score Cross Zero Exit")
