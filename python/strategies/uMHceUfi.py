"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EXPMA三线回踩｜多1绿多2蓝多3紫
Author       : MieMomo3
Source URL   : https://www.tradingview.com/script/uMHceUfi
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). In an EMA10 > EMA20 trend, three pull-back patterns (long 1: open over EMA10 with a low touching EMA20; long 2: open between the EMAs; long 3: a low touching EMA10), each requiring an up day, a bounded EMA bias, a small upper shadow and a volume within a band of its average,
set a signal; a signal on the PREVIOUS bar opens a long while no position type is active (the recorded entry price is that bar's open, not the actual fill). Each type has its own fixed stop, break-even / half-profit stop raises at +5 % / +10 %, two take-profit stages (a part at the first, everything at the second) and a time exit after three days
without +5 %; a close at or below the stop or the 20 EMA also exits. All exits are market closes: a later close order in the same bar replaces an earlier one.
Deviations from the original: none.
Not carried over: the coloured signal markers (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class ExpmaPullback(Script):
    TITLE = "EXPMA三线回踩｜多1绿多2蓝多3紫"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="cash", default_qty_value=100000, commission_type="percent", commission_value=0.13)
    SOURCE = {"id": "uMHceUfi", "author": "MieMomo3", "licence": "not stated", "url": "https://www.tradingview.com/script/uMHceUfi"}

    def init(self):
        i = self.input
        self.min_vol_mult = i.float(1.0, "成交量下限倍数(改1.0更容易出信号)")
        self.max_vol_mult = i.float(3.5, "成交量上限倍数")
        self.min_ma_bias = i.float(0.0, "EXPMA乖离下限%")
        self.max_ma_bias = i.float(2.5, "EXPMA乖离上限%")
        self.max_upper_shadow = i.float(0.8, "上影/收盘价上限%")
        self.stop_loss = [i.float(3.5, "多1固定止损%"), i.float(3.0, "多2固定止损%"), i.float(2.2, "多3固定止损%")]
        self.tp1 = [i.float(7.0, "多1一档止盈%"), i.float(6.0, "多2一档止盈%"), i.float(5.0, "多3一档止盈%")]
        self.tp2 = [i.float(13.0, "多1二档止盈%"), i.float(11.0, "多2二档止盈%"), i.float(9.0, "多3二档止盈%")]
        self.entry_price = NA
        self.pos_type = 0
        self.hold_days = 0
        self.prev_sig = [False, False, False]

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        expma10 = ta.ema(close, 10)
        expma20 = ta.ema(close, 20)
        vol_ma = ta.sma(self.volume, 20)
        ma_bias = div(expma10 - expma20, expma20) * 100
        upper_shadow_pct = div(high - close, close) * 100
        day_gain = div(ta.change(close), self.close[1]) * 100
        cond_vol = self.volume >= vol_ma * self.min_vol_mult and self.volume <= vol_ma * self.max_vol_mult
        cond_bias = ma_bias >= self.min_ma_bias and ma_bias <= self.max_ma_bias
        cond_shadow = upper_shadow_pct < self.max_upper_shadow
        cond_up = day_gain > 0
        cond_trend = expma10 > expma20
        common = cond_up and cond_bias and cond_shadow and cond_vol
        sig1 = cond_trend and open_ > expma10 and low <= expma20 and close > expma10 and common
        sig2 = cond_trend and open_ > expma20 and open_ < expma10 and low <= expma20 and close > expma10 and common
        sig3 = cond_trend and open_ > expma10 and low <= expma10 and close > expma10 and common
        p1, p2, p3 = self.prev_sig
        self.prev_sig = [bool(sig1), bool(sig2), bool(sig3)]
        for k, ps in enumerate((p1, p2, p3)):
            if ps and self.pos_type == 0:
                st.entry("Long", st.long)
                self.entry_price = float(open_)
                self.pos_type = k + 1
                self.hold_days = 0
        if st.position_size > 0:
            self.hold_days += 1
        stop_price = NA
        if self.pos_type in (1, 2, 3):
            stop_price = self.entry_price * (1 - self.stop_loss[self.pos_type - 1] / 100)
        if st.position_size > 0 and div(close, self.entry_price) >= 1.05:
            stop_price = pmath.max(stop_price, self.entry_price)
        if st.position_size > 0 and div(close, self.entry_price) >= 1.10:
            stop_price = pmath.max(stop_price, self.entry_price + (close - self.entry_price) / 2)
        exit_stop = close <= stop_price or close <= expma20
        highest3 = ta.highest(high, 3)
        time_exit = self.hold_days >= 3 and div(highest3, self.entry_price) < 1.05
        if self.pos_type in (1, 2, 3) and st.position_size > 0:
            pos_amt = st.position_size
            frac = 0.4 if self.pos_type == 1 else 0.5
            if div(close, self.entry_price) >= 1 + self.tp1[self.pos_type - 1] / 100:
                st.close("Long", qty=pos_amt * frac, comment="一档止盈")
            if div(close, self.entry_price) >= 1 + self.tp2[self.pos_type - 1] / 100:
                st.close("Long", comment="二档全平")
        if st.position_size > 0 and (exit_stop or time_exit):
            st.close("Long", comment="止损/时间离场")
        if st.position_size == 0:
            self.entry_price = NA
            self.pos_type = 0
            self.hold_days = 0
