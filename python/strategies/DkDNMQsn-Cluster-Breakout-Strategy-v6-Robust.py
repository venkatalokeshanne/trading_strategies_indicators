"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Cluster Breakout Strategy v8 (Partial+BE)
Author       : ruchiragrawal
Source URL   : https://www.tradingview.com/script/DkDNMQsn-Cluster-Breakout-Strategy-v6-Robust
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A tight, volatility-contracting price cluster defines a box; a close beyond it by an ATR buffer with a strong close, volume confirmation and an optional trend filter inside the session enters at the close with fixed-percentage levels. Half the position is closed at the first target, then the stop moves to the break-even level and the second target applies; a maximum holding time, the end of the session and a re-entry cooldown also apply.

Deviations from the original: none.
Not carried over: box lines, trade labels, alerts and the pending-reason bookkeeping used only for them.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class ClusterBreakout(Script):
    TITLE = "Cluster Breakout Strategy v8 (Partial+BE)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=2, process_orders_on_close=True, slippage=2,
                    commission_type="percent", commission_value=0.02)
    SOURCE = {"id": "DkDNMQsn", "author": "ruchiragrawal", "licence": "not stated",
              "url": "https://www.tradingview.com/script/DkDNMQsn-Cluster-Breakout-Strategy-v6-Robust"}

    def init(self):
        i = self.input
        g = "Cluster Detection"
        self.cluster_len = i.int(10, "Cluster lookback (bars)", group=g)
        self.atr_len_c = i.int(14, "ATR length (for cluster sizing)", group=g)
        self.tightness_atr = i.float(2.0, "Cluster tightness (range <= ATR x)", group=g)
        self.require_contraction = i.bool(True, "Require volatility to be contracting", group=g)
        self.contraction_lookback = i.int(20, "Contraction comparison lookback", group=g)
        g = "Breakout Confirmation"
        self.break_buffer_atr = i.float(0.1, "Breakout buffer (ATR x)", group=g)
        self.use_strong_close = i.bool(True, "Require strong close on breakout bar", group=g)
        self.strong_close_pct = i.float(0.6, "Strong-close threshold (0-1)", group=g)
        self.use_vol_confirm = i.bool(True, "Confirm with volume (auto-off if none)", group=g)
        self.vol_mult = i.float(1.3, "Breakout volume x average", group=g)
        self.vol_avg_len = i.int(20, "Volume average length", group=g)
        g = "Session"
        self.use_session = i.bool(True, "Restrict entries to session", group=g)
        self.sess = i.session("0915-1530", "Session (HHMM-HHMM)", group=g)
        self.tz = i.string("Asia/Kolkata", "Timezone", group=g)
        self.exit_eod = i.bool(True, "Close open trade at session end", group=g)
        self.max_trades_per_day = i.int(3, "Max entries per day", group=g)
        g = "Exit Rules"
        self.order_size = i.int(2, "Order size (must be even for 50% partial)", group=g, minval=2)
        self.sl_pct = i.float(0.5, "Initial stop-loss %", group=g, minval=0.05)
        self.tp1_pct = i.float(1.0, "First target % (50% closed here)", group=g, minval=0.1)
        self.tp2_mult = i.float(2.0, "Second target multiplier (x first target)", group=g)
        self.be_sl_pct = i.float(0.5, "Breakeven trail SL (% above entry for remaining)", group=g)
        self.use_max_hold = i.bool(True, "Use hard max-hold (bars)", group=g)
        self.max_hold_bars = i.int(20, "Max hold (bars) — closes everything", group=g)
        self.cooldown_bars = i.int(5, "Re-entry cooldown (bars after an exit)", group="Risk")
        g = "Trend Filter"
        self.use_trend_filter = i.bool(False, "Use trend filter (200 EMA + ADX)", group=g)
        self.ema_len = i.int(200, "EMA length", group=g)
        self.adx_len = i.int(14, "ADX length", group=g)
        self.adx_min = i.float(20, "Minimum ADX", group=g)
        self.box_top = NA
        self.box_bottom = NA
        self.box_active = False
        self.trades_today = 0
        self.last_exit_bar = NA
        self.tp1 = NA
        self.tp2 = NA
        self.full_sl = NA
        self.be_sl = NA
        self.bars_in_trade = 0
        self.phase2 = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        atr = ta.atr(self.atr_len_c)
        atr_h = self.H("atr")
        atr_back = atr_h[self.contraction_lookback]
        atr_h.set(atr)
        cluster_high = ta.highest(high, self.cluster_len)
        cluster_low = ta.lowest(low, self.cluster_len)
        cluster_range = cluster_high - cluster_low
        is_tight = cluster_range <= atr * self.tightness_atr
        contracting = (not self.require_contraction) or (atr < atr_back)
        is_cluster = is_tight and contracting
        has_volume = (not na(self.volume)) and self.volume > 0
        vol_sma = ta.sma(self.volume, self.vol_avg_len)
        vol_ok = (not self.use_vol_confirm) or (not has_volume) or (self.volume > vol_sma * self.vol_mult)
        ema_trend = ta.ema(close, self.ema_len)
        high_1, low_1 = high[1], low[1]
        up_move = high - high_1
        down_move = low_1 - low
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
        tr_rma = ta.rma(ta.tr(True), self.adx_len)
        plus_di = 100 * div(ta.rma(plus_dm, self.adx_len), tr_rma)
        minus_di = 100 * div(ta.rma(minus_dm, self.adx_len), tr_rma)
        dx = 100 * div(abs(plus_di - minus_di), plus_di + minus_di)
        adx_val = ta.rma(dx, self.adx_len)
        trend_long_ok = (not self.use_trend_filter) or (close > ema_trend and adx_val > self.adx_min)
        trend_short_ok = (not self.use_trend_filter) or (close < ema_trend and adx_val > self.adx_min)
        bt_h, bb_h, bu_h = self.H("box_top"), self.H("box_bottom"), self.H("buffer")
        box_top_1, box_bottom_1, buffer_1 = bt_h[1], bb_h[1], bu_h[1]
        new_cluster = is_cluster and (self.box_top != cluster_high or self.box_bottom != cluster_low or not self.box_active)
        if new_cluster:
            self.box_top = cluster_high
            self.box_bottom = cluster_low
            self.box_active = True
        bt_h.set(self.box_top)
        bb_h.set(self.box_bottom)
        session_now = not na(self.time_fn(None, self.sess, self.tz))
        in_session = (not self.use_session) or session_now
        if ta.change(self.time_fn("D")) != 0:
            self.trades_today = 0
        in_cooldown = (not na(self.last_exit_bar)) and (self.bar_index - self.last_exit_bar) < self.cooldown_bars
        bar_range = high - low
        close_pos = div(close - low, bar_range) if bar_range > 0 else 0.5
        strong_long = (not self.use_strong_close) or close_pos >= self.strong_close_pct
        strong_short = (not self.use_strong_close) or close_pos <= (1 - self.strong_close_pct)
        buffer = atr * self.break_buffer_atr
        bu_h.set(buffer)
        close_1 = close[1]
        long_break = self.box_active and close > self.box_top + buffer and close_1 <= box_top_1 + buffer_1
        short_break = self.box_active and close < self.box_bottom - buffer and close_1 >= box_bottom_1 - buffer_1
        can_trade = in_session and self.trades_today < self.max_trades_per_day and not in_cooldown
        long_signal = long_break and can_trade and trend_long_ok and vol_ok and strong_long
        short_signal = short_break and can_trade and trend_short_ok and vol_ok and strong_short
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        half_qty = pmath.floor(self.order_size / 2)
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long, qty=self.order_size)
            self.bars_in_trade = 0
            self.phase2 = False
            self.full_sl = close * (1 - self.sl_pct / 100)
            self.tp1 = close * (1 + self.tp1_pct / 100)
            self.tp2 = close * (1 + self.tp1_pct * self.tp2_mult / 100)
            self.be_sl = close * (1 + self.be_sl_pct / 100)
            self.trades_today = self.trades_today + 1
        if short_signal and st.position_size == 0:
            st.entry("Short", st.short, qty=self.order_size)
            self.bars_in_trade = 0
            self.phase2 = False
            self.full_sl = close * (1 + self.sl_pct / 100)
            self.tp1 = close * (1 - self.tp1_pct / 100)
            self.tp2 = close * (1 - self.tp1_pct * self.tp2_mult / 100)
            self.be_sl = close * (1 - self.be_sl_pct / 100)
            self.trades_today = self.trades_today + 1
        if st.position_size > 0:
            self.bars_in_trade = self.bars_in_trade + 1
            if (not self.phase2) and close >= self.tp1:
                st.close("Long", qty=half_qty, comment="TP1-50%")
                self.phase2 = True
            active_sl = self.be_sl if self.phase2 else self.full_sl
            active_tp = self.tp2 if self.phase2 else self.tp1
            st.exit("Long-exit", from_entry="Long", stop=active_sl, limit=active_tp)
            if self.use_max_hold and self.bars_in_trade >= self.max_hold_bars:
                st.close("Long", comment="Time exit")
        if st.position_size < 0:
            self.bars_in_trade = self.bars_in_trade + 1
            if (not self.phase2) and close <= self.tp1:
                st.close("Short", qty=half_qty, comment="TP1-50%")
                self.phase2 = True
            active_sl = self.be_sl if self.phase2 else self.full_sl
            active_tp = self.tp2 if self.phase2 else self.tp1
            st.exit("Short-exit", from_entry="Short", stop=active_sl, limit=active_tp)
            if self.use_max_hold and self.bars_in_trade >= self.max_hold_bars:
                st.close("Short", comment="Time exit")
        if self.exit_eod and (not session_now) and st.position_size != 0:
            st.close_all(comment="Session end flat")
        just_flat = st.position_size == 0 and pos_prev != 0
        if just_flat:
            self.last_exit_bar = self.bar_index
        if st.position_size == 0:
            self.tp1 = NA
            self.tp2 = NA
            self.full_sl = NA
            self.be_sl = NA
            self.bars_in_trade = 0
            self.phase2 = False
