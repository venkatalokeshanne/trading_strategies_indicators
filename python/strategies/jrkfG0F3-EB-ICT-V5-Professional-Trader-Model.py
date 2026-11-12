"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EB ICT Gold V5 Pro Premium Sell
Author       : robmagnaye14
Source URL   : https://www.tradingview.com/script/jrkfG0F3-EB-ICT-V5-Professional-Trader-Model
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A liquidity sweep of the previous N-bar low (high) that closes back inside with a rejection wick, optionally with the EMA trend, RSI, ADX, daily-bias and killzone filters and a cooldown between signals, enters at the close with the stop at the lowest low (highest high)
of the last bars and a reward / risk target; a "premium sell" (a bearish rejection sweep above the fast EMA) is a second short trigger. The bracket is placed with the entry.

Deviations from the original: none.
Not carried over: sweep labels, WAIT dots and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class EbIctGold(Script):
    TITLE = "EB ICT Gold V5 Pro Premium Sell"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=3000, default_qty_type="percent_of_equity", default_qty_value=1, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "jrkfG0F3", "author": "robmagnaye14", "licence": "not stated",
              "url": "https://www.tradingview.com/script/jrkfG0F3-EB-ICT-V5-Professional-Trader-Model"}

    def init(self):
        i = self.input
        self.rr = i.float(1.0, "Risk Reward", step=0.1)
        self.liq_lookback = i.int(10, "Liquidity Lookback", minval=3)
        self.sl_lookback = i.int(5, "SL Lookback", minval=3)
        self.signal_cooldown = i.int(8, "Signal Cooldown Bars", minval=1)
        self.ema_fast_len = i.int(50, "EMA Fast")
        self.ema_slow_len = i.int(200, "EMA Slow")
        self.rsi_len = i.int(14, "RSI Length")
        self.adx_len = i.int(14, "ADX Length")
        self.min_adx = i.float(18, "Min ADX")
        self.entry_mode = i.string("Balanced", "Entry Frequency Mode", options=["Strict", "Balanced", "Aggressive"])
        self.use_daily_bias = i.bool(False, "Use Daily Bias")
        self.use_trend_filter = i.bool(True, "Use EMA Trend")
        self.use_rsi_filter = i.bool(False, "Use RSI Momentum")
        self.use_adx_filter = i.bool(False, "Use ADX Filter")
        self.use_session = i.bool(False, "Trade NY Killzone Only")
        self.use_premium_sell = i.bool(True, "Use Premium Sell Above EMA")
        self.ny_killzone = i.session("0700-1100", "NY Killzone")
        self.last_buy_bar = NA
        self.last_sell_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        in_killzone = not na(self.time_fn(None, self.ny_killzone, "America/New_York"))
        session_ok = (not self.use_session) or in_killzone
        pdh = self.security(None, "D", lambda v: v.high[1])
        pdl = self.security(None, "D", lambda v: v.low[1])
        pdc = self.security(None, "D", lambda v: v.close[1])
        pd_mid = (pdh + pdl) / 2
        bull_bias = pdc > pd_mid
        bear_bias = pdc < pd_mid
        buy_bias_ok = (not self.use_daily_bias) or bull_bias
        sell_bias_ok = (not self.use_daily_bias) or bear_bias
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        ef_h = self.H("ef")
        ema_fast_3 = ef_h[3]
        ef_h.set(ema_fast)
        rsi = ta.rsi(close, self.rsi_len)
        _plus_di, _minus_di, adx = ta.dmi(self.adx_len, self.adx_len)
        atr = ta.atr(14)
        trend_buy = close > ema_fast and ema_fast > ema_slow
        trend_sell = close < ema_fast and ema_fast < ema_slow
        ema_slope_buy = ema_fast > ema_fast_3
        ema_slope_sell = ema_fast < ema_fast_3
        rsi_buy = rsi > 50 and rsi < 75
        rsi_sell = rsi < 50 and rsi > 25
        adx_ok = adx >= self.min_adx
        trend_buy_ok = (not self.use_trend_filter) or trend_buy
        trend_sell_ok = (not self.use_trend_filter) or trend_sell
        rsi_buy_ok = (not self.use_rsi_filter) or rsi_buy
        rsi_sell_ok = (not self.use_rsi_filter) or rsi_sell
        adx_filter_ok = (not self.use_adx_filter) or adx_ok
        sweep_atr = 0.45 if self.entry_mode == "Strict" else (0.25 if self.entry_mode == "Balanced" else 0.10)
        wick_factor = 1.5 if self.entry_mode == "Strict" else (1.0 if self.entry_mode == "Balanced" else 0.5)
        need_slope = True if self.entry_mode == "Strict" else (True if self.entry_mode == "Balanced" else False)
        lh_h, ll_h = self.H("lh"), self.H("ll")
        liq_high = lh_h[1]
        liq_low = ll_h[1]
        lh_h.set(ta.highest(high, self.liq_lookback))
        ll_h.set(ta.lowest(low, self.liq_lookback))
        buy_sweep = low < liq_low and close > liq_low and (close - low) > atr * sweep_atr
        sell_sweep = high > liq_high and close < liq_high and (high - close) > atr * sweep_atr
        candle_body = abs(close - open_)
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - low
        candle_range = high - low
        bull_reject = close > open_ and lower_wick > candle_body * wick_factor and close >= high - (candle_range * 0.40)
        bear_reject = close < open_ and upper_wick > candle_body * wick_factor and close <= low + (candle_range * 0.40)
        buy_cooldown_ok = na(self.last_buy_bar) or (self.bar_index - self.last_buy_bar > self.signal_cooldown)
        sell_cooldown_ok = na(self.last_sell_bar) or (self.bar_index - self.last_sell_bar > self.signal_cooldown)
        buy_signal = (session_ok and buy_sweep and bull_reject and buy_bias_ok and rsi_buy_ok and adx_filter_ok and ((not need_slope) or ema_slope_buy)
                      and buy_cooldown_ok and close > ema_fast and ema_fast > ema_slow and self.barstate.isconfirmed)
        trend_sell_signal = (session_ok and sell_sweep and bear_reject and sell_bias_ok and rsi_sell_ok and adx_filter_ok and ((not need_slope) or ema_slope_sell)
                             and sell_cooldown_ok and close < ema_fast and ema_fast < ema_slow and self.barstate.isconfirmed)
        premium_sell = (self.use_premium_sell and session_ok and sell_sweep and bear_reject and close > ema_fast and close < open_ and ema_slope_sell
                        and sell_cooldown_ok and self.barstate.isconfirmed)
        sell_signal = trend_sell_signal or premium_sell
        if buy_signal:
            self.last_buy_bar = self.bar_index
        if sell_signal:
            self.last_sell_bar = self.bar_index
        buy_sl = ta.lowest(low, self.sl_lookback)
        sell_sl = ta.highest(high, self.sl_lookback)
        buy_risk = close - buy_sl
        sell_risk = sell_sl - close
        buy_tp = close + buy_risk * self.rr
        sell_tp = close - sell_risk * self.rr
        if buy_signal and st.position_size == 0 and buy_risk > 0:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", "BUY", stop=buy_sl, limit=buy_tp)
        if sell_signal and st.position_size == 0 and sell_risk > 0:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", "SELL", stop=sell_sl, limit=sell_tp)
