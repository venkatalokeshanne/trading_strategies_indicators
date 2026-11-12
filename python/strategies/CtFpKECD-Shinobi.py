"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Shinobi HA Stratégia v3
Author       : Takumi_algo
Source URL   : https://www.tradingview.com/script/CtFpKECD-Shinobi
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A Heikin-Ashi doji with a bigger range than the bar before it, preceded by two same-colour bars without a wick on the entry side, in the SuperTrend direction with ADX, a structure filter (LinReg channel, ATR channel, Donchian channel or the Swing HL sequence), the session and a volume filter, enters at the close; the stop is the HA low / high and the target is a risk / reward multiple of it.

Deviations from the original: none.
Not carried over: SuperTrend and body-middle plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class ShinobiHA(Script):
    TITLE = "Shinobi HA Stratégia v3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, process_orders_on_close=True)
    SOURCE = {"id": "CtFpKECD", "author": "Takumi_algo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/CtFpKECD-Shinobi"}

    def init(self):
        i = self.input
        g = "SuperTrend"
        self.atr_len = i.int(15, "ATR Length", group=g, minval=1)
        self.st_factor = i.float(3.44, "SuperTrend Factor", group=g, minval=0.01, step=0.01)
        g = "ADX szűrő"
        self.adx_len = i.int(14, "ADX Length", group=g)
        self.adx_min = i.float(22, "Minimum ADX", group=g)
        g = "Gyertya formáció"
        self.doji_max_pct = div(i.float(20, "Doji max test %", group=g, minval=1, maxval=50), 100)
        self.wick_tol_pct = div(i.float(3, "Kanóc tolerancia %", group=g, minval=0, maxval=50), 100)
        self.doji_wick_mult = i.float(0.3, "Doji kanóc minimum szorzó", group=g, minval=0.0, maxval=2.0, step=0.1)
        self.rr_ratio = i.float(1.0, "Risk/Reward arány", group="RR beállítás", minval=0.1, step=0.1)
        g = "Volume szűrő"
        self.use_volume = i.bool(True, "Volume szűrő bekapcsolva", group=g)
        self.vol_len = i.int(20, "Volume MA periódus", group=g, minval=1)
        self.vol_mult = i.float(1.0, "Volume minimum szorzó", group=g, minval=0.1, step=0.1)
        g = "Időszűrő"
        self.trade_sess = i.session("1700-2000", "Trading időszak", group=g)
        self.trade_tz = i.string("Europe/Budapest", "Időzóna", group=g, options=["Europe/Budapest", "America/New_York", "UTC"])
        g = "Struktúra szűrő"
        self.filter_type = i.string("Swing HL", "Struktúra szűrő típusa", options=["LinReg csatorna", "ATR csatorna", "Donchian Channel", "Swing HL"], group=g)
        g = "Struktúra szűrő — LinReg"
        self.lr_len = i.int(100, "LinReg periódus", group=g, minval=10)
        self.lr_src = i.source(self.close, "LinReg forrás", group=g)
        self.lr_dev_mult = i.float(2.0, "Sáv szélesség (StdDev szorzó)", group=g, step=0.1)
        g = "Struktúra szűrő — ATR csatorna"
        self.atr_ma_len = i.int(50, "MA periódus", group=g)
        self.atr_mult = i.float(2.0, "ATR szorzó", group=g, step=0.1)
        self.don_len = i.int(20, "Periódus", group="Struktúra szűrő — Donchian")
        self.swing_len = i.int(5, "Swing érzékenység", group="Struktúra szűrő — Swing HL")
        self.ha_open = NA
        self.last_sh = NA
        self.last_sh2 = NA
        self.last_sl = NA
        self.last_sl2 = NA

    def lin_reg(self):
        src, length = self.lr_src, int(self.lr_len)
        sum_x = sum_y = sum_x_sqr = sum_xy = 0.0
        for k in range(length):
            v = src[k]
            p = float(k + 1)
            sum_x += p
            sum_y += v
            sum_x_sqr += p * p
            sum_xy += v * p
        slope = div(length * sum_xy - sum_x * sum_y, length * sum_x_sqr - sum_x * sum_x)
        avg = div(sum_y, length)
        intercept = avg - div(slope * sum_x, length) + slope
        std_acc = 0.0
        val = intercept
        for k in range(length):
            diff = src[k] - val
            std_acc += diff * diff
            val += slope
        std_dev = pmath.sqrt(div(std_acc, length))
        return intercept + slope * (length - 1), std_dev

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ha_close = (open_ + high + low + close) / 4
        hc_h, ho_h, hh_h, hl_h = self.H("ha_close"), self.H("ha_open"), self.H("ha_high"), self.H("ha_low")
        hc_1, hc_2 = hc_h[1], hc_h[2]
        ha_open_prev = self.ha_open
        self.ha_open = (open_ + close) / 2 if na(ha_open_prev) else (ha_open_prev + (0.0 if na(hc_1) else hc_1)) / 2
        ha_open = self.ha_open
        ha_high = pmath.max(high, pmath.max(ha_open, ha_close))
        ha_low = pmath.min(low, pmath.min(ha_open, ha_close))
        ho_1, ho_2, hh_1, hh_2, hl_1, hl_2 = ho_h[1], ho_h[2], hh_h[1], hh_h[2], hl_h[1], hl_h[2]
        hc_h.set(ha_close)
        ho_h.set(ha_open)
        hh_h.set(ha_high)
        hl_h.set(ha_low)
        supertrend, direction = ta.supertrend(self.st_factor, self.atr_len)
        ha_bull = direction < 0
        ha_bear = direction > 0
        _, _, adx_val = ta.dmi(self.adx_len, self.adx_len)
        adx_ok = adx_val >= self.adx_min
        in_session = not na(self.time_fn(None, self.trade_sess, self.trade_tz))
        vol_ma = ta.ema(self.volume, self.vol_len)
        vol_ok = (not self.use_volume) or self.volume >= vol_ma * self.vol_mult
        lr_upper = lr_lower = NA
        if self.filter_type == "LinReg csatorna":
            lr_start, lr_std = self.lin_reg()
            lr_upper = lr_start + self.lr_dev_mult * lr_std
            lr_lower = lr_start - self.lr_dev_mult * lr_std
        lr_in_band = close <= lr_upper and close >= lr_lower
        atr_ma = ta.ema(ha_close, self.atr_ma_len)
        atr_val = ta.atr(self.atr_ma_len)
        atr_upper = atr_ma + self.atr_mult * atr_val
        atr_lower = atr_ma - self.atr_mult * atr_val
        atr_in_band = ha_close <= atr_upper and ha_close >= atr_lower
        don_upper = ta.highest(high, self.don_len)
        don_lower = ta.lowest(low, self.don_len)
        don_in_band = ha_close <= don_upper and ha_close >= don_lower
        swing_high = ta.pivothigh(ha_high, self.swing_len, self.swing_len)
        swing_low = ta.pivotlow(ha_low, self.swing_len, self.swing_len)
        if not na(swing_high):
            self.last_sh2 = self.last_sh
            self.last_sh = swing_high
        if not na(swing_low):
            self.last_sl2 = self.last_sl
            self.last_sl = swing_low
        swing_bull_ok = na(self.last_sl2) or self.last_sl > self.last_sl2
        swing_bear_ok = na(self.last_sh2) or self.last_sh < self.last_sh2
        ft = self.filter_type
        if ft == "LinReg csatorna":
            struct_bull = lr_in_band and close > (lr_upper + lr_lower) / 2
            struct_bear = lr_in_band and close < (lr_upper + lr_lower) / 2
        elif ft == "ATR csatorna":
            struct_bull = atr_in_band and ha_close > atr_ma
            struct_bear = atr_in_band and ha_close < atr_ma
        elif ft == "Donchian Channel":
            struct_bull = don_in_band and ha_close > (don_upper + don_lower) / 2
            struct_bear = don_in_band and ha_close < (don_upper + don_lower) / 2
        elif ft == "Swing HL":
            struct_bull = swing_bull_ok
            struct_bear = swing_bear_ok
        else:
            struct_bull = struct_bear = True
        hac = (ha_close, hc_1, hc_2)
        hao = (ha_open, ho_1, ho_2)
        hah = (ha_high, hh_1, hh_2)
        hal = (ha_low, hl_1, hl_2)

        def ha_total(k):
            return hah[k] - hal[k]

        def ha_bullish(k):
            return hac[k] >= hao[k]

        def ha_bearish(k):
            return hac[k] < hao[k]

        def no_upper_wick(k):
            total = ha_total(k)
            upper = hah[k] - pmath.max(hac[k], hao[k])
            return div(upper, total) <= self.wick_tol_pct if total > 0 else True

        def no_lower_wick(k):
            total = ha_total(k)
            lower = pmath.min(hac[k], hao[k]) - hal[k]
            return div(lower, total) <= self.wick_tol_pct if total > 0 else True

        def is_doji(k):
            body = abs(hac[k] - hao[k])
            total = ha_total(k)
            upper = hah[k] - pmath.max(hac[k], hao[k])
            lower = pmath.min(hac[k], hao[k]) - hal[k]
            body_pct = div(body, total) if total > 0 else 1.0
            both_wicks = upper >= body * self.doji_wick_mult and lower >= body * self.doji_wick_mult
            return body_pct <= self.doji_max_pct and both_wicks

        s_size = ha_total(0) > ha_total(1)
        sell_setup = ha_bullish(2) and no_lower_wick(2) and ha_bullish(1) and no_lower_wick(1) and is_doji(0) and s_size
        buy_setup = ha_bearish(2) and no_upper_wick(2) and ha_bearish(1) and no_upper_wick(1) and is_doji(0) and s_size
        long_signal = buy_setup and ha_bull and adx_ok and struct_bull and in_session and vol_ok
        short_signal = sell_setup and ha_bear and adx_ok and struct_bear and in_session and vol_ok
        if long_signal and st.position_size == 0:
            sl = ha_low
            tp = close + (close - sl) * self.rr_ratio
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=sl, limit=tp)
        if short_signal and st.position_size == 0:
            sl = ha_high
            tp = close - (sl - close) * self.rr_ratio
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=sl, limit=tp)
