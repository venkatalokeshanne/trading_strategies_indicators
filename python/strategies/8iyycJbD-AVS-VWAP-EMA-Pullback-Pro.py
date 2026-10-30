"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AVS VWAP EMA Pullback Pro
Author       : anna797979
Source URL   : https://www.tradingview.com/script/8iyycJbD-AVS-VWAP-EMA-Pullback-Pro
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). Inside the trading session (bar open time 07:00 - 20:00 exchange time), with the ADX above its minimum: a long needs the close over the VWAP, the fast EMA over the slow one and +DI over -DI, a low that dipped to within the pullback
percentage of the VWAP, a close back above the VWAP and the fast EMA and an RSI above the long level; shorts are the mirror image. When only one side signals and the position is not already in that direction, the entry is placed together with two exit orders of 50 % each at 1R and 2R,
both with the stop at the lower of the VWAP / slow EMA (higher for shorts) minus (plus) ATR x multiplier.
Deviations from the original: none.
Not carried over: the signal table, session / trend / ADX text and the last-signal level lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AvsVwapEmaPullback(Script):
    TITLE = "AVS VWAP EMA Pullback Pro"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="percent", commission_value=0.05, process_orders_on_close=True)
    SOURCE = {"id": "8iyycJbD", "author": "anna797979", "licence": "not stated", "url": "https://www.tradingview.com/script/8iyycJbD-AVS-VWAP-EMA-Pullback-Pro"}

    def init(self):
        i = self.input
        self.ema_fast_len = i.int(20, "Fast EMA", minval=1)
        self.ema_slow_len = i.int(50, "Slow EMA", minval=1)
        self.rsi_len = i.int(14, "RSI Length", minval=2)
        self.atr_len = i.int(14, "ATR Length", minval=2)
        self.dmi_len = i.int(14, "DMI Length", minval=2)
        self.adx_smooth = i.int(14, "ADX Smoothing", minval=2)
        self.adx_min = i.float(18, "Minimum ADX", step=0.5)
        self.pullback_pct = i.float(0.25, "VWAP Pullback %", step=0.05)
        self.rsi_bull_level = i.float(52, "RSI Long Level", step=0.5)
        self.rsi_bear_level = i.float(48, "RSI Short Level", step=0.5)
        self.sl_atr_mult = i.float(1.2, "SL ATR Multiplier", step=0.1)
        self.tp1_rr = i.float(1.0, "TP1 RR", step=0.1)
        self.tp2_rr = i.float(2.0, "TP2 RR", step=0.1)
        self.trade_session = i.session("0700-2000", "Trading Session")

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_session = self.time_in_session(self.trade_session)
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        rsi = ta.rsi(close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        vwap_val = ta.vwap(self.hlc3)
        plus_di, minus_di, adx_val = ta.dmi(self.dmi_len, self.adx_smooth)
        bull_trend = close > vwap_val and ema_fast > ema_slow and plus_di > minus_di
        bear_trend = close < vwap_val and ema_fast < ema_slow and minus_di > plus_di
        trend_ok = adx_val >= self.adx_min
        pull_long = bull_trend and self.low <= vwap_val * (1 + self.pullback_pct / 100)
        pull_short = bear_trend and self.high >= vwap_val * (1 - self.pullback_pct / 100)
        reclaim_long = close > vwap_val and close > ema_fast
        reject_short = close < vwap_val and close < ema_fast
        rsi_long_ok = rsi > self.rsi_bull_level
        rsi_short_ok = rsi < self.rsi_bear_level
        long_signal = in_session and trend_ok and pull_long and reclaim_long and rsi_long_ok
        short_signal = in_session and trend_ok and pull_short and reject_short and rsi_short_ok
        enter_long = long_signal and not short_signal
        enter_short = short_signal and not long_signal
        long_sl = long_tp1 = long_tp2 = short_sl = short_tp1 = short_tp2 = NA
        if enter_long:
            long_sl = pmath.min(vwap_val, ema_slow) - atr * self.sl_atr_mult
            long_risk = close - long_sl
            if long_risk > 0:
                long_tp1 = close + long_risk * self.tp1_rr
                long_tp2 = close + long_risk * self.tp2_rr
        if enter_short:
            short_sl = pmath.max(vwap_val, ema_slow) + atr * self.sl_atr_mult
            short_risk = short_sl - close
            if short_risk > 0:
                short_tp1 = close - short_risk * self.tp1_rr
                short_tp2 = close - short_risk * self.tp2_rr
        if enter_long and st.position_size <= 0 and not na(long_sl) and not na(long_tp1) and not na(long_tp2):
            st.entry("Long", st.long)
            st.exit("Long TP1", from_entry="Long", stop=long_sl, limit=long_tp1, qty_percent=50)
            st.exit("Long TP2", from_entry="Long", stop=long_sl, limit=long_tp2, qty_percent=50)
        if enter_short and st.position_size >= 0 and not na(short_sl) and not na(short_tp1) and not na(short_tp2):
            st.entry("Short", st.short)
            st.exit("Short TP1", from_entry="Short", stop=short_sl, limit=short_tp1, qty_percent=50)
            st.exit("Short TP2", from_entry="Short", stop=short_sl, limit=short_tp2, qty_percent=50)
