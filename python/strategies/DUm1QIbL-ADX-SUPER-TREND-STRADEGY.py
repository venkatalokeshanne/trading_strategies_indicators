"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ADX-ZONE/ST/S-R (ADX-SUPER TREND STRADEGY)
Author       : fullmax
Source URL   : https://www.tradingview.com/script/DUm1QIbL-ADX-SUPER-TREND-STRADEGY
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend line is stretched by the ADX (a one-bar smoothed |DI+ - DI-| / (DI+ + DI-)) into a buy zone above the up-trend line and a sell zone below the
down-trend line; a low below the buy zone that does not make a new low of the previous bars (a high above the sell zone not making a new high) enters when no trade is open. A percent
trailing stop (ratcheting from the close) and a percent take-profit around the average price are issued while in a position. The trade size array grows after losing trades and
resets after wins, as in the original (it does not affect which trades are taken).

Deviations from the original: none.
Not carried over: SuperTrend / zone / stop plots and fills (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, fixnan, na, nz, parray, pmath, ta


class AdxSuperTrend(Script):
    TITLE = "ADX-ZONE/ST/S-R"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "DUm1QIbL", "author": "fullmax", "licence": "not stated",
              "url": "https://www.tradingview.com/script/DUm1QIbL-ADX-SUPER-TREND-STRADEGY"}

    def init(self):
        self.tradedir = self.input.string("Both", "Trade Direction", options=["Long", "Short", "Both"])
        self.long_trail_perc = self.input.float(2.0, "Trail Long Loss (%)", minval=0.0, step=0.1) * 0.01
        self.short_trail_perc = self.input.float(2.0, "Trail Short Loss (%)", minval=0.0, step=0.1) * 0.01
        self.tp_level_l = self.input.float(1.5, "Take Profit long (%)", step=0.1)
        self.tp_level_s = self.input.float(1.5, "Take Profit short (%)", step=0.1)
        self.atr_period = self.input.int(5, "ATR Length", minval=1)
        self.factor = self.input.float(3.02, "Factor", minval=0.01, step=0.01)
        self.s_r = self.input.bool(True, "Support-Res")
        self.sup = self.input.int(33, "Lookback (Sup)", minval=1)
        self.res = self.input.int(17, "Lookback (Res)", minval=1)
        self.adxlen = self.input.int(1, "ADX Smoothing")
        self.dilen = self.input.int(20, "DI Length")
        self.szz = self.input.int(1000, "Size of the trade in USD")
        self.increase_t = self.input.bool(True, " Increase size of the trade after # of losing trades ")
        self.nl = self.input.float(1, "# of losing trades in the row", minval=1)
        self.size_arr = None

    def on_bar(self):
        supertrend, direction = ta.supertrend(self.factor, self.atr_period)
        if self.barstate.isfirst:
            supertrend = NA
        upd = supertrend if direction < 0 else NA
        dnd = NA if direction < 0 else supertrend
        support = ta.lowest(self.low[1], self.sup)
        resistan = ta.highest(self.high[1], self.res)
        entrysup = self.low >= support
        entryres = self.high <= resistan
        up = ta.change(self.high)
        down = -ta.change(self.low)
        plus_dm = NA if na(up) else (up if (up > down and up > 0) else 0)
        minus_dm = NA if na(down) else (down if (down > up and down > 0) else 0)
        truerange = ta.rma(ta.tr(False), self.dilen)
        plus = fixnan(100 * div(ta.rma(plus_dm, self.dilen), truerange))
        minus = fixnan(100 * div(ta.rma(minus_dm, self.dilen), truerange))
        s = plus + minus
        sig = 100 * ta.rma(div(pmath.abs(plus - minus), 1 if s == 0 else s), self.adxlen)
        buyzone = upd * (1 + sig / 10000)
        sellzone = dnd * (1 - sig / 10000)
        buy = self.low < buyzone and entrysup
        sell = self.high > sellzone and entryres
        st = self.strategy
        avg = st.position_avg_price
        tp_price_long = avg * (1 + self.tp_level_l / 100)
        tp_price_short = avg * (1 - self.tp_level_s / 100)
        long_prev = nz(self.H("long_stop")[1], 0.0)
        short_prev = nz(self.H("short_stop")[1], 0.0)
        if st.position_size > 0:
            long_stop = pmath.max(self.close * (1 - self.long_trail_perc), long_prev)
        else:
            long_stop = 0
        if st.position_size < 0:
            short_stop = pmath.min(self.close * (1 + self.short_trail_perc), short_prev)
        else:
            short_stop = 999999
        self.H("long_stop").set(long_stop)
        self.H("short_stop").set(short_stop)
        osc = div(self.szz, self.close)
        wins, losses, evens = st.wintrades, st.losstrades, st.eventrades
        w1, l1, e1 = self.H("wins")[1], self.H("losses")[1], self.H("evens")[1]
        self.H("wins").set(wins)
        self.H("losses").set(losses)
        self.H("evens").set(evens)
        loss = losses > l1 and wins == w1 and evens == e1
        win = wins > w1 and losses == l1 and evens == e1
        streak_prev = nz(self.H("streak")[1])
        if loss:
            streaklen = streak_prev + 1
        elif wins > w1 or evens > e1:
            streaklen = 0
        else:
            streaklen = streak_prev
        self.H("streak").set(streaklen)
        if self.size_arr is None:
            self.size_arr = [osc / 2, osc, osc, osc / 2]
        if win and parray.size(self.size_arr) >= 4:
            parray.shift(self.size_arr)
            parray.pop(self.size_arr)
        elif win:
            self.size_arr = [osc / 2, osc / 2, osc / 2, osc / 2]
        if streaklen >= self.nl and loss:
            parray.push(self.size_arr, parray.get(self.size_arr, 1) + parray.last(self.size_arr))
        fl = parray.get(self.size_arr, 0) + parray.last(self.size_arr)
        if buy and (self.tradedir == "Long" or self.tradedir == "Both") and st.opentrades == 0:
            st.entry("Long", st.long, qty=fl if self.increase_t else osc)
        if sell and (self.tradedir == "Short" or self.tradedir == "Both") and st.opentrades == 0:
            st.entry("Short", st.short, qty=fl if self.increase_t else osc)
        if st.position_size > 0:
            st.exit("TP/stop", stop=long_stop, limit=tp_price_long)
        if st.position_size < 0:
            st.exit("Tp/stop", stop=short_stop, limit=tp_price_short)
        self.plot(buyzone, "Buy zone", color=color.blue)
        self.plot(sellzone, "Sell Zone", color=color.orange)
