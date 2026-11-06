"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ICT 2022 NAS100 | Smart Trend v2.0
Author       : not stated
Source URL   : https://www.tradingview.com/script/tDFJR5PV-ICT-2022-NAS100-Smart-Trend-v2-0
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Inside Israel-time killzones (Asian, London, NY, NY lunch) a close through the latest pivot high (low) of the session with a displacement candle (body larger than a multiple of the average body)
and the 60-minute close above (below) its EMA (the EMA runs on the mapped chart-bar series, as in the original) enters long (short); the stop is ATR x multiplier (or the previous bar's extreme) from the close and the target is R:R times that distance, issued with the entry.
A cooldown between trades and a minimum stop (in ticks) apply.
Deviations from the original: none (the second identical request.security call is merged with the first).
Not carried over: killzone tint, pivot / sweep / MSS markers, the H1 EMA plot, bar colours and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class IctNas100SmartTrend(Script):
    TITLE = "ICT 2022 NAS100 | Smart Trend v2.0"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=1, initial_capital=10000,
                    commission_type="percent", commission_value=0.02, slippage=2)
    SOURCE = {"id": "tDFJR5PV", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/tDFJR5PV-ICT-2022-NAS100-Smart-Trend-v2-0"}

    def init(self):
        i = self.input
        g = "Killzone Times — Israel Time (UTC+3)"
        self.use_asian = i.bool(True, "Asian Session", group=g)
        self.asian_s = i.int(2, "Asian Start Hour", group=g, minval=0, maxval=23)
        self.asian_e = i.int(5, "Asian End Hour", group=g, minval=0, maxval=23)
        self.use_london = i.bool(True, "London Session", group=g)
        self.lon_s = i.int(9, "London Start Hour", group=g, minval=0, maxval=23)
        self.lon_e = i.int(12, "London End Hour", group=g, minval=0, maxval=23)
        self.use_ny = i.bool(True, "NY Session", group=g)
        self.ny_s_h = i.int(15, "NY Start Hour", group=g, minval=0, maxval=23)
        self.ny_s_m = i.int(30, "NY Start Minute", group=g, minval=0, maxval=59)
        self.ny_e_h = i.int(18, "NY End Hour", group=g, minval=0, maxval=23)
        self.ny_e_m = i.int(30, "NY End Minute", group=g, minval=0, maxval=59)
        self.use_lunch = i.bool(True, "NY Lunch Reversal", group=g)
        self.lunch_s = i.int(19, "Lunch Start Hour", group=g, minval=0, maxval=23)
        self.lunch_e = i.int(21, "Lunch End Hour", group=g, minval=0, maxval=23)
        self.utc_offset = i.int(3, "Israel UTC Offset (3=summer / 2=winter)", group=g, minval=-12, maxval=14)
        g = "H1 Trend Filter"
        self.use_trend = i.bool(True, "Enable H1 EMA Trend Filter", group=g)
        self.ema_len = i.int(50, "EMA Period", group=g, minval=5)
        g = "ICT Trade Logic"
        self.swing_lb = i.int(2, "Pivot Lookback (bars each side)", group=g, minval=1, maxval=10)
        self.disp_mult = i.float(1.3, "Displacement Multiplier", group=g, step=0.1, minval=0.5, maxval=5.0)
        self.req_sweep = i.bool(False, "Require Liquidity Sweep", group=g)
        self.min_sl_pts = i.float(30.0, "Min SL (Points for NAS100)", group=g, step=5)
        self.use_atr_sl = i.bool(True, "Use ATR-based SL (smarter)", group=g)
        self.atr_sl_mult = i.float(1.5, "ATR SL Multiplier", group=g, step=0.1, minval=0.5, maxval=5.0)
        self.cooldown = i.int(4, "Cooldown Bars Between Trades", group=g, minval=1, maxval=50)
        g = "Risk Management"
        self.risk_pct = i.float(1.0, "Risk % per Trade", group=g, step=0.1, minval=0.1, maxval=10.0)
        self.rr_ratio = i.float(2.0, "Risk:Reward Ratio", group=g, step=0.1, minval=0.5, maxval=10.0)
        g = "Direction Settings"
        self.enable_long = i.bool(True, "Enable LONG trades", group=g)
        self.enable_short = i.bool(True, "Enable SHORT trades", group=g)
        self.local_high = NA
        self.local_low = NA
        self.swept_high = False
        self.swept_low = False
        self.last_trade_bar = -999

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        tz = "Asia/Jerusalem"
        h1_close = self.security(None, "60", lambda v: v.close)
        h1_ema = ta.ema(h1_close, self.ema_len)
        is_bull = h1_close > h1_ema
        is_bear = h1_close < h1_ema
        atr14 = ta.atr(14)
        tot = self.hour(self.time, tz) * 60 + self.minute(self.time, tz)
        in_asian = self.use_asian and (tot >= self.asian_s * 60 and tot < self.asian_e * 60)
        in_london = self.use_london and (tot >= self.lon_s * 60 and tot < self.lon_e * 60)
        in_ny = self.use_ny and (tot >= self.ny_s_h * 60 + self.ny_s_m and tot < self.ny_e_h * 60 + self.ny_e_m)
        in_lunch = self.use_lunch and (tot >= self.lunch_s * 60 and tot < self.lunch_e * 60)
        in_kz = bool(in_asian or in_london or in_ny or in_lunch)
        kz_h = self.H("in_kz")
        in_kz_1 = kz_h[1]
        kz_h.set(1.0 if in_kz else 0.0)
        session_change = in_kz and not (in_kz_1 == 1.0)
        ph = ta.pivothigh(high, self.swing_lb, self.swing_lb)
        pl = ta.pivotlow(low, self.swing_lb, self.swing_lb)
        if session_change:
            self.local_high = NA
            self.local_low = NA
        if not na(ph):
            self.local_high = float(ph)
        if not na(pl):
            self.local_low = float(pl)
        if session_change:
            self.swept_high = False
            self.swept_low = False
        if in_kz:
            if not na(self.local_high) and high > self.local_high:
                self.swept_high = True
            if not na(self.local_low) and low < self.local_low:
                self.swept_low = True
        body_now = abs(close - open_)
        bh = self.H("body_prev")
        body_prev = bh[1]
        bh.set(body_now)
        avg_body = ta.sma(body_prev, 20)
        is_disp = avg_body > 0 and body_now > avg_body * self.disp_mult
        mss_bull = (not na(self.local_high)) and close > self.local_high and is_disp and in_kz and ((not self.req_sweep) or self.swept_low) and (is_bull if self.use_trend else True)
        mss_bear = (not na(self.local_low)) and close < self.local_low and is_disp and in_kz and ((not self.req_sweep) or self.swept_high) and (is_bear if self.use_trend else True)
        cooldown_ok = self.bar_index > self.last_trade_bar + self.cooldown
        lh, hh = self.H("low_prev"), self.H("high_prev")
        low_1, high_1 = lh[1], hh[1]
        lh.set(low)
        hh.set(high)
        atr_sl_long = atr14 * self.atr_sl_mult if self.use_atr_sl else abs(close - low_1)
        atr_sl_short = atr14 * self.atr_sl_mult if self.use_atr_sl else abs(high_1 - close)
        long_ok = self.enable_long and mss_bull and cooldown_ok and st.opentrades == 0
        short_ok = self.enable_short and mss_bear and cooldown_ok and st.opentrades == 0
        mintick = self.syminfo.mintick
        long_valid = div(atr_sl_long, mintick) >= self.min_sl_pts
        short_valid = div(atr_sl_short, mintick) >= self.min_sl_pts
        if long_ok and long_valid:
            sl_price = close - atr_sl_long
            tp_price = close + atr_sl_long * self.rr_ratio
            st.entry("LONG", st.long, comment="ICT LONG")
            st.exit("LONG_X", "LONG", stop=sl_price, limit=tp_price, comment="ICT EXIT")
            self.last_trade_bar = self.bar_index
            self.swept_low = False
            self.local_high = NA
        if short_ok and short_valid:
            sl_price = close + atr_sl_short
            tp_price = close - atr_sl_short * self.rr_ratio
            st.entry("SHORT", st.short, comment="ICT SHORT")
            st.exit("SHORT_X", "SHORT", stop=sl_price, limit=tp_price, comment="ICT EXIT")
            self.last_trade_bar = self.bar_index
            self.swept_high = False
            self.local_low = NA
