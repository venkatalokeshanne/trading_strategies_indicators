"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DRO Momentum Surge
Author       : Bonestorm007
Source URL   : https://www.tradingview.com/script/7cisWbRB-DRO-Momentum-Surge
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A bar whose volume is at least a multiple of its average, that closes up in the top part of its range, with the RSI below the maximum, the close over the trend EMA and no blow-off pattern (a larger volume multiple with a long upper wick), enters long while flat. The script tracks a hard stop (ATR multiple below the close) and, once the highest close since entry
is the minimum gain above the entry, an ATR trailing stop; one stop order at the higher of the two is re-issued every bar. A blow-off bar while long closes the position at the next open and clears the tracker (the stop order of that bar is then without levels).
Deviations from the original: none.
Not carried over: the signal markers and the information table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class DroMomentumSurge(Script):
    TITLE = "DRO Momentum Surge"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=5, commission_type="percent", commission_value=0.2, slippage=10)
    SOURCE = {"id": "7cisWbRB", "author": "Bonestorm007", "licence": "not stated", "url": "https://www.tradingview.com/script/7cisWbRB-DRO-Momentum-Surge"}

    def init(self):
        i = self.input
        g_vol, g_trend, g_exit = "Volume Surge", "Trend Filter", "Exit Logic"
        self.vol_len = i.int(10, "Volume MA Length", group=g_vol, minval=5)
        self.vol_mult = i.float(2.0, "Volume Surge Multiplier", group=g_vol, minval=1.2, step=0.1)
        self.blowoff = i.float(3.5, "Blow-off Vol Multiplier", group=g_vol, minval=2.0, step=0.1)
        self.wick_pct = i.float(0.35, "Blow-off Wick Ratio", group=g_vol, minval=0.1, step=0.05)
        self.ema_len = i.int(20, "Trend EMA", group=g_trend, minval=5)
        self.rsi_len = i.int(14, "RSI Length", group=g_trend, minval=5)
        self.rsi_max = i.int(80, "Max RSI at Entry", group=g_trend, minval=50, maxval=90)
        self.close_pct = i.float(0.6, "Min Close % of Range", group=g_trend, minval=0.3, maxval=1.0, step=0.05)
        self.atr_len = i.int(10, "ATR Length", group=g_exit, minval=3)
        self.atr_sl = i.float(2.5, "ATR Hard Stop Mult", group=g_exit, minval=1.5, step=0.1)
        self.atr_tr = i.float(3.0, "ATR Trail Stop Mult", group=g_exit, minval=2.0, step=0.1)
        self.min_gain = i.float(15.0, "Min Gain % for Trail", group=g_exit, minval=5.0, step=1.0)
        self.entry_px = NA
        self.hard_stop = NA
        self.trail_high = NA
        self.trail_stop = NA
        self.trail_active = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        vol_ma = ta.sma(self.volume, self.vol_len)
        ema_trend = ta.ema(close, self.ema_len)
        rsi_val = ta.rsi(close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        vol_ratio = div(self.volume, vol_ma)
        vol_surge = vol_ratio >= self.vol_mult
        candle_range = high - low
        close_pos = div(close - low, candle_range) if candle_range > 0 else 0.5
        bullish_bar = close > open_ and close_pos >= self.close_pct
        upper_wick = high - pmath.max(open_, close)
        blowoff_top = vol_ratio >= self.blowoff and candle_range > 0 and div(upper_wick, candle_range) >= self.wick_pct
        long_signal = vol_surge and bullish_bar and rsi_val < self.rsi_max and close > ema_trend and (not blowoff_top) and st.position_size == 0
        if long_signal:
            self.entry_px = float(close)
            self.hard_stop = close - self.atr_sl * atr_val
            self.trail_high = float(close)
            self.trail_stop = self.hard_stop
            self.trail_active = False
            st.entry("Long", st.long)
        if st.position_size > 0:
            self.trail_high = pmath.max(self.trail_high, close)
            gain_pct = div(self.trail_high - self.entry_px, self.entry_px) * 100
            if gain_pct >= self.min_gain:
                self.trail_active = True
            self.trail_stop = self.trail_high - self.atr_tr * atr_val if self.trail_active else self.hard_stop
            st.exit("Exit", "Long", stop=pmath.max(self.hard_stop, self.trail_stop))
        if st.position_size > 0 and blowoff_top:
            st.close("Long", comment="Blow-off exit")
            self.entry_px = NA
            self.hard_stop = NA
            self.trail_high = NA
            self.trail_stop = NA
            self.trail_active = False
