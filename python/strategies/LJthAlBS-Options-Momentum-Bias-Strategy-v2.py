"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Options Momentum Bias Strategy v2
Author       : bblacks_tv
Source URL   : https://www.tradingview.com/script/LJthAlBS-Options-Momentum-Bias-Strategy-v2
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Price on the right side of VWAP and the EMA stack (9/20/50) with a volume spike, a recent dip to the fast EMA and a breakout candle enters at the next open
(cooldown of 5 bars per side, regular session only), reversing an open opposite trade. Both exit orders are rebuilt every bar from position_avg_price (ATR stop 1.0 / target 1.5; na while flat) and a close
through VWAP exits.

Deviations from the original: none.
Not carried over: VWAP / EMA plots, background, labels and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, ta


class OptionsMomentumBias(Script):
    TITLE = "Options Momentum Bias Strategy v2"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=0)
    SOURCE = {"id": "LJthAlBS", "author": "bblacks_tv", "licence": "not stated",
              "url": "https://www.tradingview.com/script/LJthAlBS-Options-Momentum-Bias-Strategy-v2"}

    def init(self):
        self.fast_ema_len = self.input.int(9, "Fast EMA Length", minval=1)
        self.slow_ema_len = self.input.int(20, "Slow EMA Length", minval=1)
        self.trend_ema_len = self.input.int(50, "Trend EMA Length", minval=1)
        self.vol_len = self.input.int(20, "Volume Avg Length", minval=1)
        self.vol_mult = self.input.float(1.2, "Volume Multiplier", step=0.1)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.stop_atr = self.input.float(1.0, "Stop Loss ATR Mult", step=0.1)
        self.target_atr = self.input.float(1.5, "Target ATR Mult", step=0.1)
        self.pullback_lookback = self.input.int(3, "Pullback Lookback Bars", minval=1)
        self.cooldown_bars = self.input.int(5, "Signal Cooldown Bars", minval=0)
        self.use_session = self.input.bool(True, "Use Regular Session Filter")
        self.session_input = self.input.session("0930-1600", "Session")
        self.last_bull_bar = NA
        self.last_bear_bar = NA

    def on_bar(self):
        in_session = not na(self.time_fn(None, self.session_input))
        session_ok = in_session if self.use_session else True
        vwap_value = ta.vwap(self.close)
        fast_ema = S(ta.ema(self.close, self.fast_ema_len))
        slow_ema = ta.ema(self.close, self.slow_ema_len)
        trend_ema = ta.ema(self.close, self.trend_ema_len)
        avg_vol = ta.sma(self.volume, self.vol_len)
        atr = ta.atr(self.atr_len)
        vol_active = self.volume > avg_vol * self.vol_mult
        bull_bias = self.close > vwap_value and fast_ema[0] > slow_ema and self.close > trend_ema
        bear_bias = self.close < vwap_value and fast_ema[0] < slow_ema and self.close < trend_ema
        bull_pullback = ta.lowest(self.low, self.pullback_lookback) <= fast_ema[0]
        bear_pullback = ta.highest(self.high, self.pullback_lookback) >= fast_ema[0]
        high, low = S(self.high), S(self.low)
        bull_break = self.close > high[1] and self.close > self.open and fast_ema[0] > fast_ema[1]
        bear_break = self.close < low[1] and self.close < self.open and fast_ema[0] < fast_ema[1]
        bull_signal_raw = session_ok and bull_bias and vol_active and bull_pullback and bull_break
        bear_signal_raw = session_ok and bear_bias and vol_active and bear_pullback and bear_break
        bull_cooldown_ok = na(self.last_bull_bar) or (self.bar_index - self.last_bull_bar > self.cooldown_bars)
        bear_cooldown_ok = na(self.last_bear_bar) or (self.bar_index - self.last_bear_bar > self.cooldown_bars)
        st = self.strategy
        bull_signal = bull_signal_raw and bull_cooldown_ok and st.position_size <= 0
        bear_signal = bear_signal_raw and bear_cooldown_ok and st.position_size >= 0
        if bull_signal:
            self.last_bull_bar = self.bar_index
        if bear_signal:
            self.last_bear_bar = self.bar_index
        if bull_signal:
            st.entry("CALL", st.long)
        if bear_signal:
            st.entry("PUT", st.short)
        avg = st.position_avg_price
        st.exit("CALL Exit", from_entry="CALL", stop=avg - atr * self.stop_atr, limit=avg + atr * self.target_atr)
        st.exit("PUT Exit", from_entry="PUT", stop=avg + atr * self.stop_atr, limit=avg - atr * self.target_atr)
        if st.position_size > 0 and self.close < vwap_value:
            st.close("CALL", comment="Lost VWAP")
        if st.position_size < 0 and self.close > vwap_value:
            st.close("PUT", comment="Reclaimed VWAP")
        self.plot(vwap_value, "VWAP", color=color.yellow, linewidth=2)
