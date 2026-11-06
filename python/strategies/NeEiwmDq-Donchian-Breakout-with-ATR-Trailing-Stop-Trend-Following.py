"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC BTCUSD · capital.com · Trailing v3 FINAL (Donchian Breakout with ATR Trailing Stop)
Author       : raven_suurineru
Source URL   : https://www.tradingview.com/script/NeEiwmDq-Donchian-Breakout-with-ATR-Trailing-Stop-Trend-Following
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close above the previous N bars' highest high (below the lowest low for shorts, off by default) with the EMA200 trend filter enters at the close, sized to
risk a percent of equity over the ATR trail distance (capped by leverage). On the first script run with the position (the bar after the fill) the trailing stop is set from the average price and the CURRENT
ATR distance, then ratchets with highs minus that fixed distance; the stop is re-issued every bar. On Fridays from the configured UTC hour everything is closed and no new entries are made.

Deviations from the original: none.
Not carried over: alert() texts, the EMA / channel / stop plots and the breakout shape (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class DonchianAtrTrail(Script):
    TITLE = "BTC BTCUSD · capital.com · Trailing v3 FINAL"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=4000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.03, pyramiding=0,
                    process_orders_on_close=True, margin_long=50.0, margin_short=50.0)
    SOURCE = {"id": "NeEiwmDq", "author": "raven_suurineru", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NeEiwmDq-Donchian-Breakout-with-ATR-Trailing-Stop-Trend-Following"}

    def init(self):
        g = "Risk manažment"
        self.risk_pct = self.input.float(0.9, "Risk na obchod (%)", minval=0.1, maxval=10, step=0.1, group=g)
        self.use_equity = self.input.bool(True, "Risk z aktuálneho equity (compounding)", group=g)
        self.use_risk_cap = self.input.bool(False, "Použiť dolárový strop rizika", group=g)
        self.risk_cap_usd = self.input.float(150, "Max riziko na obchod (USD)", minval=1, step=5, group=g)
        self.leverage = self.input.int(2, "Páka", minval=1, group=g)
        self.entry_len = self.input.int(20, "Vstupný kanál (prerazenie N-bar maxima)", minval=2, group="Breakout")
        g = "Trend filter"
        self.trend_len = self.input.int(200, "Trendový filter EMA", minval=1, group=g)
        self.use_trend_filt = self.input.bool(True, "Obchoduj len v smere 200 EMA", group=g)
        g = "Trailing stop"
        self.atr_len = self.input.int(14, "ATR perióda", minval=1, group=g)
        self.trail_mult = self.input.float(2.5, "Vzdialenosť trailingu (× ATR)", minval=0.1, step=0.1, group=g)
        g = "Smer"
        self.allow_long = self.input.bool(True, "Povoliť LONG", group=g)
        self.allow_short = self.input.bool(False, "Povoliť SHORT", group=g)
        g = "Víkend"
        self.use_wknd_flat = self.input.bool(True, "Zatvoriť pozíciu pred víkendom (BTC beží 24/7 – voliteľné)", group=g)
        self.fri_exit_hr = self.input.int(20, "Hodina zatvorenia v piatok (UTC)", minval=0, maxval=23, group=g)
        self.trail_dist = NA
        self.trail_stop = NA

    def on_bar(self):
        upper_entry = self.H("up")[1]
        lower_entry = self.H("lo")[1]
        self.H("up").set(ta.highest(self.high, self.entry_len))
        self.H("lo").set(ta.lowest(self.low, self.entry_len))
        ema_trend = ta.ema(self.close, self.trend_len)
        atr = ta.atr(self.atr_len)
        trend_up_ok = (not self.use_trend_filt) or self.close > ema_trend
        trend_dn_ok = (not self.use_trend_filt) or self.close < ema_trend
        is_wknd_close = self.use_wknd_flat and self.dayofweek(self.time, "UTC") == 6 and self.hour(self.time, "UTC") >= self.fri_exit_hr
        long_signal = self.allow_long and self.close > upper_entry and trend_up_ok and not is_wknd_close
        short_signal = self.allow_short and self.close < lower_entry and trend_dn_ok and not is_wknd_close
        st = self.strategy
        capital_base = st.equity if self.use_equity else st.initial_capital
        risk_amount = capital_base * self.risk_pct / 100.0
        risk_amount = pmath.min(risk_amount, self.risk_cap_usd) if self.use_risk_cap else risk_amount
        sl_dist = atr * self.trail_mult
        qty_raw = div(risk_amount, sl_dist) if sl_dist > 0 else NA
        max_qty = div(capital_base * self.leverage, self.close)
        qty = pmath.min(qty_raw, max_qty) if not na(qty_raw) else NA
        pos_prev = self.H("pos")[1]
        self.H("pos").set(st.position_size)
        if long_signal and st.position_size == 0 and not na(qty):
            st.entry("Long", st.long, qty=qty)
        if short_signal and st.position_size == 0 and not na(qty):
            st.entry("Short", st.short, qty=qty)
        prev0 = 0 if na(pos_prev) else pos_prev
        long_just_in = st.position_size > 0 and prev0 <= 0
        short_just_in = st.position_size < 0 and prev0 >= 0
        if long_just_in:
            self.trail_dist = sl_dist
            self.trail_stop = st.position_avg_price - self.trail_dist
        elif st.position_size > 0:
            self.trail_stop = pmath.max(self.trail_stop, self.high - self.trail_dist)
        if short_just_in:
            self.trail_dist = sl_dist
            self.trail_stop = st.position_avg_price + self.trail_dist
        elif st.position_size < 0:
            self.trail_stop = pmath.min(self.trail_stop, self.low + self.trail_dist)
        if st.position_size > 0:
            st.exit("Long exit", from_entry="Long", stop=self.trail_stop)
        if st.position_size < 0:
            st.exit("Short exit", from_entry="Short", stop=self.trail_stop)
        if st.position_size == 0:
            self.trail_dist = NA
            self.trail_stop = NA
        if is_wknd_close and st.position_size != 0:
            st.close_all(comment="Pred víkendom")
        self.plot(ema_trend, "200 EMA", color=color.green if self.close > ema_trend else color.red, linewidth=2)
        self.plot(upper_entry, "Vstup kanál", color=color.blue)
        self.plot(self.trail_stop if st.position_size != 0 else NA, "Trailing stop", color=color.orange, linewidth=2)
