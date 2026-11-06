"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strict Failed 2 + Daily Bias Only
Author       : not stated
Source URL   : https://www.tradingview.com/script/cgT9ys8s
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (orders at the bar's close: process_orders_on_close, 1 contract). A "failed 2" is a candle that ends a run of at least two same-colour candles, is not an inside bar, and probes beyond the previous ("mother") bar's extreme in the run's direction without closing outside it. The signal must agree with the daily bias - the same pattern evaluated on daily bars with request.security (lookahead off), where the previous run length comes from ta.barssince on the daily series - and, if the target (the mother bar's opposite extreme) is already passed, it is skipped. An entry carries a stop at the signal bar's extreme (plus the optional tick buffer) and a limit at the mother bar's other extreme.
Deviations from the original: none.
Not carried over: plots, shading and alert conditions.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na


class StrictFailed2(Script):
    TITLE = "Strict Failed 2 + Daily Bias Only"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "cgT9ys8s", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/cgT9ys8s"}

    def init(self):
        i = self.input
        self.signal_min_consecutive = i.int(2, "Minimum Consecutive Candles", minval=2)
        self.enable_failed2 = i.bool(True, "Enable Failed 2 Signals")
        self.use_confirmation = i.bool(True, "Use Bar Close Confirmation")
        self.use_daily_bias = i.bool(True, "Use Daily Failed 2 Bias")
        self.require_htf_bias = i.bool(True, "Require Daily Bias In Trade Direction")
        self.stop_buffer_ticks = i.int(0, "Stop Buffer (ticks)", minval=0)
        self.skip_if_target_passed = i.bool(True, "Skip if target already exceeded")
        self.up_streak = 0
        self.dn_streak = 0
        self.bull_state = {"prev_bearish": NA, "bs": NA}       # the daily function's own history (bearish[1], barssince[1])
        self.bear_state = {"prev_bullish": NA, "bs": NA}

    def _f_bull(self, v):
        s = self.bull_state
        close, open_, high, low = float(v.close), float(v.open), float(v.high), float(v.low)
        bearish = close < open_
        bullish = close > open_
        inside = high < v.high[1] and low > v.low[1]
        bs_prev = s["bs"]
        cur = 0 if (not bearish) else (NA if na(bs_prev) else bs_prev + 1)       # ta.barssince(not bearish)
        prev_streak = (bs_prev if s["prev_bearish"] is True else 0)
        s["prev_bearish"], s["bs"] = bearish, cur
        ended = (not na(prev_streak)) and prev_streak >= self.signal_min_consecutive and (not bearish) and prev_streak > 0
        mother_high, mother_low = v.high[1], v.low[1]
        return bool(ended and (not inside) and bullish and low < mother_low and high <= mother_high and close > mother_low and close < mother_high)

    def _f_bear(self, v):
        s = self.bear_state
        close, open_, high, low = float(v.close), float(v.open), float(v.high), float(v.low)
        bullish = close > open_
        bearish = close < open_
        inside = high < v.high[1] and low > v.low[1]
        bs_prev = s["bs"]
        cur = 0 if (not bullish) else (NA if na(bs_prev) else bs_prev + 1)       # ta.barssince(not bullish)
        prev_streak = (bs_prev if s["prev_bullish"] is True else 0)
        s["prev_bullish"], s["bs"] = bullish, cur
        ended = (not na(prev_streak)) and prev_streak >= self.signal_min_consecutive and (not bullish) and prev_streak > 0
        mother_high, mother_low = v.high[1], v.low[1]
        return bool(ended and (not inside) and bearish and high > mother_high and low >= mother_low and close < mother_high and close > mother_low)

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        high_1, low_1 = self.high[1], self.low[1]
        is_bull = close > open_
        is_bear = close < open_
        is_inside = high < high_1 and low > low_1
        mother_high, mother_low = high_1, low_1
        prev_up, prev_dn = self.up_streak, self.dn_streak
        if is_bull:
            self.dn_streak = 0
            self.up_streak = 1 if self.up_streak == 0 else self.up_streak + 1
        elif is_bear:
            self.up_streak = 0
            self.dn_streak = 1 if self.dn_streak == 0 else self.dn_streak + 1
        else:
            self.up_streak = 0
            self.dn_streak = 0
        streak_ended_bullish = prev_up >= self.signal_min_consecutive and (not is_bull) and prev_up > 0
        streak_ended_bearish = prev_dn >= self.signal_min_consecutive and (not is_bear) and prev_dn > 0
        bearish_failed2 = (self.enable_failed2 and streak_ended_bullish and (not is_inside) and is_bear and high > mother_high and low >= mother_low and close < mother_high and close > mother_low)
        bullish_failed2 = (self.enable_failed2 and streak_ended_bearish and (not is_inside) and is_bull and low < mother_low and high <= mother_high and close > mother_low and close < mother_high)
        signal_confirmed = True                     # barstate.ishistory or not useConfirmation or barstate.isconfirmed
        bullish_signal = signal_confirmed and bullish_failed2
        bearish_signal = signal_confirmed and bearish_failed2
        if self.use_daily_bias:
            daily_bull_f2 = self.security(None, "D", self._f_bull)
            daily_bear_f2 = self.security(None, "D", self._f_bear)
        else:
            daily_bull_f2 = daily_bear_f2 = False
        daily_bull_f2 = bool(daily_bull_f2) if not na(daily_bull_f2) else False
        daily_bear_f2 = bool(daily_bear_f2) if not na(daily_bear_f2) else False
        long_target = mother_high
        short_target = mother_low
        tick = self.syminfo.mintick
        long_stop = low - self.stop_buffer_ticks * tick
        short_stop = high + self.stop_buffer_ticks * tick
        valid_long_target = long_target > close
        valid_short_target = short_target < close
        long_bias_ok = (not self.require_htf_bias) or daily_bull_f2
        short_bias_ok = (not self.require_htf_bias) or daily_bear_f2
        take_long = bullish_signal and long_bias_ok and ((not self.skip_if_target_passed) or valid_long_target)
        take_short = bearish_signal and short_bias_ok and ((not self.skip_if_target_passed) or valid_short_target)
        if take_long:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=long_stop, limit=long_target)
        if take_short:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=short_stop, limit=short_target)
