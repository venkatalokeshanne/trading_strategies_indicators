"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 82 TRADE Strategy v8.4 (Pine v6 Ready)
Author       : mdfe3757
Source URL   : https://www.tradingview.com/script/RcF7t6Am
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A liquidity sweep of the latest confirmed swing low (high) - the bar trades through it, closes back above (below) it in the candle's direction - on a volume surge with a strong closing position, inside the Taipei killzone, opens a risk-sized
position at the next open with the stop one tick beyond the sweep bar. From the bar of the fill the stop is kept as an exit order: it moves to break-even and then trails an ATR multiple after `trailR` R, tightens on a climactic reversal bar, and a trade still under water after N bars is closed.

Deviations from the original: none.
Not carried over: the labels and the closed-trade report drawings (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class Trade82V84(Script):
    TITLE = "82 TRADE Strategy v8.4 (Pine v6 Ready)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2000000, commission_type="percent", commission_value=0.05, process_orders_on_close=False)
    SOURCE = {"id": "RcF7t6Am", "author": "mdfe3757", "licence": "not stated",
              "url": "https://www.tradingview.com/script/RcF7t6Am"}

    def init(self):
        g = "1. 進場核心 (PA + Volume)"
        self.piv_l = self.input.int(5, "Sweep 左側 K 數", group=g)
        self.piv_r = self.input.int(2, "Sweep 右側 K 數", group=g)
        self.vol_ma_len = self.input.int(20, "均量週期", group=g)
        self.vol_mult = self.input.float(1.2, "放量倍數", group=g, step=0.1)
        self.min_delta = self.input.float(0.65, "K線拒絕力道門檻 (0~1)", group=g, step=0.05)
        self.use_session = self.input.bool(True, "啟用 Killzones 時段", group=g)
        self.session_time = self.input.session("1500-0300", "允許進場時間 (台北)", group=g)
        g = "2. 風控與部位管理"
        self.risk_pct = self.input.float(1.0, "單筆風險 %(權益)", group=g, step=0.25) / 100
        self.max_pos_pct = self.input.float(100, "最大部位佔比 %", group=g, step=10) / 100
        g = "3. 動態追蹤與保護 (Smart Exit)"
        self.trail_r = self.input.float(1.5, "啟動追蹤/保本門檻 (R)", group=g, step=0.25)
        self.use_atr_trail = self.input.bool(True, "啟用 ATR 移動止損", group=g)
        self.atr_mult = self.input.float(3.0, "ATR 追蹤倍數", group=g, step=0.5)
        self.cap_exit_mode = self.input.string("收緊止損", "爆量反轉(CapExit)", options=["直接平倉", "收緊止損", "關閉"], group=g)
        self.cap_vol_mult = self.input.float(2.5, "爆量反轉倍數門檻", group=g, step=0.5)
        self.cap_min_r = self.input.float(1.0, "觸發爆量保護最低浮盈 (R)", group=g, step=0.25)
        self.use_time_stop = self.input.bool(True, "啟用虧損時間停損", group=g)
        self.time_stop_bars = self.input.int(15, "進場後 N 根未獲利平倉", group=g)
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.pending_sl_l = NA
        self.pending_sl_s = NA
        self.stop_price = NA
        self.entry_risk = NA
        self.entry_bar = NA
        self.trail_active = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        atr_v = ta.atr(14)
        ph = ta.pivothigh(high, self.piv_l, self.piv_r)
        pl = ta.pivotlow(low, self.piv_l, self.piv_r)
        if not na(ph):
            self.last_swing_high = ph
        if not na(pl):
            self.last_swing_low = pl
        bullish_sweep = (not na(self.last_swing_low)) and low < self.last_swing_low and close > self.last_swing_low and close > open_
        bearish_sweep = (not na(self.last_swing_high)) and high > self.last_swing_high and close < self.last_swing_high and close < open_
        in_session = (not self.use_session) or (not na(self.time_fn(None, self.session_time, "Asia/Taipei")))
        vol_ma = ta.sma(self.volume, self.vol_ma_len)
        is_high_vol = self.volume > self.vol_mult * vol_ma
        candle_range = high - low
        buy_pressure = 0 if candle_range == 0 else div(close - low, candle_range)
        sell_pressure = 0 if candle_range == 0 else div(high - close, candle_range)
        pa_ok_l = is_high_vol and buy_pressure >= self.min_delta
        pa_ok_s = is_high_vol and sell_pressure >= self.min_delta
        long_signal = bullish_sweep and in_session and pa_ok_l and st.position_size == 0
        short_signal = bearish_sweep and in_session and pa_ok_s and st.position_size == 0
        mintick = self.syminfo.mintick
        if long_signal:
            self.pending_sl_l = low - mintick
            est_risk = close - self.pending_sl_l
            if est_risk > 0:
                risk_qty = div(st.equity * self.risk_pct, est_risk)
                cap_qty = div(st.equity * self.max_pos_pct, close)
                qty = pmath.min(risk_qty, cap_qty)
                if qty > 0:
                    st.entry("Long", st.long, qty=qty)
        if short_signal:
            self.pending_sl_s = high + mintick
            est_risk = self.pending_sl_s - close
            if est_risk > 0:
                risk_qty = div(st.equity * self.risk_pct, est_risk)
                cap_qty = div(st.equity * self.max_pos_pct, close)
                qty = pmath.min(risk_qty, cap_qty)
                if qty > 0:
                    st.entry("Short", st.short, qty=qty)
        just_opened_long = st.position_size > 0 and (not na(pos_1)) and pos_1 <= 0
        just_opened_short = st.position_size < 0 and (not na(pos_1)) and pos_1 >= 0
        is_flat = st.position_size == 0
        if just_opened_long:
            self.stop_price = self.pending_sl_l
            self.entry_risk = st.position_avg_price - self.stop_price
            self.entry_bar = self.bar_index
            self.trail_active = False
        if just_opened_short:
            self.stop_price = self.pending_sl_s
            self.entry_risk = self.stop_price - st.position_avg_price
            self.entry_bar = self.bar_index
            self.trail_active = False
        if is_flat:
            self.stop_price = NA
            self.entry_risk = NA
            self.entry_bar = NA
            self.trail_active = False
        body = abs(close - open_)
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - low
        capit_long = self.volume > self.cap_vol_mult * vol_ma and upper_wick >= (body * 1.5)
        capit_short = self.volume > self.cap_vol_mult * vol_ma and lower_wick >= (body * 1.5)
        if st.position_size > 0:
            avg_px = st.position_avg_price
            if (not self.trail_active) and (close >= avg_px + self.entry_risk * self.trail_r):
                self.trail_active = True
            if self.trail_active:
                self.stop_price = pmath.max(self.stop_price, avg_px)
                if self.use_atr_trail:
                    self.stop_price = pmath.max(self.stop_price, close - atr_v * self.atr_mult)
            if capit_long and self.cap_exit_mode != "關閉":
                prof_r_l = div(close - avg_px, self.entry_risk)
                if prof_r_l >= self.cap_min_r:
                    if self.cap_exit_mode == "直接平倉":
                        st.close("Long", comment="爆量出貨")
                    else:
                        self.stop_price = pmath.max(self.stop_price, close - atr_v)
            if self.use_time_stop and (not na(self.entry_bar)) and (self.bar_index - self.entry_bar) >= self.time_stop_bars and close < avg_px:
                st.close("Long", comment="時間停損")
            st.exit("SL", from_entry="Long", stop=self.stop_price)
        elif st.position_size < 0:
            avg_px = st.position_avg_price
            if (not self.trail_active) and (close <= avg_px - self.entry_risk * self.trail_r):
                self.trail_active = True
            if self.trail_active:
                self.stop_price = pmath.min(self.stop_price, avg_px)
                if self.use_atr_trail:
                    self.stop_price = pmath.min(self.stop_price, close + atr_v * self.atr_mult)
            if capit_short and self.cap_exit_mode != "關閉":
                prof_r_s = div(avg_px - close, self.entry_risk)
                if prof_r_s >= self.cap_min_r:
                    if self.cap_exit_mode == "直接平倉":
                        st.close("Short", comment="爆量止跌")
                    else:
                        self.stop_price = pmath.min(self.stop_price, close + atr_v)
            if self.use_time_stop and (not na(self.entry_bar)) and (self.bar_index - self.entry_bar) >= self.time_stop_bars and close > avg_px:
                st.close("Short", comment="時間停損")
            st.exit("SL", from_entry="Short", stop=self.stop_price)
