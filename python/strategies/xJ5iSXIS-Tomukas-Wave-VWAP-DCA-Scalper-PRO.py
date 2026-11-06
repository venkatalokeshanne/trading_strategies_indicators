"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Tomukas Wave VWAP DCA Scalper PRO Clean Confirmed
Author       : Tomukasss
Source URL   : https://www.tradingview.com/script/xJ5iSXIS-Tomukas-Wave-VWAP-DCA-Scalper-PRO
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). A confirmed long needs the close over the 200 EMA, the 50 EMA over the 200 EMA, the close above a range filter, a WaveTrend cross-up, RSI over 50 with volume over its average, the close over the VWAP, a momentum confirmation (RSI / MACD / 20 EMA), a volume-profile zone
(the close over the latest highest-volume bar's price, or near it) and a close above the previous high (shorts mirror it). From a flat position it enters 0.5 units and records the entry; each further 1 % (input) move against it adds a larger lot (0.5, 1, 2, 4 - the last is beyond the pyramiding limit of 4). The whole basket is closed at the take-profit or the drawdown-stop percentage of the average price.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, ta


class TomukasWaveVwapDca(Script):
    TITLE = "Tomukas Wave VWAP DCA Scalper PRO Clean Confirmed"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=4, process_orders_on_close=True, default_qty_type="percent_of_equity")
    SOURCE = {"id": "xJ5iSXIS", "author": "Tomukasss", "licence": "not stated", "url": "https://www.tradingview.com/script/xJ5iSXIS-Tomukas-Wave-VWAP-DCA-Scalper-PRO"}

    def init(self):
        i = self.input
        self.ema_len = i.int(200, "EMA Trend Length")
        self.tp_perc = i.float(0.6, "Basket TP %", step=0.1)
        self.dd_stop_perc = i.float(4.0, "Basket DD Stop %", step=0.1)
        self.add_step_perc = i.float(1.0, "DCA Add Every % Against", step=0.1)
        self.use_session = i.bool(False, "Use Session Filter")
        self.trade_sess = i.session("0930-1600", "Trade Session")
        self.tz = i.string("America/New_York", "Timezone")
        self.use_vwap = i.bool(True, "Use VWAP Filter")
        self.use_momentum = i.bool(True, "Use Momentum Confirm")
        self.use_vol_zone = i.bool(True, "Use Volume Profile Zone")
        self.smooth_len = i.int(27, "Range Smooth Length")
        self.sens = i.float(1.8, "Range Sensitivity", step=0.1)
        self.wt_fast = i.int(9, "Wave Fast")
        self.wt_slow = i.int(6, "Wave Slow")
        self.vp_lookback = i.int(80, "Volume Profile Lookback")
        self.range_filter = NA
        self.volume_node = NA
        self.dca_count = 0
        self.first_entry = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        ema200 = ta.ema(close, self.ema_len)
        ema50 = ta.ema(close, 50)
        ema20 = ta.ema(close, 20)
        vwap_val = ta.vwap(self.hlc3)
        trend_up = ema50 > ema200
        trend_down = ema50 < ema200
        in_session = (not self.use_session) or self.time_in_session(self.trade_sess, self.tz)
        range_base = ta.ema(abs(close - self.close[1]), self.smooth_len)
        range_smooth = ta.ema(range_base, self.smooth_len * 2 - 1) * self.sens
        prev_range = float(nz(self.range_filter, close))
        if close > prev_range:
            self.range_filter = prev_range if close - range_smooth < prev_range else close - range_smooth
        else:
            self.range_filter = prev_range if close + range_smooth > prev_range else close + range_smooth
        range_bull = close > self.range_filter
        range_bear = close < self.range_filter
        esa = ta.ema(self.hlc3, self.wt_fast)
        dev = ta.ema(abs(self.hlc3 - esa), self.wt_fast)
        wave = ta.ema(div(self.hlc3 - esa, 0.015 * dev), self.wt_slow)
        wave_signal = ta.sma(wave, 3)
        wave_bull_cross = ta.crossover(wave, wave_signal)
        wave_bear_cross = ta.crossunder(wave, wave_signal)
        rsi = ta.rsi(close, 14)
        macd = ta.ema(close, 12) - ta.ema(close, 26)
        macd_signal = ta.ema(macd, 9)
        mom_bull = (not self.use_momentum) or (rsi > 50 and macd > macd_signal and close > ema20)
        mom_bear = (not self.use_momentum) or (rsi < 50 and macd < macd_signal and close < ema20)
        vol_ma = ta.sma(self.volume, 20)
        vol_ok = self.volume > vol_ma
        high_vol_bar = self.volume == ta.highest(self.volume, self.vp_lookback)
        if high_vol_bar:
            self.volume_node = float(self.hlc3)
        near_vol_node = (not na(self.volume_node)) and div(abs(close - self.volume_node), close) < 0.003
        vol_zone_long = (not self.use_vol_zone) or na(self.volume_node) or close > self.volume_node or near_vol_node
        vol_zone_short = (not self.use_vol_zone) or na(self.volume_node) or close < self.volume_node or near_vol_node
        vwap_long = (not self.use_vwap) or close > vwap_val
        vwap_short = (not self.use_vwap) or close < vwap_val
        bull_pressure = rsi > 50 and vol_ok
        bear_pressure = rsi < 50 and vol_ok
        high_1, low_1 = self.high[1], self.low[1]
        confirmed_long = (close > ema200 and trend_up and range_bull and wave_bull_cross and bull_pressure and vwap_long and mom_bull and vol_zone_long and close > high_1)
        confirmed_short = (close < ema200 and trend_down and range_bear and wave_bear_cross and bear_pressure and vwap_short and mom_bear and vol_zone_short and close < low_1)
        long_signal = in_session and st.position_size == 0 and st.opentrades == 0 and confirmed_long
        short_signal = in_session and st.position_size == 0 and st.opentrades == 0 and confirmed_short
        if st.position_size == 0:
            self.dca_count = 0
            self.first_entry = NA
        if long_signal:
            st.entry("L1", st.long, qty=0.5)
            self.first_entry = float(close)
            self.dca_count = 1
        if short_signal:
            st.entry("S1", st.short, qty=0.5)
            self.first_entry = float(close)
            self.dca_count = 1
        step = self.add_step_perc
        pos = st.position_size
        fe = self.first_entry
        long_adds = [pos > 0 and self.dca_count == k and close <= fe * (1 - step * k / 100) for k in (1, 2, 3, 4)]
        short_adds = [pos < 0 and self.dca_count == k and close >= fe * (1 + step * k / 100) for k in (1, 2, 3, 4)]
        qtys = (0.5, 1, 2, 4)
        for k in range(4):
            if long_adds[k]:
                st.entry("L%d" % (k + 2), st.long, qty=qtys[k])
                self.dca_count = k + 2
        for k in range(4):
            if short_adds[k]:
                st.entry("S%d" % (k + 2), st.short, qty=qtys[k])
                self.dca_count = k + 2
        avg = st.position_avg_price
        long_tp = pos > 0 and close >= avg * (1 + self.tp_perc / 100)
        short_tp = pos < 0 and close <= avg * (1 - self.tp_perc / 100)
        long_dd = pos > 0 and close <= avg * (1 - self.dd_stop_perc / 100)
        short_dd = pos < 0 and close >= avg * (1 + self.dd_stop_perc / 100)
        if long_tp:
            st.close_all("Long Basket TP")
        if short_tp:
            st.close_all("Short Basket TP")
        if long_dd:
            st.close_all("Long DD Stop")
        if short_dd:
            st.close_all("Short DD Stop")
