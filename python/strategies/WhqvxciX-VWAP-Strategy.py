"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NYSE Open VWAP Reclaim + Pullback Hold (5/8/13 Curl) — Long & Short + Cross Filters
Author       : Neptuko
Source URL   : https://www.tradingview.com/script/WhqvxciX-VWAP-Strategy
Pine version : v5
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (stop entries, protective stop + target orders; intraday chart). The VWAP anchored to the 09:30 New York open is the reference: a close back above (below) it ("1-close+hold" or "2-closes"), curling 5/8/13 EMAs, an optional rising-volume hold candle that touches the VWAP inside the trade window
sets a pending long (short) with its entry stop one tick beyond the hold candle and its stop beyond the other side (maximum stop in ticks); chop (too many VWAP crosses in the session) stops new trades. The stop and an N-tick target are issued while the trade is open.
As written in the original, the whole strategy only acts on the current and previous trading day of the loaded history (showThisOrPrevSession is derived from last_bar_time).
Deviations from the original: none for the trading logic.
Not carried over: every plot and display feature (anchored-VWAP / opening-range / initial-balance levels, markers, the ES / NQ / YM / MAG 7 status panel which uses request.security on other symbols), which do not feed any order.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta

MS_IN_DAY = 24 * 60 * 60 * 1000


class NyseOpenVwapReclaim(Script):
    TITLE = "NYSE Open VWAP Reclaim + Pullback Hold (5/8/13 Curl) — Long & Short + Cross Filters"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, calc_on_every_tick=True, commission_type="cash_per_contract", commission_value=0)
    SOURCE = {"id": "WhqvxciX", "author": "Neptuko", "licence": "Mozilla Public License 2.0", "url": "https://www.tradingview.com/script/WhqvxciX-VWAP-Strategy"}

    def init(self):
        i = self.input
        self.tz = i.string("America/New_York", "Time Zone")
        self.rth_session = i.session("0930-1600", "RTH Session (NYSE Open VWAP Anchor)")
        self.trade_session = i.session("0945-1100", "Trade Window (execute trades only in this window)")
        self.ema_fast_len = i.int(5, "EMA Fast", minval=1)
        self.ema_mid_len = i.int(8, "EMA Mid", minval=1)
        self.ema_slow_len = i.int(13, "EMA Slow", minval=1)
        self.touch_buffer_ticks = i.int(2, "VWAP Touch Buffer (ticks)", minval=0)
        self.use_vol_confirm = i.bool(True, "Require Rising Volume on Hold Candle")
        self.reclaim_mode = i.string("1-close+hold", "Reclaim Definition", options=["2-closes", "1-close+hold"])
        self.stop_buffer_ticks = i.int(2, "Stop Buffer Beyond Setup Extreme (ticks)", minval=0)
        self.max_stop_ticks = i.int(40, "Max Stop (ticks) — cancel if larger", minval=1)
        self.take_profit_ticks = i.int(40, "Take Profit (ticks)", minval=1)
        self.cross_by = i.string("Close", "Cross Detection", options=["Close", "Wick"])
        self.max_vwap_crosses = i.int(4, "Max NYSE Open VWAP Crosses (no new trades after)", minval=0)
        self.cum_pv = NA
        self.cum_v = NA
        self.vwap_cross_count = 0
        self.below_count = 0
        self.above_count = 0
        self.reclaimed_long = False
        self.reclaimed_short = False
        self.pending_long = False
        self.long_setup_high = NA
        self.long_setup_low = NA
        self.pending_short = False
        self.short_setup_high = NA
        self.short_setup_low = NA

    def trade_day_start(self, t):
        tz = self.tz
        y, m, d, h = self.year(t, tz), self.month(t, tz), self.dayofmonth(t, tz), self.hour(t, tz)
        today1800 = self.timestamp(tz, y, m, d, 18, 0)
        return today1800 if h >= 18 else today1800 - MS_IN_DAY

    def on_bar(self):
        st = self.strategy
        close, high, low, volume = self.close, self.high, self.low, self.volume
        tz = self.tz
        in_rth = self.time_in_session(self.rth_session, tz)
        in_trade = self.time_in_session(self.trade_session, tz)
        rth_h = self.H("in_rth")
        in_rth_1 = rth_h[1] == 1.0
        rth_h.set(1.0 if in_rth else 0.0)
        is_new_rth = in_rth and not in_rth_1
        latest_trade_day_start = self.trade_day_start(self.last_bar_time)
        prev_trade_day_start = latest_trade_day_start - MS_IN_DAY
        bar_trade_day_start = self.trade_day_start(self.time)
        show_this_or_prev = bool(bar_trade_day_start == latest_trade_day_start or bar_trade_day_start == prev_trade_day_start)
        tick = self.syminfo.mintick
        buf = self.touch_buffer_ticks * tick
        tp = self.hlc3
        if is_new_rth:
            self.cum_pv = tp * volume
            self.cum_v = float(volume)
        elif in_rth:
            self.cum_pv += tp * volume
            self.cum_v += volume
        open_vwap = div(self.cum_pv, self.cum_v) if self.cum_v > 0 else NA
        vw_h, c_h, e5_h, e8_h, e13_h, v_h, ca_h, cb_h = (self.H(k) for k in ("open_vwap", "close", "ema5", "ema8", "ema13", "volume", "close_above", "close_below"))
        open_vwap_1, close_1, volume_1 = vw_h[1], c_h[1], v_h[1]
        ema5_1, ema8_1, ema13_1 = e5_h[1], e8_h[1], e13_h[1]
        close_above_1, close_below_1 = ca_h[1] == 1.0, cb_h[1] == 1.0
        ema5 = ta.ema(close, self.ema_fast_len)
        ema8 = ta.ema(close, self.ema_mid_len)
        ema13 = ta.ema(close, self.ema_slow_len)
        show_markers_rth = in_rth and show_this_or_prev
        cross_up_ta = ta.crossover(close, open_vwap)
        cross_down_ta = ta.crossunder(close, open_vwap)
        cross_up_close = bool(show_markers_rth and not na(open_vwap) and not is_new_rth and cross_up_ta)
        cross_down_close = bool(show_markers_rth and not na(open_vwap) and not is_new_rth and cross_down_ta)
        prev_above = close_1 > open_vwap_1
        prev_below = close_1 < open_vwap_1
        spans_vwap = low <= open_vwap and high >= open_vwap
        cross_up_wick = bool(show_markers_rth and not na(open_vwap) and not is_new_rth and spans_vwap and prev_below and close > open_vwap)
        cross_down_wick = bool(show_markers_rth and not na(open_vwap) and not is_new_rth and spans_vwap and prev_above and close < open_vwap)
        cross_up = cross_up_close if self.cross_by == "Close" else cross_up_wick
        cross_down = cross_down_close if self.cross_by == "Close" else cross_down_wick
        if is_new_rth:
            self.vwap_cross_count = 0
        elif cross_up or cross_down:
            self.vwap_cross_count += 1
        allow_new_trades = self.vwap_cross_count < self.max_vwap_crosses
        cancel_because_chop = not allow_new_trades
        ema_long_ok = bool((ema5 > ema8 and ema8 > ema13) and (ema5 > ema5_1 and ema8 > ema8_1 and ema13 > ema13_1))
        ema_short_ok = bool((ema5 < ema8 and ema8 < ema13) and (ema5 < ema5_1 and ema8 < ema8_1 and ema13 < ema13_1))
        close_above_vwap = bool(in_rth and not na(open_vwap) and close > open_vwap)
        close_below_vwap = bool(in_rth and not na(open_vwap) and close < open_vwap)
        self.below_count = self.below_count + 1 if close_below_vwap else 0
        self.above_count = self.above_count + 1 if close_above_vwap else 0
        accept_below_vwap = self.below_count >= 2
        accept_above_vwap = self.above_count >= 2
        reclaim_long_2closes = close_above_vwap and close_above_1
        reclaim_long_cross = close_above_vwap and (close_1 <= open_vwap_1)
        reclaim_long = reclaim_long_2closes if self.reclaim_mode == "2-closes" else (close_above_vwap and (close_above_1 or reclaim_long_cross))
        reclaim_short_2closes = close_below_vwap and close_below_1
        reclaim_short_cross = close_below_vwap and (close_1 >= open_vwap_1)
        reclaim_short = reclaim_short_2closes if self.reclaim_mode == "2-closes" else (close_below_vwap and (close_below_1 or reclaim_short_cross))
        vol_ok = (not self.use_vol_confirm) or (volume > volume_1)
        if is_new_rth:
            self.reclaimed_long = False
        elif accept_below_vwap:
            self.reclaimed_long = False
        elif reclaim_long:
            self.reclaimed_long = True
        if is_new_rth:
            self.reclaimed_short = False
        elif accept_above_vwap:
            self.reclaimed_short = False
        elif reclaim_short:
            self.reclaimed_short = True
        touched_long = bool(in_rth and not na(open_vwap) and low <= open_vwap + buf)
        touched_short = bool(in_rth and not na(open_vwap) and high >= open_vwap - buf)
        hold_candle_long = bool(show_this_or_prev and allow_new_trades and in_trade and self.reclaimed_long and ema_long_ok and touched_long and close > open_vwap and vol_ok)
        hold_candle_short = bool(show_this_or_prev and allow_new_trades and in_trade and self.reclaimed_short and ema_short_ok and touched_short and close < open_vwap and vol_ok)
        if is_new_rth:
            self.pending_long = False
            self.pending_short = False
            self.long_setup_high = NA
            self.long_setup_low = NA
            self.short_setup_high = NA
            self.short_setup_low = NA
        if hold_candle_long:
            self.pending_long = True
            self.long_setup_high = float(high)
            self.long_setup_low = float(low)
        if hold_candle_short:
            self.pending_short = True
            self.short_setup_high = float(high)
            self.short_setup_low = float(low)
        if self.pending_long and (accept_below_vwap or not ema_long_ok or not self.reclaimed_long or not in_trade or cancel_because_chop or not show_this_or_prev):
            self.pending_long = False
            self.long_setup_high = NA
            self.long_setup_low = NA
        if self.pending_short and (accept_above_vwap or not ema_short_ok or not self.reclaimed_short or not in_trade or cancel_because_chop or not show_this_or_prev):
            self.pending_short = False
            self.short_setup_high = NA
            self.short_setup_low = NA
        stop_buf = self.stop_buffer_ticks * tick
        long_entry_stop = self.long_setup_high + tick
        long_stop_price = self.long_setup_low - stop_buf
        long_risk_ticks = pmath.round(div(long_entry_stop - long_stop_price, tick)) if (self.pending_long and not na(long_stop_price)) else NA
        long_risk_ok = bool(self.pending_long and (long_risk_ticks <= self.max_stop_ticks) and (long_entry_stop > long_stop_price))
        short_entry_stop = self.short_setup_low - tick
        short_stop_price = self.short_setup_high + stop_buf
        short_risk_ticks = pmath.round(div(short_stop_price - short_entry_stop, tick)) if (self.pending_short and not na(short_stop_price)) else NA
        short_risk_ok = bool(self.pending_short and (short_risk_ticks <= self.max_stop_ticks) and (short_stop_price > short_entry_stop))
        pos = st.position_size
        if pos == 0 and show_this_or_prev and allow_new_trades and in_trade:
            if self.pending_long and long_risk_ok:
                st.entry("L", st.long, stop=long_entry_stop)
            if self.pending_short and short_risk_ok:
                st.entry("S", st.short, stop=short_entry_stop)
        if pos > 0:
            tp_l = st.position_avg_price + (self.take_profit_ticks * tick)
            st.exit("L-exit", "L", stop=long_stop_price, limit=tp_l)
        if pos < 0:
            tp_s = st.position_avg_price - (self.take_profit_ticks * tick)
            st.exit("S-exit", "S", stop=short_stop_price, limit=tp_s)
        vw_h.set(open_vwap)
        c_h.set(close)
        e5_h.set(ema5)
        e8_h.set(ema8)
        e13_h.set(ema13)
        v_h.set(volume)
        ca_h.set(1.0 if close_above_vwap else 0.0)
        cb_h.set(1.0 if close_below_vwap else 0.0)
