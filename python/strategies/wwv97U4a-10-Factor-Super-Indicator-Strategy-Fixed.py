"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 10-Factor Super Indicator Strategy (Fixed)
Author       : kmarin137
Source URL   : https://www.tradingview.com/script/wwv97U4a-10-Factor-Super-Indicator-Strategy-Fixed
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Ten weighted factors (EMA trend, Supertrend, MACD, RSI, ADX/DI, VWAP, Bollinger position, stochastic RSI, OBV vs its EMA, ATR regime) each add +weight, -weight or 0 to a raw score that is scaled to +-100 by the total weight.
A long needs a score at or above the long threshold with the EMA trend, Supertrend, ADX and ATR regime all agreeing (short mirrored) and flips a flat or short position; one exit order (ATR stop and ATR target from the average entry price) per side is re-issued every bar, and a score below (above) the exit threshold closes the position at the next open.
Deviations from the original: none.
Not carried over: the score colour and the factor table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, ta


class TenFactorSuper(Script):
    TITLE = "10-Factor Super Indicator Strategy (Fixed)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "wwv97U4a", "author": "kmarin137", "licence": "not stated", "url": "https://www.tradingview.com/script/wwv97U4a-10-Factor-Super-Indicator-Strategy-Fixed"}

    def init(self):
        i = self.input
        self.ema_fast_len = i.int(20, "EMA Fast")
        self.ema_slow_len = i.int(50, "EMA Slow")
        self.macd_fast = i.int(12, "MACD Fast")
        self.macd_slow = i.int(26, "MACD Slow")
        self.macd_signal_len = i.int(9, "MACD Signal")
        self.rsi_len = i.int(14, "RSI Length")
        self.adx_len = i.int(14, "ADX Length")
        self.adx_smoothing = i.int(14, "ADX Smoothing")
        self.adx_min = i.float(20.0, "ADX Minimum")
        self.bb_len = i.int(20, "BB Length")
        self.bb_mult = i.float(2.0, "BB Mult")
        self.stoch_rsi_len = i.int(14, "Stoch RSI Length")
        self.stoch_k_len = i.int(3, "Stoch RSI K")
        self.stoch_d_len = i.int(3, "Stoch RSI D")
        self.st_atr = i.int(10, "Supertrend ATR Length")
        self.st_mult = i.float(3.0, "Supertrend Factor")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_min_pct = i.float(0.4, "Min ATR % of Price", step=0.1)
        self.long_threshold = i.float(45.0, "Long Score Threshold", minval=0, maxval=100)
        self.short_threshold = i.float(-45.0, "Short Score Threshold", minval=-100, maxval=0)
        self.exit_threshold = i.float(10.0, "Exit Score Threshold")
        self.stop_atr_mult = i.float(2.0, "Stop ATR Mult")
        self.take_atr_mult = i.float(3.5, "Take Profit ATR Mult")
        self.w_ema = i.int(15, "Weight EMA Trend")
        self.w_st = i.int(15, "Weight Supertrend")
        self.w_macd = i.int(12, "Weight MACD")
        self.w_rsi = i.int(8, "Weight RSI")
        self.w_adx = i.int(10, "Weight ADX")
        self.w_vwap = i.int(10, "Weight VWAP")
        self.w_bb = i.int(8, "Weight Bollinger")
        self.w_stoch = i.int(8, "Weight Stoch RSI")
        self.w_obv = i.int(7, "Weight OBV")
        self.w_atr = i.int(7, "Weight ATR Regime")

    def on_bar(self):
        st = self.strategy
        close = self.close
        total_weight = self.w_ema + self.w_st + self.w_macd + self.w_rsi + self.w_adx + self.w_vwap + self.w_bb + self.w_stoch + self.w_obv + self.w_atr
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        macd_line, macd_signal, macd_hist = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_signal_len)
        rsi = ta.rsi(close, self.rsi_len)
        plus_di, minus_di, adx = ta.dmi(self.adx_len, self.adx_smoothing)
        vwap_val = ta.vwap(self.hlc3)
        bb_basis = ta.sma(close, self.bb_len)
        bb_dev = ta.stdev(close, self.bb_len) * self.bb_mult
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        rsi_base = ta.rsi(close, self.stoch_rsi_len)
        rsi_lowest = ta.lowest(rsi_base, self.stoch_rsi_len)
        rsi_highest = ta.highest(rsi_base, self.stoch_rsi_len)
        stoch_rsi_raw = 100 * div(rsi_base - rsi_lowest, rsi_highest - rsi_lowest) if rsi_highest != rsi_lowest else 0
        stoch_k = ta.sma(stoch_rsi_raw, self.stoch_k_len)
        stoch_d = ta.sma(stoch_k, self.stoch_d_len)
        st_line, st_dir = ta.supertrend(self.st_mult, self.st_atr)
        obv = ta.obv()
        obv_ema = ta.ema(obv, 21)
        atr = ta.atr(self.atr_len)
        atr_pct = div(atr, close) * 100.0 if close != 0 else 0.0
        ema_bull = ema_fast > ema_slow and close > ema_fast
        ema_bear = ema_fast < ema_slow and close < ema_fast
        super_bull = st_dir < 0
        super_bear = st_dir > 0
        macd_bull = macd_line > macd_signal and macd_hist > 0
        macd_bear = macd_line < macd_signal and macd_hist < 0
        rsi_bull = rsi > 55
        rsi_bear = rsi < 45
        adx_bull = adx > self.adx_min and plus_di > minus_di
        adx_bear = adx > self.adx_min and minus_di > plus_di
        vwap_bull = close > vwap_val
        vwap_bear = close < vwap_val
        bb_bull = close > bb_basis and close < bb_upper
        bb_bear = close < bb_basis and close > bb_lower
        stoch_bull = stoch_k > stoch_d and stoch_k > 20 and stoch_k < 80
        stoch_bear = stoch_k < stoch_d and stoch_k > 20 and stoch_k < 80
        obv_bull = obv > obv_ema
        obv_bear = obv < obv_ema
        atr_active = atr_pct > self.atr_min_pct
        atr_score = self.w_atr if atr_active else 0

        def f(bull, bear, w):
            return w if bull else (-w if bear else 0)
        score_raw = (f(ema_bull, ema_bear, self.w_ema) + f(super_bull, super_bear, self.w_st) + f(macd_bull, macd_bear, self.w_macd)
                     + f(rsi_bull, rsi_bear, self.w_rsi) + f(adx_bull, adx_bear, self.w_adx) + f(vwap_bull, vwap_bear, self.w_vwap)
                     + f(bb_bull, bb_bear, self.w_bb) + f(stoch_bull, stoch_bear, self.w_stoch) + f(obv_bull, obv_bear, self.w_obv) + atr_score)
        score = div(score_raw, total_weight) * 100.0 if total_weight > 0 else 0.0
        long_signal = score >= self.long_threshold and ema_bull and super_bull and adx > self.adx_min and atr_active
        short_signal = score <= self.short_threshold and ema_bear and super_bear and adx > self.adx_min and atr_active
        exit_long = score < self.exit_threshold
        exit_short = score > -self.exit_threshold
        if long_signal and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_signal and st.position_size >= 0:
            st.entry("Short", st.short)
        avg = st.position_avg_price
        st.exit("Long Exit", from_entry="Long", stop=avg - atr * self.stop_atr_mult, limit=avg + atr * self.take_atr_mult)
        st.exit("Short Exit", from_entry="Short", stop=avg + atr * self.stop_atr_mult, limit=avg - atr * self.take_atr_mult)
        if st.position_size > 0 and exit_long:
            st.close("Long")
        if st.position_size < 0 and exit_short:
            st.close("Short")
