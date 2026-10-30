"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Sell Strategy - Clean Entries v2 (Labelled)
Author       : PlusMongolia
Source URL   : https://www.tradingview.com/script/FW4sGvzj-PLUS-BTC-1-hour
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Short only: the smoothed Stochastic-RSI K line crossing under 80 within 10 bars of having crossed over
it, K under D, a quiet Williams-VIX-Fix bar (under 2), the close under the 240-minute EMA200 (request.security, lookahead off), the
08:00-22:00 session and a 10-bar cooldown open a short. strategy.exit("Exit") is re-issued on EVERY bar with the swing / ATR stop
and a 1.5 R target; once the trade is 0.8 R in profit it is re-issued on that bar only with the stop moved to break-even (or the
close + 1.5 ATR if lower), after which the next bar's unconditional call restores the normal stop - exactly as the code reads.

Deviations from the original: none.
Not carried over: the entry label (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, div, na, pmath, ta


class PlusBtcSell(Script):
    TITLE = "BTC Sell Strategy - Clean Entries v2 (Labelled)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "FW4sGvzj", "author": "PlusMongolia", "licence": "not stated",
              "url": "https://www.tradingview.com/script/FW4sGvzj-PLUS-BTC-1-hour"}

    def init(self):
        self.rsi_length = self.input.int(14, "RSI Length", group="Stoch RSI")
        self.stoch_length = self.input.int(14, "Stoch Length", group="Stoch RSI")
        self.stoch_k = self.input.int(3, "K Smoothing", group="Stoch RSI")
        self.stoch_d = self.input.int(3, "D Smoothing", group="Stoch RSI")
        self.ob_level = self.input.float(80, "Overbought Level", group="Stoch RSI")
        self.vix_length = self.input.int(22, "VIX Fix Length", group="VIX Fix")
        self.vix_threshold = self.input.float(2.0, "VIX Max (Grey)", group="VIX Fix")
        self.rr_primary = self.input.float(1.5, "RR Take Profit", group="Trade")
        self.atr_len = self.input.int(14, "ATR Length", group="Trade")
        self.atr_mult_sl = self.input.float(2.0, "ATR SL Mult", group="Trade")
        self.breakeven_r = self.input.float(0.8, "Move SL to BE at R", group="Trade")
        self.trail_atr = self.input.bool(True, "ATR Trailing after BE", group="Trade")
        self.trail_mult = self.input.float(1.5, "ATR Trail Mult", group="Trade")
        self.cooldown_bars = self.input.int(10, "Cooldown Bars", group="Trade")
        self.use_session = self.input.bool(True, "Limit to London/NY", group="Session")
        self.htf_tf = self.input.string("240", "HTF for Trend (min)", group="Trend")
        self.ema_len = self.input.int(200, "EMA Length (HTF)", group="Trend")
        self.last_trade_bar = NA
        self.moved_to_be = False

    def on_bar(self):
        highest_close = ta.highest(self.close, self.vix_length)
        vix_fix = div(highest_close - self.low, highest_close) * 100
        is_vix_grey = vix_fix < self.vix_threshold
        rsi_val = ta.rsi(self.close, self.rsi_length)
        stoch_raw = ta.stoch(rsi_val, rsi_val, rsi_val, self.stoch_length)
        k_line = S(ta.sma(stoch_raw, self.stoch_k))
        d_line = ta.sma(k_line.cur, self.stoch_d)
        was_previously_ob = ta.barssince(k_line[1] >= self.ob_level and k_line[2] < self.ob_level) <= 10
        cross_under = ta.crossunder(k_line.cur, self.ob_level)
        bear_confirm = k_line.cur < d_line
        is_double_top = was_previously_ob and cross_under and bear_confirm
        ema_htf = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.ema_len))
        trend_ok = self.close < ema_htf
        in_session = (not self.use_session) or (not na(self.time_fn(None, "0800-2200:1234567")))
        cooldown_ok = na(self.last_trade_bar) or (self.bar_index - self.last_trade_bar > self.cooldown_bars)
        entry_signal = is_double_top and is_vix_grey and trend_ok and in_session and cooldown_ok
        st = self.strategy
        if entry_signal:
            st.entry("Short", st.short)
            self.last_trade_bar = self.bar_index
        atr = ta.atr(self.atr_len)
        swing_sl = ta.highest(self.high, 5)
        stop_loss = pmath.max(swing_sl, self.close + self.atr_mult_sl * atr)
        risk_pts = stop_loss - self.close
        take_profit = self.close - self.rr_primary * risk_pts
        st.exit("Exit", from_entry="Short", stop=stop_loss, limit=take_profit)
        if st.position_size < 0:
            avg = st.position_avg_price
            r_now = div(avg - self.close, stop_loss - avg)
            if (not self.moved_to_be) and r_now >= self.breakeven_r:
                be_stop = avg
                new_stop = be_stop
                if self.trail_atr:
                    t_stop = self.close + self.trail_mult * atr
                    new_stop = pmath.min(be_stop, t_stop)
                st.exit("Exit", from_entry="Short", stop=new_stop, limit=take_profit)
                self.moved_to_be = True
        else:
            self.moved_to_be = False
