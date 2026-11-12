"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTCUSDT 4H Breakout Retest Strategy - S/R + RSI/MACD/SMA Filter
Author       : Crypto_Andy_
Source URL   : https://www.tradingview.com/script/zMwHN2Uu-BTCUSDT-4H-Breakout-Retest-Strategy-S-R-RSI-MACD-SMA-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Support / resistance levels are either the manual input levels (from the "active from" date) or swing-pivot auto levels before it. A retest of the breakout zone (a bullish close above the zone after coming from above, without sweeping the floor) or a breakout above the resistance, with the RSI / MACD / SMA filters, enters long; a close through the structural break level enters short; a cooldown applies after each trade. The stop and target are percentages of the entry close and are placed with the entry.

Deviations from the original: none.
Not carried over: level plots, trade labels, risk lines and the blocked-signal markers (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, ta

LEVELS_FROM = 1789948800000     # timestamp("21 Sep 2026 00:00 +0000")


class BtcRetestBreakout(Script):
    TITLE = "BTCUSDT 4H Breakout Retest Strategy - S/R + RSI/MACD/SMA Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, margin_long=100, margin_short=100,
                    commission_type="percent", commission_value=0.04, pyramiding=0)
    SOURCE = {"id": "zMwHN2Uu", "author": "Crypto_Andy_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/zMwHN2Uu-BTCUSDT-4H-Breakout-Retest-Strategy-S-R-RSI-MACD-SMA-Filter"}

    def init(self):
        i = self.input
        g = "Risk"
        self.sl_perc = i.float(1.5, "Stop Loss %", minval=0.1, maxval=20.0, step=0.1, group=g) / 100.0
        self.tp_perc = i.float(3.0, "Take Profit %", minval=0.1, maxval=50.0, step=0.1, group=g) / 100.0
        self.cooldown_bars = i.int(6, "Cooldown between trades (bars)", minval=0, maxval=50, group=g)
        self.enable_longs = i.bool(True, "Enable longs", group=g)
        self.enable_shorts = i.bool(True, "Enable shorts", group=g)
        g = "Manual levels (structure as of 2026-10-02)"
        self.zone_top = i.float(85300.0, "Breakout zone top / range top", step=50.0, group=g)
        self.zone_bot = i.float(84500.0, "Breakout zone bottom", step=50.0, group=g)
        self.res_break = i.float(87400.0, "Breakout resistance (Sep 22-23 highs)", step=50.0, group=g)
        self.floor_level = i.float(83000.0, "Retest floor (key support)", step=50.0, group=g)
        self.break_level = i.float(82600.0, "Structural break (range low)", step=50.0, group=g)
        self.levels_from = i.time(LEVELS_FROM, "Manual levels active from", group=g)
        g = "Auto levels (history backtest)"
        self.auto_before = i.bool(True, "Backtest bars before the manual-levels date with swing-based auto levels", group=g)
        self.use_auto = i.bool(False, "Use auto levels on all bars (ignore manual levels)", group=g)
        self.pvt_len = i.int(5, "Pivot lookback (bars each side)", minval=2, maxval=30, group=g)
        self.auto_zone_perc = i.float(1.0, "Auto retest zone depth %", minval=0.1, maxval=10.0, step=0.1, group=g) / 100.0
        self.auto_floor_perc = i.float(2.7, "Auto retest floor distance %", minval=0.2, maxval=20.0, step=0.1, group=g) / 100.0
        g = "Indicators"
        self.rsi_len = i.int(14, "RSI length", minval=2, group=g)
        self.macd_fast = i.int(12, "MACD fast", minval=2, group=g)
        self.macd_slow = i.int(26, "MACD slow", minval=3, group=g)
        self.macd_sig = i.int(9, "MACD signal", minval=2, group=g)
        self.sma_fast_len = i.int(50, "SMA fast length", minval=2, group=g)
        self.sma_long_len = i.int(200, "SMA long length", minval=10, group=g)
        self.use_trend = i.bool(False, "Require trend side of SMA long", group=g)
        g = "Signal filters"
        self.rsi_pull_min = i.float(42.0, "Retest long: RSI min", group=g)
        self.rsi_pull_max = i.float(72.0, "Retest long: RSI max", group=g)
        self.rsi_break_min = i.float(55.0, "Breakout long: RSI min", group=g)
        self.rsi_break_max = i.float(80.0, "Breakout long: RSI max", group=g)
        self.rsi_short_min = i.float(20.0, "Breakdown short: RSI min", group=g)
        self.rsi_short_max = i.float(45.0, "Breakdown short: RSI max", group=g)
        self.max_ext_perc = i.float(6.0, "Max extension from SMA fast %", minval=0.5, maxval=40.0, step=0.5, group=g) / 100.0
        self.max_chase_perc = i.float(1.0, "Max close distance beyond trigger level %", minval=0.1, maxval=10.0, step=0.1, group=g) / 100.0
        self.sweep_lookback = i.int(6, "Retest: dip window (bars)", minval=1, maxval=50, group=g)
        self.prior_window = i.int(8, "Retest: prior window above the zone (bars)", minval=1, maxval=50, group=g)
        self.auto_res = NA
        self.auto_sup = NA
        self.auto_flip = NA
        self.last_trade_bar = NA

    def cross_up(self, lvl):
        return (not na(lvl)) and self.close > lvl and self.close[1] <= lvl

    def cross_dn(self, lvl):
        return (not na(lvl)) and self.close < lvl and self.close[1] >= lvl

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        rsi_val = ta.rsi(close, self.rsi_len)
        _, _, macd_hist = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_sig)
        sma_fast = ta.sma(close, self.sma_fast_len)
        sma_long = ta.sma(close, self.sma_long_len)
        hist_h = self.H("macd_hist")
        macd_hist_1 = hist_h[1]
        hist_h.set(macd_hist)
        ph = ta.pivothigh(high, self.pvt_len, self.pvt_len)
        pl = ta.pivotlow(low, self.pvt_len, self.pvt_len)
        if not na(ph):
            self.auto_res = ph
        if not na(pl):
            self.auto_sup = pl
        if self.cross_up(self.auto_res):
            self.auto_flip = self.auto_res
        auto_now = self.use_auto or (self.auto_before and self.time < self.levels_from)
        zone_top_u = self.auto_flip if auto_now else self.zone_top
        zone_bot_u = self.auto_flip * (1.0 - self.auto_zone_perc) if auto_now else self.zone_bot
        floor_u = self.auto_flip * (1.0 - self.auto_floor_perc) if auto_now else self.floor_level
        res1_u = NA if auto_now else self.zone_top
        res2_u = self.auto_res if auto_now else self.res_break
        break_u = self.auto_sup if auto_now else self.break_level
        in_window = auto_now or self.time >= self.levels_from
        sweep_low = ta.lowest(low, self.sweep_lookback)
        hi_h = self.H("prior_hi")
        prior_high_close = hi_h[self.sweep_lookback]
        hi_h.set(ta.highest(close, self.prior_window))
        zone_ok = (not na(zone_top_u)) and (not na(floor_u))
        retest_event = zone_ok and close > zone_top_u and close > open_ and (low <= zone_top_u or close[1] <= zone_top_u)
        came_from_above = zone_ok and (not na(prior_high_close)) and prior_high_close > zone_top_u
        not_collapsed = zone_ok and sweep_low >= floor_u
        brk1 = self.cross_up(res1_u)
        brk2 = self.cross_up(res2_u)
        breakout_event = brk1 or brk2
        breakout_lvl = res2_u if brk2 else res1_u
        breakdown_event = self.cross_dn(break_u)
        macd_up = macd_hist > 0 or macd_hist > macd_hist_1
        retest_mom = rsi_val > self.rsi_pull_min and rsi_val < self.rsi_pull_max and macd_up
        break_mom = rsi_val > self.rsi_break_min and rsi_val < self.rsi_break_max and macd_hist > 0 and (na(sma_fast) or close > sma_fast)
        short_mom = rsi_val > self.rsi_short_min and rsi_val < self.rsi_short_max and macd_hist < 0 and (na(sma_fast) or close < sma_fast)
        not_ext_up = na(sma_fast) or close < sma_fast * (1.0 + self.max_ext_perc)
        not_ext_dn = na(sma_fast) or close > sma_fast * (1.0 - self.max_ext_perc)
        trend_long_ok = (not self.use_trend) or ((not na(sma_long)) and close > sma_long)
        trend_short_ok = (not self.use_trend) or ((not na(sma_long)) and close < sma_long)
        chase_retest_ok = (not na(zone_top_u)) and close <= zone_top_u * (1.0 + self.max_chase_perc)
        chase_break_ok = (not na(breakout_lvl)) and close <= breakout_lvl * (1.0 + self.max_chase_perc)
        chase_short_ok = (not na(break_u)) and close >= break_u * (1.0 - self.max_chase_perc)
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        if st.position_size == 0 and pos_prev != 0:
            self.last_trade_bar = self.bar_index
        cooldown_ok = na(self.last_trade_bar) or (self.bar_index - self.last_trade_bar) >= self.cooldown_bars
        can_trade = in_window and st.position_size == 0 and cooldown_ok and self.barstate.isconfirmed
        retest_long = self.enable_longs and can_trade and retest_event and came_from_above and not_collapsed and retest_mom and not_ext_up and chase_retest_ok and trend_long_ok
        break_long = self.enable_longs and can_trade and (not retest_long) and breakout_event and break_mom and not_ext_up and chase_break_ok and trend_long_ok
        long_signal = retest_long or break_long
        short_signal = self.enable_shorts and can_trade and (not long_signal) and breakdown_event and short_mom and not_ext_dn and chase_short_ok and trend_short_ok
        if long_signal:
            sl_price = close * (1.0 - self.sl_perc)
            tp_price = close * (1.0 + self.tp_perc)
            self.last_trade_bar = self.bar_index
            st.entry("Long", st.long, comment="L retest" if retest_long else "L breakout")
            st.exit("Long exit", from_entry="Long", stop=sl_price, limit=tp_price, comment_loss="SL", comment_profit="TP")
        if short_signal:
            sl_price = close * (1.0 + self.sl_perc)
            tp_price = close * (1.0 - self.tp_perc)
            self.last_trade_bar = self.bar_index
            st.entry("Short", st.short, comment="S breakdown")
            st.exit("Short exit", from_entry="Short", stop=sl_price, limit=tp_price, comment_loss="SL", comment_profit="TP")
