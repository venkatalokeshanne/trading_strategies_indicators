"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Universal Aggressive Trend MACD v3.3 - Trailing TP
Author       : finnp17
Source URL   : https://www.tradingview.com/script/UVosPbFA-Universal-Aggressive-Trend-MACD-v3-3-Trailing-TP
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). While flat, a trend filter (close beyond a 99 EMA that also slopes the right way), an ADX filter and a volume filter must pass, the entry cool-down must be over, and either a fresh MACD cross (armed for N bars, MACD still on the right side) or a breakout of the previous N-bar high / low with MACD histogram support triggers the entry at the close. The emergency ATR stop is issued from the next bar on. Open trades are closed at the close by the trailing take-profit (peak profit % armed above a minimum, closed when the profit gives back a relative or point amount) and optionally by an opposite MACD cross.

Deviations from the original: none.
Not carried over: dashboard, entry-signal markers and the plotted stop / EMA lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class UniversalAggressiveTrendMACD(Script):
    TITLE = "Universal Aggressive Trend MACD v3.3 - Trailing TP"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "UVosPbFA", "author": "finnp17", "licence": "not stated",
              "url": "https://www.tradingview.com/script/UVosPbFA-Universal-Aggressive-Trend-MACD-v3-3-Trailing-TP"}

    def init(self):
        i = self.input
        g = "MACD Settings"
        self.fast_len = i.int(14, "MACD Fast Length", minval=1, group=g)
        self.slow_len = i.int(39, "MACD Slow Length", minval=1, group=g)
        self.sig_len = i.int(9, "MACD Signal Length", minval=1, group=g)
        g = "Entry Timing"
        self.use_arming = i.bool(True, "MACD Cross Arming nutzen", group=g)
        self.valid_bars = i.int(10, "MACD Cross gültig für X Kerzen", minval=1, maxval=50, group=g)
        self.use_cont = i.bool(True, "Continuation Entries nutzen", group=g)
        self.cont_len = i.int(5, "Continuation Breakout Lookback", minval=2, maxval=50, group=g)
        self.cooldown = i.int(3, "Cooldown nach Entry in Kerzen", minval=0, maxval=100, group=g)
        self.allow_longs = i.bool(True, "Longs erlauben", group=g)
        self.allow_shorts = i.bool(True, "Shorts erlauben", group=g)
        g = "Trend & Filter Settings"
        self.trend_len = i.int(99, "Trend EMA Length", minval=1, group=g)
        self.use_slope = i.bool(True, "EMA-Slope Filter nutzen", group=g)
        self.slope_bars = i.int(3, "EMA-Slope Lookback", minval=1, maxval=50, group=g)
        self.adx_len = i.int(11, "ADX Smoothing", minval=1, group=g)
        self.adx_thr = i.float(20.0, "ADX Trend Threshold", step=0.5, group=g)
        self.use_adx = i.bool(True, "ADX Filter nutzen", group=g)
        g = "Volume Settings"
        self.use_vol = i.bool(True, "Volumenfilter nutzen", group=g)
        self.vol_len = i.int(22, "Volume SMA Length", minval=1, group=g)
        self.vol_mult = i.float(0.6, "Volume Multiplier", step=0.1, group=g)
        g = "Risk Management"
        self.atr_len = i.int(18, "ATR Length", minval=1, group=g)
        self.emerg_mult = i.float(2.5, "ATR Emergency Stop Multiplier", step=0.1, group=g)
        self.use_opp_exit = i.bool(False, "Bei MACD-Gegencross schließen", group=g)
        g = "Trailing TP - Peak Profit Close"
        self.use_ttp = i.bool(True, "Trailing TP aktivieren", group=g)
        self.ttp_mode = i.string("Relativ vom Peak", "Trailing TP Modus", options=["Relativ vom Peak", "Prozentpunkte"], group=g)
        self.ttp_giveback = i.float(3.0, "Rücklauf vom höchsten Profit", step=0.1, minval=0.1, group=g)
        self.ttp_min = i.float(0.50, "Trailing TP aktiv ab Peak-Profit (%)", step=0.05, minval=0.0, group=g)
        self.last_bull = NA
        self.last_bear = NA
        self.last_entry = NA
        self.peak = NA
        self.armed = False
        self.long_stop = NA
        self.short_stop = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        fast_ema = ta.ema(close, self.fast_len)
        slow_ema = ta.ema(close, self.slow_len)
        macd = fast_ema - slow_ema
        sig = ta.ema(macd, self.sig_len)
        hist = macd - sig
        trend_ema = ta.ema(close, self.trend_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        vol_sma = ta.sma(self.volume, self.vol_len)
        atr = ta.atr(self.atr_len)
        te_h = self.H("trend_ema")
        te_back = te_h[self.slope_bars]
        te_h.set(trend_ema)
        slope_up = (not self.use_slope) or trend_ema > te_back
        slope_dn = (not self.use_slope) or trend_ema < te_back
        long_trend_ok = close > trend_ema and slope_up
        short_trend_ok = close < trend_ema and slope_dn
        adx_ok = (not self.use_adx) or adx > self.adx_thr
        vol_ok = (not self.use_vol) or self.volume > vol_sma * self.vol_mult
        market_ok = adx_ok and vol_ok
        bull_cross = ta.crossover(macd, sig)
        bear_cross = ta.crossunder(macd, sig)
        if bull_cross:
            self.last_bull = self.bar_index
        if bear_cross:
            self.last_bear = self.bar_index
        bull_fresh = (not self.use_arming) or (not na(self.last_bull) and self.bar_index - self.last_bull <= self.valid_bars and macd > sig)
        bear_fresh = (not self.use_arming) or (not na(self.last_bear) and self.bar_index - self.last_bear <= self.valid_bars and macd < sig)
        hh_h, ll_h = self.H("hh"), self.H("ll")
        highest_before, lowest_before = hh_h[1], ll_h[1]
        hh_h.set(ta.highest(self.high, self.cont_len))
        ll_h.set(ta.lowest(self.low, self.cont_len))
        long_cont = self.use_cont and macd > sig and hist > 0 and close > highest_before
        short_cont = self.use_cont and macd < sig and hist < 0 and close < lowest_before
        cooldown_ok = na(self.last_entry) or self.bar_index - self.last_entry >= self.cooldown
        flat = st.position_size == 0
        is_long = st.position_size > 0
        is_short = st.position_size < 0
        long_cond = self.allow_longs and flat and cooldown_ok and market_ok and long_trend_ok and (bull_fresh or long_cont)
        short_cond = self.allow_shorts and flat and cooldown_ok and market_ok and short_trend_ok and (bear_fresh or short_cont)
        cur_profit = 0.0
        if is_long and st.position_avg_price > 0:
            cur_profit = div(close - st.position_avg_price, st.position_avg_price) * 100.0
        if is_short and st.position_avg_price > 0:
            cur_profit = div(st.position_avg_price - close, st.position_avg_price) * 100.0
        if flat:
            self.peak = NA
            self.armed = False
            self.long_stop = NA
            self.short_stop = NA
        if not flat:
            self.peak = cur_profit if na(self.peak) else pmath.max(self.peak, cur_profit)
            if self.peak >= self.ttp_min:
                self.armed = True
        ttp_level = NA
        if self.armed and not na(self.peak):
            if self.ttp_mode == "Relativ vom Peak":
                ttp_level = self.peak * (1.0 - self.ttp_giveback / 100.0)
            else:
                ttp_level = self.peak - self.ttp_giveback
        ttp_exit = self.use_ttp and self.armed and not na(ttp_level) and cur_profit <= ttp_level
        opp_long = self.use_opp_exit and is_long and bear_cross
        opp_short = self.use_opp_exit and is_short and bull_cross
        if is_long and ttp_exit:
            st.close("Long", comment="Long Trailing TP")
        if is_short and ttp_exit:
            st.close("Short", comment="Short Trailing TP")
        if opp_long:
            st.close("Long", comment="Long MACD Reverse")
        if opp_short:
            st.close("Short", comment="Short MACD Reverse")
        if long_cond:
            st.entry("Long", st.long, comment="Long")
            self.long_stop = float(close - atr * self.emerg_mult)
            self.short_stop = NA
            self.peak = NA
            self.armed = False
            self.last_entry = self.bar_index
        if short_cond:
            st.entry("Short", st.short, comment="Short")
            self.short_stop = float(close + atr * self.emerg_mult)
            self.long_stop = NA
            self.peak = NA
            self.armed = False
            self.last_entry = self.bar_index
        if is_long and not na(self.long_stop):
            st.exit("Long Emergency SL", "Long", stop=self.long_stop)
        if is_short and not na(self.short_stop):
            st.exit("Short Emergency SL", "Short", stop=self.short_stop)
