"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Auto-Trade Bot v12 [Dayrel] — EMA115
Author       : Dayrel
Source URL   : https://www.tradingview.com/script/tDChqhhR
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A liquidity sweep (a low under the lowest low of the previous 14 bars; mirror for highs) arms a setup; the first bullish candle that closes above the sweep bar's high with the 20-bar HMA rising, the close over the hourly EMA(115) and that EMA rising triggers a long when Williams %R is above its EMA(13) and was oversold (-79) within the last 70 bars ("HP"), or without that oversold history when the sweep lows are making a higher low ("LP"). Shorts mirror these rules and are off in the default "Longs Only" mode. A flat strategy enters with 100 % of equity and the exit order is a stop under the sweep bar's low (a 0.5 % fallback) and a target 5 x the risk away, re-issued every bar while in the trade.
Deviations from the original: none.
Not carried over: plots, shapes, the alert messages.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AutoTradeBotV12(Script):
    TITLE = "Auto-Trade Bot v12 [Dayrel] — EMA115"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=10000, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "tDChqhhR", "author": "Dayrel", "licence": "not stated", "url": "https://www.tradingview.com/script/tDChqhhR"}

    def init(self):
        i = self.input
        self.longs_only = i.bool(True, "Longs Only Mode", group="⚙️ Mode")
        self.hma_len = i.int(20, "HMA Length", group="📈 HMA", minval=5)
        self.sweep_len = i.int(14, "Sweep Lookback (bars)", group="🔍 Sweep", minval=3, maxval=50)
        self.willy_len = i.int(14, "%R Length", group="🟡 Willy", minval=1)
        self.willy_ema = i.int(13, "%R EMA Length", group="🟡 Willy", minval=1)
        self.willy_os = i.float(-79.0, "%R Oversold Level", group="🟡 Willy", minval=-100, maxval=-50, step=1)
        self.willy_window = i.int(70, "OS/OB Lookback (bars)", group="🟡 Willy", minval=5, maxval=200)
        self.ema_len = i.int(115, "EMA Length (1H TF)", group="📊 EMA115", minval=10, maxval=500)
        self.rr = i.float(5.0, "Risk to Reward Ratio", group="💰 R:R", minval=0.1, step=0.1)
        self.last_os_bar = -1000
        self.last_ob_bar = -1000
        self.long_sweep_high = NA
        self.long_sweep_low = NA
        self.long_sweep_on = False
        self.short_sweep_low = NA
        self.short_sweep_high = NA
        self.short_sweep_on = False
        self.last_long_sl = NA
        self.prev_long_sl = NA
        self.last_short_sh = NA
        self.prev_short_sh = NA
        self.t_sl = NA
        self.t_tp = NA

    def _hma(self, src, length):
        return ta.wma(2 * ta.wma(src, pmath.floor(length / 2)) - ta.wma(src, length), pmath.floor(pmath.sqrt(length)))

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        h_hma, h_ema = self.H("hma"), self.H("ema")
        hma_1, hma_2, ema_1, ema_2 = h_hma[1], h_hma[2], h_ema[1], h_ema[2]
        low_1, high_1 = self.low[1], self.high[1]
        hma20 = self._hma(close, self.hma_len)
        hma_rising = hma20 >= hma_1 and hma_1 >= hma_2
        hma_falling = hma20 <= hma_1 and hma_1 <= hma_2
        ema115 = self.security(None, "60", lambda v: ta.ema(v.close, self.ema_len))
        ema_rising = ema115 >= ema_1 and ema_1 >= ema_2
        ema_falling = ema115 <= ema_1 and ema_1 <= ema_2
        willy_ob = -(100 + self.willy_os)
        willy = ta.wpr(self.willy_len)
        willy_ema_v = ta.ema(willy, self.willy_ema)
        willy_above = willy > willy_ema_v
        willy_below = willy < willy_ema_v
        if willy <= self.willy_os:
            self.last_os_bar = self.bar_index
        if willy >= willy_ob:
            self.last_ob_bar = self.bar_index
        from_os = (self.bar_index - self.last_os_bar) <= self.willy_window
        from_ob = (self.bar_index - self.last_ob_bar) <= self.willy_window

        recent_swing_low = ta.lowest(low_1, self.sweep_len)
        is_long_sweep = low < recent_swing_low
        if is_long_sweep:
            self.long_sweep_high = float(high)
            self.long_sweep_low = float(low)
            self.long_sweep_on = True
        recent_swing_high = ta.highest(high_1, self.sweep_len)
        is_short_sweep = high > recent_swing_high
        if is_short_sweep:
            self.short_sweep_low = float(low)
            self.short_sweep_high = float(high)
            self.short_sweep_on = True
        if is_long_sweep:
            self.prev_long_sl = self.last_long_sl
            self.last_long_sl = float(low)
        if is_short_sweep:
            self.prev_short_sh = self.last_short_sh
            self.last_short_sh = float(high)
        higher_low = (not na(self.prev_long_sl)) and self.last_long_sl > self.prev_long_sl
        lower_high = (not na(self.prev_short_sh)) and self.last_short_sh < self.prev_short_sh

        long_base = self.long_sweep_on and (close > open_) and close > self.long_sweep_high and close > hma20 and hma_rising and close > ema115 and ema_rising
        if long_base:
            self.long_sweep_on = False
        long_hp = long_base and willy_above and from_os
        long_lp = long_base and willy_above and (not from_os) and higher_low
        long_sig = long_hp or long_lp
        short_base = (not self.longs_only) and self.short_sweep_on and (close < open_) and close < self.short_sweep_low and close < hma20 and hma_falling and close < ema115 and ema_falling
        if short_base:
            self.short_sweep_on = False
        short_hp = short_base and willy_below and from_ob
        short_lp = short_base and willy_below and (not from_ob) and lower_high
        short_sig = short_hp or short_lp

        tick = self.syminfo.mintick
        l_sl = self.long_sweep_low - tick if not na(self.long_sweep_low) else close * 0.995
        l_risk = pmath.max(close - l_sl, tick)
        l_tp = close + l_risk * self.rr
        s_sl = self.short_sweep_high + tick if not na(self.short_sweep_high) else close * 1.005
        s_risk = pmath.max(s_sl - close, tick)
        s_tp = close - s_risk * self.rr

        if long_sig and st.position_size == 0:
            self.t_sl = l_sl
            self.t_tp = l_tp
            st.entry("Long", st.long)
        if short_sig and st.position_size == 0:
            self.t_sl = s_sl
            self.t_tp = s_tp
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=self.t_sl, limit=self.t_tp, comment_profit="TP 🎯 5R", comment_loss="SL ❌")
        if st.position_size < 0:
            st.exit("Exit Short", "Short", stop=self.t_sl, limit=self.t_tp, comment_profit="TP 🎯 5R", comment_loss="SL ❌")
        h_hma.set(hma20)
        h_ema.set(ema115)
