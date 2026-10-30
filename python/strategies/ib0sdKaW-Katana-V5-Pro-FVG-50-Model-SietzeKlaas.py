"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Katana V5 Pro FVG 50% Model [SietzeKlaas]
Author       : SietzeKlaas
Source URL   : https://www.tradingview.com/script/ib0sdKaW-Katana-V5-Pro-FVG-50-Model-SietzeKlaas
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A fair value gap candle (bullish: low above the high two bars back) that passes the ATR displacement, EMA trend, RSI and session filters arms a setup whose entry is the 50 % level of the swing range, the stop the 25 % level and the target the 75 % level (or 1R / 1.5R / 2R); the setup expires after a number of bars, and the market entry is made at the close of the first bar whose range touches the entry level. Position size is a fixed quantity or risk-based on equity.

Deviations from the original: none.
Not carried over: labels, FVG boxes, level lines and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class KatanaV5Pro(Script):
    TITLE = "Katana V5 Pro FVG 50% Model [SietzeKlaas]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, process_orders_on_close=True, commission_type="cash_per_contract", commission_value=0.0)
    SOURCE = {"id": "ib0sdKaW", "author": "SietzeKlaas", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ib0sdKaW-Katana-V5-Pro-FVG-50-Model-SietzeKlaas"}

    def init(self):
        i = self.input
        self.trade_mode = i.string("Risk Based", "Position sizing mode", options=["Fixed Qty", "Risk Based"])
        self.fixed_qty = i.float(1.0, "Fixed qty/contracts", minval=0.01, step=0.01)
        self.use_compounding = i.bool(True, "Use compounding")
        self.risk_percent = i.float(1.0, "Risk % per trade", minval=0.01, maxval=20.0, step=0.1)
        self.swing_lookback = i.int(20, "Swing lookback", minval=3, maxval=200)
        self.setup_expire_bars = i.int(10, "Setup expires after candles", minval=1, maxval=100)
        self.use_atr_disp = i.bool(True, "Use ATR displacement filter")
        self.atr_length = i.int(14, "ATR length", minval=1)
        self.atr_mult = i.float(1.0, "Minimum displacement ATR multiplier", minval=0.1, step=0.1)
        self.use_trend = i.bool(True, "Use EMA trend filter")
        self.ema_length = i.int(200, "EMA length", minval=1)
        self.use_rsi = i.bool(True, "Use RSI filter")
        self.rsi_length = i.int(14, "RSI length", minval=1)
        self.long_rsi_min = i.float(50.0, "Long RSI minimum", minval=1, maxval=99, step=0.5)
        self.short_rsi_max = i.float(50.0, "Short RSI maximum", minval=1, maxval=99, step=0.5)
        self.use_session = i.bool(True, "Use session filter")
        self.trade_session = i.session("0800-1800", "Trading session")
        self.session_tz = i.string("Etc/UTC", "Session timezone")
        self.use_min_stop = i.bool(True, "Use minimum stop distance filter")
        self.min_stop_distance = i.float(3.0, "Minimum stop distance in price", minval=0.0, step=0.1)
        self.tp_mode = i.string("Katana Original", "Take profit mode", options=["Katana Original", "1R", "1.5R", "2R"])
        self.allow_longs = i.bool(True, "Allow longs")
        self.allow_shorts = i.bool(True, "Allow shorts")
        self.setup_active = False
        self.setup_side = ""
        self.setup_bar = NA
        self.setup_entry = NA
        self.setup_stop = NA
        self.setup_tp = NA
        self.setup_qty = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        atr = ta.atr(self.atr_length)
        ema = ta.ema(close, self.ema_length)
        rsi = ta.rsi(close, self.rsi_length)
        in_session = not na(self.time_fn(None, self.trade_session, self.session_tz))
        session_ok = (not self.use_session) or in_session
        bull_fvg = low > high[2]
        bear_fvg = high < low[2]
        candle_range = high - low
        valid_disp = (not self.use_atr_disp) or candle_range >= atr * self.atr_mult
        bull_raw = bull_fvg and close > open_ and valid_disp
        bear_raw = bear_fvg and close < open_ and valid_disp
        long_trend_ok = (not self.use_trend) or close > ema
        short_trend_ok = (not self.use_trend) or close < ema
        long_rsi_ok = (not self.use_rsi) or rsi >= self.long_rsi_min
        short_rsi_ok = (not self.use_rsi) or rsi <= self.short_rsi_max
        bull_signal = bull_raw and long_trend_ok and long_rsi_ok and session_ok
        bear_signal = bear_raw and short_trend_ok and short_rsi_ok and session_ok
        if self.setup_active and st.position_size == 0 and not na(self.setup_bar):
            if self.bar_index - self.setup_bar > self.setup_expire_bars:
                self.setup_active = False
                self.setup_side = ""
                self.setup_entry = NA
                self.setup_stop = NA
                self.setup_tp = NA
                self.setup_qty = NA
        if st.position_size != 0:
            self.setup_active = False
        can_create = st.position_size == 0 and not self.setup_active
        long_range_low = ta.lowest(low, self.swing_lookback)
        long_range = high - long_range_low
        long_entry = long_range_low + long_range * 0.50
        long_stop = long_range_low + long_range * 0.25
        long_katana_tp = long_range_low + long_range * 0.75
        long_risk = abs(long_entry - long_stop)
        if self.tp_mode == "Katana Original":
            long_tp = long_katana_tp
        elif self.tp_mode == "1R":
            long_tp = long_entry + long_risk * 1.0
        elif self.tp_mode == "1.5R":
            long_tp = long_entry + long_risk * 1.5
        else:
            long_tp = long_entry + long_risk * 2.0
        valid_long_range = long_range > mintick and long_stop < long_entry and long_tp > long_entry
        short_range_high = ta.highest(high, self.swing_lookback)
        short_range = short_range_high - low
        short_entry = short_range_high - short_range * 0.50
        short_stop = short_range_high - short_range * 0.25
        short_katana_tp = short_range_high - short_range * 0.75
        short_risk = abs(short_stop - short_entry)
        if self.tp_mode == "Katana Original":
            short_tp = short_katana_tp
        elif self.tp_mode == "1R":
            short_tp = short_entry - short_risk * 1.0
        elif self.tp_mode == "1.5R":
            short_tp = short_entry - short_risk * 1.5
        else:
            short_tp = short_entry - short_risk * 2.0
        valid_short_range = short_range > mintick and short_stop > short_entry and short_tp < short_entry
        long_stop_ok = (not self.use_min_stop) or long_risk >= self.min_stop_distance
        short_stop_ok = (not self.use_min_stop) or short_risk >= self.min_stop_distance
        equity_for_sizing = st.equity if self.use_compounding else st.initial_capital
        risk_cash = equity_for_sizing * (self.risk_percent / 100.0)
        long_rpc = long_risk * self.syminfo.pointvalue
        short_rpc = short_risk * self.syminfo.pointvalue
        long_risk_qty = div(risk_cash, long_rpc) if long_rpc > 0 else NA
        short_risk_qty = div(risk_cash, short_rpc) if short_rpc > 0 else NA
        long_qty = self.fixed_qty if self.trade_mode == "Fixed Qty" else long_risk_qty
        short_qty = self.fixed_qty if self.trade_mode == "Fixed Qty" else short_risk_qty
        valid_long_qty = (not na(long_qty)) and long_qty > 0
        valid_short_qty = (not na(short_qty)) and short_qty > 0
        if self.allow_longs and can_create and bull_signal and valid_long_range and long_stop_ok and valid_long_qty:
            self.setup_active = True
            self.setup_side = "LONG"
            self.setup_bar = self.bar_index
            self.setup_entry = long_entry
            self.setup_stop = long_stop
            self.setup_tp = long_tp
            self.setup_qty = long_qty
        if self.allow_shorts and can_create and bear_signal and valid_short_range and short_stop_ok and valid_short_qty:
            self.setup_active = True
            self.setup_side = "SHORT"
            self.setup_bar = self.bar_index
            self.setup_entry = short_entry
            self.setup_stop = short_stop
            self.setup_tp = short_tp
            self.setup_qty = short_qty
        long_touch = self.setup_active and self.setup_side == "LONG" and st.position_size == 0 and low <= self.setup_entry and high >= self.setup_entry
        short_touch = self.setup_active and self.setup_side == "SHORT" and st.position_size == 0 and low <= self.setup_entry and high >= self.setup_entry
        if long_touch:
            st.entry("Katana Long", st.long, qty=self.setup_qty)
            st.exit("Katana Long TP/SL", from_entry="Katana Long", stop=self.setup_stop, limit=self.setup_tp)
            self.setup_active = False
        if short_touch:
            st.entry("Katana Short", st.short, qty=self.setup_qty)
            st.exit("Katana Short TP/SL", from_entry="Katana Short", stop=self.setup_stop, limit=self.setup_tp)
            self.setup_active = False
