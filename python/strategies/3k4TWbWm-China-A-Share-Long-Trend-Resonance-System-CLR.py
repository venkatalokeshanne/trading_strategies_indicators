"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : China A-Share Long Trend Resonance System (CLR System)
Author       : not stated
Source URL   : https://www.tradingview.com/script/3k4TWbWm
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (orders at the bar's close: process_orders_on_close). A long entry (100 % of equity) needs the daily Supertrend(10, 3, hl2) of the source (re-evaluated on daily bars, as request.security does) to be up, the close over the HMA(50), ADX(12) over its threshold, no entry within 5 bars of the last exit, and optionally a rising ADX, a rising HMA and a price acceleration (the high rose by more than half an ATR).
After the entry the first and second profit targets (1.5 and 3 x the ATR at entry above the entry price) each reduce 30 % of the position (strategy.close with qty_percent); the whole position is closed by the hard stop (2 x entry ATR), by the stage-1 early exit, by the Chandelier stop after the second target (highest close since then minus 3 x the 5-bar highest ATR) or by the chart-timeframe Supertrend turning down after the second target.
Deviations from the original: none.
Not carried over: the weekly HMA state (only feeds the panel), the dashboard panel, labels and plots.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


def _new_trend() -> dict:
    """The source's Supertrend state (up[1], dn[1], trend)."""
    return dict(up=NA, dn=NA, trend=1)


class ClrSystem(Script):
    TITLE = "China A-Share Long Trend Resonance System (CLR System)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=100, process_orders_on_close=True)
    SOURCE = {"id": "3k4TWbWm", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/3k4TWbWm"}

    def init(self):
        i = self.input
        self.atr_len = i.int(10, "ATR周期")
        self.factor = i.float(3.0, "Supertrend倍数")
        self.hma_len = i.int(50, "HMA周期")
        self.adx_len = i.int(12, "ADX周期")
        self.adx_th = i.int(17, "ADX阈值")
        self.use_adx_slope = i.bool(True, "ADX斜率过滤")
        self.use_hma_slope = i.bool(True, "HMA斜率过滤")
        self.use_price_accel = i.bool(True, "价格加速过滤")
        self.price_accel_factor = i.float(0.5, "价格加速ATR倍数")
        self.use_chandelier = i.bool(True, "启用吊灯止损")
        self.sl_r = i.float(2.0, "BUY-ATR止损")
        self.dynamic_r = i.float(3.0, "T2吊灯ATR倍数")
        self.atr_smooth_len = i.int(5, "吊灯ATR抗震荡周期")
        self.tp1_r = i.float(1.5, "TP1")
        self.tp2_r = i.float(3.0, "TP2")
        self.tp1_qty = i.float(30, "TP1减仓%")
        self.tp2_qty = i.float(30, "TP2减仓%")
        self.cool_bars = i.int(5, "冷却周期")
        self.chart_trend = _new_trend()
        self.daily_trend = _new_trend()
        self.last_exit_bar = NA
        self.entry_price = NA
        self.entry_atr = NA
        self.r = NA
        self.tp1_done = False
        self.tp2_done = False
        self.highest_since_t2 = NA

    def _trend_step(self, s, src, close, close_1, atr):
        up = src - self.factor * atr
        up1 = nz(s["up"], up)
        if close_1 > up1:
            up = pmath.max(up, up1)
        dn = src + self.factor * atr
        dn1 = nz(s["dn"], dn)
        if close_1 < dn1:
            dn = pmath.min(dn, dn1)
        if s["trend"] == -1 and close > dn1:
            s["trend"] = 1
        elif s["trend"] == 1 and close < up1:
            s["trend"] = -1
        s["up"], s["dn"] = up, dn
        return s["trend"]

    def _daily(self, v):
        atr = ta.atr(self.atr_len)
        return self._trend_step(self.daily_trend, (float(v.high) + float(v.low)) / 2, float(v.close), v.close[1], atr)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_adx, h_hma, h_pos, h_trend = self.H("adx"), self.H("hma"), self.H("pos"), self.H("trend")
        adx_1, hma_1, pos_1, trend_1 = h_adx[1], h_hma[1], h_pos[1], h_trend[1]
        high_1, low_1, close_1 = self.high[1], self.low[1], self.close[1]
        atr = ta.atr(self.atr_len)
        hma = ta.hma(close, self.hma_len)
        hma_up = hma > hma_1
        up_move = high - high_1
        down_move = low_1 - low
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0
        tr = pmath.max(pmath.max(high - low, abs(high - close_1)), abs(low - close_1))
        smooth_tr = ta.rma(tr, self.adx_len)
        smooth_plus = ta.rma(plus_dm, self.adx_len)
        smooth_minus = ta.rma(minus_dm, self.adx_len)
        plus_di = div(smooth_plus, smooth_tr) * 100
        minus_di = div(smooth_minus, smooth_tr) * 100
        dx = div(abs(plus_di - minus_di), plus_di + minus_di) * 100
        adx = ta.rma(dx, self.adx_len)
        adx_slope_up = adx > adx_1
        trend = self._trend_step(self.chart_trend, self.hl2, float(close), close_1, atr)
        sell_signal = trend == -1 and trend_1 == 1
        d_trend = self.security(None, "D", self._daily)
        cooling = (not na(self.last_exit_bar)) and (self.bar_index - self.last_exit_bar < self.cool_bars)
        price_accel = (high - high_1) > atr * self.price_accel_factor
        entry_trigger = d_trend == 1 and close > hma and adx > self.adx_th and not cooling
        if self.use_adx_slope:
            entry_trigger = entry_trigger and adx_slope_up
        if self.use_hma_slope:
            entry_trigger = entry_trigger and hma_up
        if self.use_price_accel:
            entry_trigger = entry_trigger and price_accel
        pos = st.position_size
        if entry_trigger and pos == 0:
            st.entry("LONG", st.long)
        is_long = pos > 0
        if st.opentrades > 0:
            self.entry_price = st.opentrades_entry_price(0)
        if is_long and (not na(pos_1)) and pos_1 == 0:
            self.entry_atr = float(atr)
        if not is_long:
            self.entry_atr = NA
        if is_long:
            self.r = div(close - self.entry_price, self.entry_atr)
        if not is_long:
            self.tp1_done = False
            self.tp2_done = False
        tp1_trig = is_long and high >= self.entry_price + self.tp1_r * self.entry_atr and not self.tp1_done
        tp2_trig = is_long and high >= self.entry_price + self.tp2_r * self.entry_atr and not self.tp2_done
        if tp1_trig:
            st.close("LONG", qty_percent=self.tp1_qty)
            self.tp1_done = True
        if tp2_trig:
            st.close("LONG", qty_percent=self.tp2_qty)
            self.tp2_done = True
        stage = 0 if not is_long else 1 if not self.tp1_done else 2 if not self.tp2_done else 3
        atr_smooth = ta.highest(ta.atr(self.atr_len), self.atr_smooth_len)
        if stage == 3:
            self.highest_since_t2 = float(close) if na(self.highest_since_t2) else pmath.max(self.highest_since_t2, close)
        else:
            self.highest_since_t2 = NA
        chandelier_stop = self.highest_since_t2 - self.dynamic_r * atr_smooth
        stop_price = self.entry_price - self.sl_r * self.entry_atr
        exit_stage1 = stage == 1 and self.r >= 2 and low < self.entry_price + 2 * self.entry_atr
        exit_stage2 = self.use_chandelier and stage == 3 and low <= chandelier_stop
        exit_stage3 = stage == 3 and sell_signal
        exit_now = (is_long and low < stop_price) or exit_stage1 or exit_stage2 or exit_stage3
        if exit_now:
            st.close("LONG")
            self.last_exit_bar = self.bar_index
        h_adx.set(adx)
        h_hma.set(hma)
        h_pos.set(pos)
        h_trend.set(trend)
