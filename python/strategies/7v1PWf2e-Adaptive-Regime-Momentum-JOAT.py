"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Adaptive Regime Momentum [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/7v1PWf2e-Adaptive-Regime-Momentum-JOAT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A composite moving average (the mean of an ALMA and a double-smoothed zero-lag EMA) must have risen (fallen) for N consecutive bars, with the close on the right side of it, a volume-RSI expansion and an RSI side filter, to enter at the next open; the ATR stop and target are re-issued every bar from the average entry price, and the trade is also closed when the close breaks the average by an ATR trail or the average turns.

Deviations from the original: none.
Not carried over: the smoothed-colour average, ATR shadow bands, labels and the performance table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, ta


class AdaptiveRegimeMomentum(Script):
    TITLE = "Adaptive Regime Momentum [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=5, commission_type="percent", commission_value=0.05,
                    initial_capital=10000, pyramiding=0)
    SOURCE = {"id": "7v1PWf2e", "author": "officialjackofalltrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7v1PWf2e-Adaptive-Regime-Momentum-JOAT"}

    def init(self):
        i = self.input
        g = "Signal 1 — Composite MA"
        self.ma_len = i.int(34, "MA Length", minval=5, maxval=200, group=g)
        self.alma_off = i.float(0.85, "ALMA Offset", minval=0.0, maxval=1.0, step=0.01, group=g)
        self.alma_sig = i.float(6.0, "ALMA Sigma", minval=1.0, maxval=20.0, step=0.5, group=g)
        self.slope_confirm = i.int(3, "Slope Confirm Bars", minval=1, maxval=10, group=g)
        g = "Signal 3 — Volume RSI"
        self.vol_rsi_len = i.int(8, "Volume RSI Length", minval=2, maxval=30, group=g)
        self.vol_thresh = i.float(1.0, "Volume RSI Threshold (x50)", minval=0.5, maxval=3.0, step=0.05, group=g)
        g = "RSI Filter"
        self.rsi_len = i.int(14, "RSI Length", minval=2, maxval=50, group=g)
        self.rsi_bull_min = i.int(50, "RSI Bull Minimum", minval=40, maxval=65, group=g)
        self.rsi_bear_max = i.int(50, "RSI Bear Maximum", minval=35, maxval=60, group=g)
        g = "Exit Settings"
        self.atr_len = i.int(14, "ATR Length", minval=1, maxval=50, group=g)
        self.stop_mult = i.float(2.5, "ATR Stop Multiplier", minval=0.5, maxval=10.0, step=0.1, group=g)
        self.tp_mult = i.float(4.0, "ATR Take Profit Mult", minval=0.5, maxval=20.0, step=0.1, group=g)
        self.trail_mult = i.float(1.5, "ATR Trail Multiplier", minval=0.5, maxval=5.0, step=0.1, group=g)
        g = "Trade Filters"
        self.use_vol_filter = i.bool(True, "Use Volume Filter", group=g)
        self.use_rsi_filter = i.bool(True, "Use RSI Filter", group=g)
        self.long_enabled = i.bool(True, "Enable Long Trades", group=g)
        self.short_enabled = i.bool(True, "Enable Short Trades", group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        src = close
        alma_line = ta.alma(src, self.ma_len, self.alma_off, self.alma_sig)
        zlma_raw = 2.0 * ta.ema(src, self.ma_len) - ta.ema(ta.ema(src, self.ma_len), self.ma_len)
        zlma_line = ta.ema(zlma_raw, self.ma_len)
        combo_ma = (alma_line + zlma_line) / 2.0
        cm_h = self.H("combo_ma")
        hist = [combo_ma] + [cm_h[k] for k in range(1, 12)]
        cm_h.set(combo_ma)
        ma_slope = combo_ma - hist[1]
        ma_slope_up = ma_slope > 0
        ma_slope_dn = ma_slope < 0
        slope_up_count = slope_dn_count = 0
        for si in range(int(self.slope_confirm)):
            if (hist[si] - hist[si + 1]) > 0:
                slope_up_count += 1
            if (hist[si] - hist[si + 1]) < 0:
                slope_dn_count += 1
        slope_confirmed_up = slope_up_count >= self.slope_confirm
        slope_confirmed_dn = slope_dn_count >= self.slope_confirm
        price_above_ma = close > combo_ma
        price_below_ma = close < combo_ma
        volume_rsi = div(ta.rsi(self.volume, self.vol_rsi_len), 50.0)
        vol_confirm = (not self.use_vol_filter) or volume_rsi > self.vol_thresh
        rsi_val = ta.rsi(close, self.rsi_len)
        rsi_bull = (not self.use_rsi_filter) or rsi_val > self.rsi_bull_min
        rsi_bear = (not self.use_rsi_filter) or rsi_val < self.rsi_bear_max
        atr14 = ta.atr(self.atr_len)
        confirmed = self.barstate.isconfirmed
        long_condition = slope_confirmed_up and price_above_ma and vol_confirm and rsi_bull and self.long_enabled and confirmed
        short_condition = slope_confirmed_dn and price_below_ma and vol_confirm and rsi_bear and self.short_enabled and confirmed
        long_exit_cond = (close < combo_ma - atr14 * self.trail_mult or ma_slope_dn) and confirmed
        short_exit_cond = (close > combo_ma + atr14 * self.trail_mult or ma_slope_up) and confirmed
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short)
        if st.position_size > 0 and st.position_avg_price > 0:
            st.exit("Long TP/SL", "Long", stop=st.position_avg_price - self.stop_mult * atr14, limit=st.position_avg_price + self.tp_mult * atr14)
        if st.position_size < 0 and st.position_avg_price > 0:
            st.exit("Short TP/SL", "Short", stop=st.position_avg_price + self.stop_mult * atr14, limit=st.position_avg_price - self.tp_mult * atr14)
        if long_exit_cond and st.position_size > 0:
            st.close("Long", comment="L-Exit")
        if short_exit_cond and st.position_size < 0:
            st.close("Short", comment="S-Exit")
