"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTCUSD Supertrend + EMA Trend Filter (1H) (Bitcoin SuperFlip)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/NgSIfKQx-Bitcoin-SuperFlip-Supertrend-EMA-Trend-Following-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend flip to an up-trend with the close above the EMA200 (and an optional ADX filter) goes long; a flip to a down-trend with the close below goes short. The opposite
position is also closed on every flip (after the entry orders in source order). Optional percent stop / take-profit around the average price are issued while in a position (off by default).

Deviations from the original: none.
Not carried over: colour presets, glow plots, gradient fills, flip markers, bar / background colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class BitcoinSuperFlip(Script):
    TITLE = "BTCUSD Supertrend + EMA Trend Filter (1H)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=25, commission_type="percent", commission_value=0.075, slippage=1)
    SOURCE = {"id": "NgSIfKQx", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NgSIfKQx-Bitcoin-SuperFlip-Supertrend-EMA-Trend-Following-Strategy"}

    def init(self):
        g = "════════ Strategy Settings ════════"
        self.atr_period = self.input.int(10, "Supertrend ATR Length", group=g)
        self.factor = self.input.float(1.8, "Supertrend Factor", step=0.1, group=g)
        self.ema_len = self.input.int(200, "EMA Trend Filter Length", group=g)
        self.enable_sl = self.input.bool(False, "Enable Stop Loss", group=g)
        self.enable_tp = self.input.bool(False, "Enable Take Profit", group=g)
        self.sl_pct = self.input.float(4.0, "Stop Loss %", step=0.1, group=g) / 100
        self.tp_pct = self.input.float(8.0, "Take Profit %", step=0.1, group=g) / 100
        g = "════════ ADX Filter ════════"
        self.enable_adx = self.input.bool(False, "Enable ADX Filter", group=g)
        self.adx_len = self.input.int(14, "ADX Length", minval=1, group=g)
        self.adx_smooth = self.input.int(14, "ADX Smoothing", minval=1, group=g)
        self.adx_thresh = self.input.float(20.0, "ADX Threshold", step=1.0, group=g)

    def on_bar(self):
        supertrend, direction = ta.supertrend(self.factor, self.atr_period)
        trend_ema = ta.ema(self.close, self.ema_len)
        d_change = ta.change(direction)
        bull_flip = d_change < 0
        bear_flip = d_change > 0
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_smooth)
        adx_ok = (not self.enable_adx) or adx > self.adx_thresh
        long_condition = bull_flip and self.close > trend_ema and adx_ok
        short_condition = bear_flip and self.close < trend_ema and adx_ok
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        if bear_flip:
            st.close("Long")
        if bull_flip:
            st.close("Short")
        if st.position_size > 0:
            entry_price = st.position_avg_price
            if self.enable_sl:
                st.exit("Long SL/TP", "Long", stop=entry_price * (1 - self.sl_pct), limit=entry_price * (1 + self.tp_pct) if self.enable_tp else NA)
        if st.position_size < 0:
            entry_price = st.position_avg_price
            if self.enable_sl:
                st.exit("Short SL/TP", "Short", stop=entry_price * (1 + self.sl_pct), limit=entry_price * (1 - self.tp_pct) if self.enable_tp else NA)
        self.plot(supertrend if direction < 0 else NA, "Bullish Supertrend", color=color.green, linewidth=2)
        self.plot(supertrend if direction > 0 else NA, "Bearish Supertrend", color=color.red, linewidth=2)
        self.plot(trend_ema, "EMA Trend Filter", color=color.orange)
