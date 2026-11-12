"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sweep + SD + MA20/50 + ATR
Author       : dobos_e_v_95
Source URL   : https://www.tradingview.com/script/3uS01cPF-Sweep-SD-MA20-50-ATR
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Each confirmed pivot (5 bars each side) sets a supply zone (pivot high down to its body top)
or a demand zone (pivot low up to its body bottom), taken from the pivot bar `swingLen` bars back. A bar that sweeps
below the demand zone and closes back above it by more than half an ATR, in a rising SMA20 > SMA50 trend with a spread
over 0.2 ATR, goes long when flat (mirror short). Entry and exit (stop = signal bar low / high, 3 R target) are issued
together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the SMA plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class SweepSdMa(Script):
    TITLE = "Sweep + SD + MA20/50 + ATR"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "3uS01cPF", "author": "dobos_e_v_95", "licence": "not stated",
              "url": "https://www.tradingview.com/script/3uS01cPF-Sweep-SD-MA20-50-ATR"}

    def init(self):
        self.swing_len = self.input.int(5, "Swing Length", minval=2)
        self.rr = self.input.float(3.0, "Risk Reward", step=0.5)
        self.atr_mult = self.input.float(0.5, "Minimum Sweep ATR", step=0.1)
        self.supply_top = NA
        self.supply_bottom = NA
        self.demand_top = NA
        self.demand_bottom = NA

    def on_bar(self):
        ma20 = S(ta.sma(self.close, 20))
        ma50 = S(ta.sma(self.close, 50))
        atr = ta.atr(14)
        ph = ta.pivothigh(self.high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(self.low, self.swing_len, self.swing_len)
        k = self.swing_len
        if not na(ph):
            self.supply_top = self.high[k]
            self.supply_bottom = pmath.max(self.open[k], self.close[k])
        if not na(pl):
            self.demand_bottom = self.low[k]
            self.demand_top = pmath.min(self.open[k], self.close[k])
        bull_trend = ma20.cur > ma50.cur and ma20.cur > ma20[1] and ma50.cur > ma50[1]
        bear_trend = ma20.cur < ma50.cur and ma20.cur < ma20[1] and ma50.cur < ma50[1]
        trend_strength = pmath.abs(ma20.cur - ma50.cur)
        valid_trend = trend_strength > atr * 0.2
        long_sweep = ((not na(self.demand_bottom)) and self.low < self.demand_bottom and self.close > self.demand_bottom
                      and (self.demand_bottom - self.low) > atr * self.atr_mult)
        short_sweep = ((not na(self.supply_top)) and self.high > self.supply_top and self.close < self.supply_top
                       and (self.high - self.supply_top) > atr * self.atr_mult)
        st = self.strategy
        long_condition = long_sweep and bull_trend and valid_trend and st.position_size == 0
        short_condition = short_sweep and bear_trend and valid_trend and st.position_size == 0
        if long_condition:
            stop_loss = float(self.low)
            risk = self.close - stop_loss
            take_profit = self.close + risk * self.rr
            st.entry("BUY", st.long)
            st.exit("BUY TP/SL", "BUY", stop=stop_loss, limit=take_profit)
        if short_condition:
            stop_loss = float(self.high)
            risk = stop_loss - self.close
            take_profit = self.close - risk * self.rr
            st.entry("SELL", st.short)
            st.exit("SELL TP/SL", "SELL", stop=stop_loss, limit=take_profit)
        self.plot(ma20, "MA20", color=color.green, linewidth=2)
        self.plot(ma50, "MA50", color=color.red, linewidth=2)
