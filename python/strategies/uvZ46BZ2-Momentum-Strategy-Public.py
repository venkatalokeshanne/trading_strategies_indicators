"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB + RSI + Volume + EMA Trend + Smart ADX (Intraday + Dynamic SL + RR + Risk Cap)
Author       : chinmayp5394
Source URL   : https://www.tradingview.com/script/uvZ46BZ2-Momentum-Strategy-Public
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close at or beyond a Bollinger band that was inside on the previous close, with RSI beyond 60 / 40, above-average volume, the EMA200 side, ADX above 20 and
rising and the matching DI on top, enters at the next open. The signal candle's extreme is the stop (capped at 1.5% risk, refreshed only on a signal while flat) and the target is 2R; both exit
orders are rebuilt every bar from position_avg_price (na while flat) and all positions are closed from 15:15 exchange time.

Deviations from the original: none.
Not carried over: BB / EMA / ADX plots, labels and alertcondition (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, pmath, ta


class MomentumStrategyPublic(Script):
    TITLE = "BB + RSI + Volume + EMA Trend + Smart ADX (Intraday + Dynamic SL + RR + Risk Cap)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "uvZ46BZ2", "author": "chinmayp5394", "licence": "not stated",
              "url": "https://www.tradingview.com/script/uvZ46BZ2-Momentum-Strategy-Public"}

    def init(self):
        self.bb_length = self.input.int(20, "BB Length")
        self.bb_mult = self.input.float(2.0, "BB StdDev")
        self.rsi_length = self.input.int(14, "RSI Length")
        self.vol_length = self.input.int(20, "Volume MA Length")
        self.ema_length = self.input.int(200, "EMA Trend Length")
        self.adx_length = self.input.int(14, "ADX Length")
        self.adx_threshold = self.input.int(20, "ADX Threshold")
        self.max_risk_percent = self.input.float(1.5, "Max Risk % Cap")
        self.exit_hour = self.input.int(15, "Exit Hour")
        self.exit_minute = self.input.int(15, "Exit Minute")
        self.long_sl = NA
        self.short_sl = NA

    def on_bar(self):
        bb_basis = ta.sma(self.close, self.bb_length)
        bb_dev = self.bb_mult * ta.stdev(self.close, self.bb_length)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        close = S(self.close)
        prev_inside_upper = close[1] < bb_upper
        prev_inside_lower = close[1] > bb_lower
        rsi_value = ta.rsi(self.close, self.rsi_length)
        avg_volume = ta.sma(self.volume, self.vol_length)
        volume_confirm = self.volume > avg_volume
        ema_trend = ta.ema(self.close, self.ema_length)
        diplus, diminus, adx_value = ta.dmi(self.adx_length, self.adx_length)
        adx = S(adx_value)
        adx_rising = adx[0] > adx[1]
        strong_trend = adx[0] > self.adx_threshold
        bullish_trend = diplus > diminus
        bearish_trend = diminus > diplus
        buy_signal = (self.close >= bb_upper and prev_inside_upper and rsi_value > 60 and volume_confirm
                      and self.close > ema_trend and strong_trend and adx_rising and bullish_trend)
        sell_signal = (self.close <= bb_lower and prev_inside_lower and rsi_value < 40 and volume_confirm
                       and self.close < ema_trend and strong_trend and adx_rising and bearish_trend)
        st = self.strategy
        if buy_signal:
            st.entry("Buy", st.long)
        if sell_signal:
            st.entry("Sell", st.short)
        if buy_signal and st.position_size == 0:
            self.long_sl = float(self.low)
        if sell_signal and st.position_size == 0:
            self.short_sl = float(self.high)
        long_entry = st.position_avg_price
        long_risk_raw = long_entry - self.long_sl
        max_long_risk = long_entry * self.max_risk_percent / 100
        long_risk = pmath.min(long_risk_raw, max_long_risk)
        long_sl_final = long_entry - long_risk
        long_target = long_entry + (2 * long_risk)
        short_entry = st.position_avg_price
        short_risk_raw = self.short_sl - short_entry
        max_short_risk = short_entry * self.max_risk_percent / 100
        short_risk = pmath.min(short_risk_raw, max_short_risk)
        short_sl_final = short_entry + short_risk
        short_target = short_entry - (2 * short_risk)
        st.exit("Exit Buy", from_entry="Buy", stop=long_sl_final, limit=long_target)
        st.exit("Exit Sell", from_entry="Sell", stop=short_sl_final, limit=short_target)
        current_hour = self.hour(self.time)
        current_minute = self.minute(self.time)
        is_exit_time = current_hour == self.exit_hour and current_minute >= self.exit_minute
        if is_exit_time:
            st.close_all(comment="EOD Exit")
        self.plot(bb_basis, "BB Basis", color=color.orange)
        self.plot(ema_trend, "EMA 200", color=color.yellow, linewidth=2)
