"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Auto Fib + EMA200 MTF [SamoAlgo] - FIXED
Author       : SamoAlgo
Source URL   : https://www.tradingview.com/script/VxbMvF97-Auto-Fib-EMA200-MTF-SamoAlgo-FIXED
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders processed at the signal bar's close). The last two confirmed pivots form a swing; a long (short) setup is armed when the swing is larger than a multiple of the ATR and expires after a number of bars.
It triggers when the close crosses the fib entry level (close above / below it) with the EMA agreement of the 1 / 5 / 15 / 60-minute timeframes (request.security, lookahead off), the session, ADX, cooldown, max-trades-per-day,
volatility and minimum-R:R filters passing and the position flat; the position is sized from the stop distance (percent of equity risked), with an ATR (or fib / fixed R:R) stop and target issued with the entry.
Deviations from the original: none (the chart must be a 1-minute chart: pinelib cannot request a timeframe below the chart's).
Not carried over: the open / close alerts, trade lines and labels and the background tints (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class AutoFibEmaMtf(Script):
    TITLE = "Auto Fib + EMA200 MTF [SamoAlgo] - FIXED"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent",
                    commission_value=0.02, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "VxbMvF97", "author": "SamoAlgo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/VxbMvF97-Auto-Fib-EMA200-MTF-SamoAlgo-FIXED"}

    def init(self):
        i = self.input
        g = "Swing / Fibonacci Detection"
        self.piv_len = i.int(2, "Pivot strength (bars left/right)", minval=2, maxval=30, group=g)
        self.entry_fib = i.float(0.7, "Entry Fib level", minval=0.1, maxval=0.99, step=0.001, group=g)
        self.target_fib = i.float(1.618, "Target Fib extension", minval=1.0, step=0.001, group=g)
        self.min_swing_atr = i.float(3.8, "Min swing size (x ATR)", minval=0.0, step=0.1, group=g)
        self.expiry_bars = i.int(33, "Setup expiry (bars)", minval=3, maxval=200, group=g)
        g = "Risk / Stop"
        self.use_atr_exit = i.bool(True, "Use ATR stop & target (instead of fib)", group=g)
        self.stop_atr = i.float(3, "ATR stop distance (x ATR)", minval=0.2, step=0.1, group=g)
        self.tp_atr = i.float(5, "ATR target distance (x ATR)", minval=0.2, step=0.1, group=g)
        self.stop_buf_atr = i.float(0, "Stop buffer beyond level 0 (x ATR)", minval=0.0, step=0.05, group=g)
        self.risk_pct = i.float(0.2, "Risk per trade (% equity)", minval=0.1, maxval=10, step=0.1, group=g)
        self.use_rr = i.bool(False, "Use fixed R:R instead of 1.618 target", group=g)
        self.rr_ratio = i.float(2.0, "R:R ratio", minval=0.5, step=0.1, group=g)
        g = "Filters"
        self.use_ema_filter = i.bool(True, "EMA200 multi-timeframe filter", group=g)
        self.ema_len = i.int(457, "EMA length", minval=10, group=g)
        self.min_tf_agree = i.int(4, "Min timeframes agreeing (out of 4)", minval=1, maxval=4, group=g)
        self.use_atr_filter = i.bool(False, "Volatility filter (avoid dead market)", group=g)
        self.atr_mult = i.float(0.3, "Min ATR vs its average", minval=0.1, step=0.1, group=g)
        self.use_session = i.bool(True, "Session filter (London + NY only)", group=g)
        self.sess_time = i.session("0800-2100", "Active session (exchange time)", group=g)
        self.min_bars_between = i.int(7, "Cooldown — min bars between trades", minval=0, maxval=500, group=g)
        self.avoid_same_swing = i.bool(True, "Avoid re-trading the same pivot swing", group=g)
        self.use_rr_filter = i.bool(True, "Minimum R:R filter", group=g)
        self.min_rr = i.float(1.5, "Min R:R ratio required to enter", minval=0.5, step=0.1, group=g)
        self.use_max_trades = i.bool(True, "Max trades per day filter", group=g)
        self.max_trades_day = i.int(2, "Max trades per day", minval=1, maxval=50, group=g)
        self.use_adx_filter = i.bool(True, "ADX trend-strength filter", group=g)
        self.adx_len = i.int(14, "ADX length", minval=2, group=g)
        self.adx_threshold = i.float(20, "Min ADX (trend strength)", minval=5, step=1, group=g)
        g = "Direction"
        self.allow_long = i.bool(True, "Allow Longs", group=g)
        self.allow_short = i.bool(True, "Allow Shorts", group=g)
        self.trades_today = 0
        self.last_trade_day = NA
        self.last_ph = NA
        self.last_ph_bar = NA
        self.last_pl = NA
        self.last_pl_bar = NA
        self.last_trade_bar = NA
        self.last_traded_ph_bar = NA
        self.last_traded_pl_bar = NA
        self.l_entry = self.l_stop = self.l_target = NA
        self.l_age = NA
        self.l_active = False
        self.s_entry = self.s_stop = self.s_target = NA
        self.s_age = NA
        self.s_active = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        atr = ta.atr(14)
        ema_1 = self.security(None, "1", lambda v: ta.ema(v.close, self.ema_len), lookahead=False)
        ema_5 = self.security(None, "5", lambda v: ta.ema(v.close, self.ema_len), lookahead=False)
        ema_15 = self.security(None, "15", lambda v: ta.ema(v.close, self.ema_len), lookahead=False)
        ema_60 = self.security(None, "60", lambda v: ta.ema(v.close, self.ema_len), lookahead=False)
        emas = (ema_1, ema_5, ema_15, ema_60)
        long_above = sum(1 for e in emas if close > e)
        short_below = sum(1 for e in emas if close < e)
        long_trend_ok = (not self.use_ema_filter) or long_above >= self.min_tf_agree
        short_trend_ok = (not self.use_ema_filter) or short_below >= self.min_tf_agree
        atr_avg = ta.sma(atr, 50)
        vol_ok = (not self.use_atr_filter) or atr > atr_avg * self.atr_mult
        in_session = (not self.use_session) or self.time_in_session(self.sess_time)
        _, _, adx_val = ta.dmi(self.adx_len, self.adx_len)
        trend_strong_ok = (not self.use_adx_filter) or adx_val > self.adx_threshold
        dom, mon = self.dayofmonth(), self.month()
        dom_h, mon_h = self.H("dom"), self.H("mon")
        dom_1, mon_1 = dom_h[1], mon_h[1]
        dom_h.set(dom)
        mon_h.set(mon)
        day_changed = na(self.last_trade_day) or dom != dom_1 or mon != mon_1
        if day_changed:
            self.trades_today = 0
            self.last_trade_day = dom
        max_trades_ok = (not self.use_max_trades) or self.trades_today < self.max_trades_day
        ph = ta.pivothigh(self.high, self.piv_len, self.piv_len)
        pl = ta.pivotlow(self.low, self.piv_len, self.piv_len)
        if not na(ph):
            self.last_ph = float(ph)
            self.last_ph_bar = self.bar_index - self.piv_len
        if not na(pl):
            self.last_pl = float(pl)
            self.last_pl_bar = self.bar_index - self.piv_len
        cooldown_ok = na(self.last_trade_bar) or (self.bar_index - self.last_trade_bar) >= self.min_bars_between
        new_long_swing_ok = (not self.avoid_same_swing) or na(self.last_traded_pl_bar) or self.last_pl_bar != self.last_traded_pl_bar
        new_short_swing_ok = (not self.avoid_same_swing) or na(self.last_traded_ph_bar) or self.last_ph_bar != self.last_traded_ph_bar
        flat = st.position_size == 0
        if self.allow_long and not na(self.last_pl) and not na(self.last_ph) and self.last_pl_bar < self.last_ph_bar and not self.l_active and flat and new_long_swing_ok:
            swing = self.last_ph - self.last_pl
            if swing > atr * self.min_swing_atr and swing > 0:
                self.l_entry = self.last_pl + swing * self.entry_fib
                self.l_stop = self.last_pl - atr * self.stop_buf_atr
                self.l_target = NA if self.use_rr else self.last_pl + swing * self.target_fib
                self.l_age = 0
                self.l_active = True
        if self.allow_short and not na(self.last_ph) and not na(self.last_pl) and self.last_ph_bar < self.last_pl_bar and not self.s_active and flat and new_short_swing_ok:
            swing = self.last_ph - self.last_pl
            if swing > atr * self.min_swing_atr and swing > 0:
                self.s_entry = self.last_ph - swing * self.entry_fib
                self.s_stop = self.last_ph + atr * self.stop_buf_atr
                self.s_target = NA if self.use_rr else self.last_ph - swing * self.target_fib
                self.s_age = 0
                self.s_active = True
        if self.l_active:
            self.l_age += 1
            if self.l_age > self.expiry_bars:
                self.l_active = False
        if self.s_active:
            self.s_age += 1
            if self.s_age > self.expiry_bars:
                self.s_active = False
        if self.use_atr_exit:
            sl_long, tp_long = close - atr * self.stop_atr, close + atr * self.tp_atr
            sl_short, tp_short = close + atr * self.stop_atr, close - atr * self.tp_atr
        else:
            sl_long = self.l_stop
            tp_long = close + (close - self.l_stop) * self.rr_ratio if self.use_rr else self.l_target
            sl_short = self.s_stop
            tp_short = close - (self.s_stop - close) * self.rr_ratio if self.use_rr else self.s_target
        rr_long = div(tp_long - close, abs(close - sl_long))
        rr_short = div(close - tp_short, abs(sl_short - close))
        rr_long_ok = (not self.use_rr_filter) or rr_long >= self.min_rr
        rr_short_ok = (not self.use_rr_filter) or rr_short >= self.min_rr
        long_trigger = bool(self.l_active and long_trend_ok and vol_ok and in_session and close > self.l_entry and flat and cooldown_ok
                            and trend_strong_ok and max_trades_ok and rr_long_ok)
        short_trigger = bool(self.s_active and short_trend_ok and vol_ok and in_session and close < self.s_entry and flat and cooldown_ok
                             and trend_strong_ok and max_trades_ok and rr_short_ok)
        if long_trigger:
            q = div(st.equity * self.risk_pct / 100.0, abs(close - sl_long))
            st.entry("L", st.long, qty=q)
            st.exit("L-x", "L", stop=sl_long, limit=tp_long)
            self.l_active = False
            self.last_trade_bar = self.bar_index
            self.last_traded_pl_bar = self.last_pl_bar
            self.trades_today += 1
        if short_trigger:
            q = div(st.equity * self.risk_pct / 100.0, abs(close - sl_short))
            st.entry("S", st.short, qty=q)
            st.exit("S-x", "S", stop=sl_short, limit=tp_short)
            self.s_active = False
            self.last_trade_bar = self.bar_index
            self.last_traded_ph_bar = self.last_ph_bar
            self.trades_today += 1
