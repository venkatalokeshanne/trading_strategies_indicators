"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 3 Soldiers 3 Crows + 8 differend MA
Author       : egoigor1976
Source URL   : https://www.tradingview.com/script/V3jpZpIs-3-Soldiers-3-Crows-8-differend-MA
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Three white soldiers above both MAs (and the cooldown) go long, three black crows below
both go short; entries fill at the next open and reverse an open opposite trade. The two MAs come from a switch over
eight types (SMA, EMA, WMA, DEMA, HMA, VAR, ZLEMA, RMA) on the chosen source (default high). Each getMA call has its own
call-site state, as in Pine.

Deviations from the original: the VAR type keeps its own rolling 9-bar sums per MA slot (math.sum has no pinelib call).
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from collections import deque

from pinelib import NA, S, Script, color, div, na, nz, pmath, ta


class SoldiersCrowsMa(Script):
    TITLE = "3 Soldiers 3 Crows + 8 differend MA"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=1000, pyramiding=1,
                    commission_type="percent", commission_value=0.05, margin_long=10, margin_short=10)
    SOURCE = {"id": "V3jpZpIs", "author": "egoigor1976", "licence": "not stated",
              "url": "https://www.tradingview.com/script/V3jpZpIs-3-Soldiers-3-Crows-8-differend-MA"}

    def init(self):
        types = ["SMA", "EMA", "WMA", "DEMA", "HMA", "VAR", "ZLEMA", "RMA"]
        self.src_input = self.input.source(self.high, "Источник цены (Source)", group="Настройки фильтров MA")
        self.ma1_type = self.input.string("SMA", "Тип MA 1 (Быстрая)", options=types, group="Настройки фильтров MA")
        self.ma1_length = self.input.int(22, "Период MA 1", group="Настройки фильтров MA")
        self.ma2_type = self.input.string("ZLEMA", "Тип MA 2 (Медленная)", options=types, group="Настройки фильтров MA")
        self.ma2_length = self.input.int(210, "Период MA 2", group="Настройки фильтров MA")
        self.use_cooldown = self.input.bool(True, "Использовать Cooldown", group="Кулдаун Фильтр")
        self.cooldown_period = self.input.int(212, "Cooldown (свечей)", group="Кулдаун Фильтр")
        self.last_buy_bar = 0
        self.last_sell_bar = 0
        self._var = {1: dict(up=deque(maxlen=9), dn=deque(maxlen=9), prev=None, val=0.0, s1=None),
                     2: dict(up=deque(maxlen=9), dn=deque(maxlen=9), prev=None, val=0.0, s1=None)}

    def var_func(self, slot, src, length):
        st = self._var[slot]
        valpha = div(2, length + 1)
        prev = st["s1"]
        vud1 = src - prev if (prev is not None and src > prev) else 0
        vdd1 = prev - src if (prev is not None and src < prev) else 0
        st["s1"] = src
        st["up"].append(vud1)
        st["dn"].append(vdd1)
        if len(st["up"]) < 9:
            vud = vdd = NA
        else:
            vud, vdd = sum(st["up"]), sum(st["dn"])
        denom = vud + vdd
        vcmo = nz(div(vud - vdd, denom))
        st["val"] = nz(valpha * pmath.abs(vcmo) * src) + (1 - valpha * pmath.abs(vcmo)) * st["val"]
        return st["val"]

    def get_ma(self, slot, src, length, typ):
        if typ == "SMA":
            return ta.sma(src, length)
        if typ == "EMA":
            return ta.ema(src, length)
        if typ == "WMA":
            return ta.wma(src, length)
        if typ == "DEMA":
            ema1 = ta.ema(src, length)
            ema2 = ta.ema(ema1, length)
            return 2 * ema1 - ema2
        if typ == "HMA":
            wma1 = ta.wma(src, int(pmath.floor(div(length, 2))))
            wma2 = ta.wma(src, length)
            return ta.wma(2 * wma1 - wma2, int(pmath.round(pmath.sqrt(length))))
        if typ == "VAR":
            return self.var_func(slot, src, length)
        if typ == "ZLEMA":
            lag = int(pmath.floor(div(length - 1, 2)))
            s = S(src)
            ema_data = src + (src - nz(s[lag]))
            return ta.ema(ema_data, length)
        if typ == "RMA":
            return ta.rma(src, length)
        return ta.sma(src, length)

    def on_bar(self):
        ma1 = self.get_ma(1, self.src_input, self.ma1_length, self.ma1_type)
        ma2 = self.get_ma(2, self.src_input, self.ma2_length, self.ma2_type)
        c, o = S(self.close), S(self.open)
        three_white_soldiers = (c[0] > o[0] and c[1] > o[1] and c[2] > o[2] and o[1] <= c[2] and c[1] > c[2]
                                and o[0] <= c[1] and c[0] > c[1])
        three_black_crows = (c[0] < o[0] and c[1] < o[1] and c[2] < o[2] and o[1] >= c[2] and c[1] < c[2]
                             and o[0] >= c[1] and c[0] < c[1])
        can_buy = (self.bar_index - self.last_buy_bar) > self.cooldown_period
        can_sell = (self.bar_index - self.last_sell_bar) > self.cooldown_period
        buy_signal = three_white_soldiers and self.close > ma1 and self.close > ma2 and ((not self.use_cooldown) or can_buy)
        sell_signal = three_black_crows and self.close < ma1 and self.close < ma2 and ((not self.use_cooldown) or can_sell)
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long, comment="Soldiers")
            self.last_buy_bar = self.bar_index
        if sell_signal:
            st.entry("Short", st.short, comment="Crows")
            self.last_sell_bar = self.bar_index
        self.plot(ma1, "Fast MA", color=color.orange, linewidth=2)
        self.plot(ma2, "Slow MA", color=color.blue, linewidth=2)
