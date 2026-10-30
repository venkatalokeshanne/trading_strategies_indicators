"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MASU+ Fib [BTT]
Author       : not stated
Source URL   : https://www.tradingview.com/script/QCkIgf3z
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Entry sources: a trend entry (ADX above its threshold, 21/50 EMA cross with the 200 EMA filter, volume spike), a breakout (close above the previous 20-bar high / below the low with a volume spike and the 200 EMA side) and a mean reversion (ADX not trending, close outside the Bollinger band, RSI back across oversold / overbought). Every entry must also pass the higher-timeframe EMA filter, the 8-MA ribbon alignment, the order-flow filter (cumulative up/down volume delta vs its average, volume ratio, daily VWAP side / cross), the Fibonacci swing filter (38.2 / 50 / 61.8 % retracement touch with a wick bounce, or simply the swing direction) and the trading session.
A flat strategy enters with the default 10 % of equity and attaches one exit order at once: ATR stop with an ATR trailing stop (activation = offset = ATR x multiplier ticks) or an ATR stop with an ATR target.
Deviations from the original: none known. Assumption (not verifiable offline): the HMA half length len / 2 is truncated to an integer when passed to ta.wma.
Not carried over: plots, dashboard, S/R and TP/SL lines, the volume-profile point of control, the Kelly size, the volatility-regime and correlation inputs, session labels and the 15m / 1h / 4h dashboard trends (they only feed the display), alerts.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class MasuFib(Script):
    TITLE = "MASU+ Fib [BTT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=0)
    SOURCE = {"id": "QCkIgf3z", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/QCkIgf3z"}

    def init(self):
        i = self.input
        g = "Time Filter"
        self.use_time_filter = i.bool(True, "Trade Only During Session", group=g)
        self.trading_session = i.session("0900-2200", "Trading Hours", group=g)
        g = "Trend Following"
        self.trend_ema_fast = i.int(21, "Trend EMA Fast", minval=5, group=g)
        self.trend_ema_slow = i.int(50, "Trend EMA Slow", minval=10, group=g)
        self.trend_ema_filter = i.int(200, "Trend Filter EMA", minval=50, group=g)
        g = "MTF Filter"
        self.use_mtf_filter = i.bool(True, "Use MTF Filter", group=g)
        self.mtf_timeframe = i.timeframe("240", "Higher Timeframe", group=g)
        self.mtf_ema_fast = i.int(21, "MTF EMA Fast", minval=5, group=g)
        self.mtf_ema_slow = i.int(55, "MTF EMA Slow", minval=10, group=g)
        g = "MA Ribbon"
        self.use_ma_ribbon = i.bool(True, "Use MA Ribbon", group=g)
        self.ribbon_type = i.string("EMA", "Ribbon MA Type", options=["EMA", "SMA", "HMA"], group=g)
        self.ribbon = [i.int(v, "Ribbon MA %d" % (k + 1), minval=2, group=g) for k, v in enumerate((8, 13, 21, 34, 55, 89, 144, 233))]
        self.ribbon_threshold = i.int(6, "Ribbon Alignment Threshold", minval=4, maxval=8, group=g)
        g = "Order Flow"
        self.use_order_flow = i.bool(True, "Enable Order Flow Analysis", group=g)
        self.cvd_length = i.int(20, "CVD Period", minval=1, group=g)
        self.cvd_threshold = i.float(0.6, "CVD Threshold", minval=0.1, maxval=1.0, step=0.1, group=g)
        g = "Fibonacci"
        self.use_fib = i.bool(True, "Enable Fibonacci", group=g)
        self.fib_swing_lb = i.int(15, "Swing Lookback", minval=5, maxval=40, group=g)
        self.fib_min_atr = i.float(1.0, "Min Swing ATR", minval=0.3, maxval=3.0, step=0.1, group=g)
        self.fib_zone = i.float(0.6, "Fib Zone ATR", minval=0.2, maxval=1.5, step=0.1, group=g)
        self.fib_use_382 = i.bool(True, "Use 38.2%", group=g)
        self.fib_use_500 = i.bool(True, "Use 50.0%", group=g)
        self.fib_use_618 = i.bool(True, "Use 61.8%", group=g)
        self.fib_wick_min = i.float(0.25, "Bounce Wick Min", minval=0.1, maxval=0.6, step=0.05, group=g)
        self.breakout_length = i.int(20, "Breakout Period", minval=5, group="Breakout")
        g = "Mean Reversion"
        self.bb_length = i.int(20, "Bollinger Bands Period", minval=5, group=g)
        self.bb_mult = i.float(2.0, "BB Std Dev", minval=0.5, step=0.1, group=g)
        self.rsi_length = i.int(14, "RSI Period", minval=2, group=g)
        self.rsi_ob = i.int(70, "RSI Overbought", minval=50, maxval=100, group=g)
        self.rsi_os = i.int(30, "RSI Oversold", minval=0, maxval=50, group=g)
        g = "Risk Management"
        self.atr_length = i.int(14, "ATR Period", minval=1, group=g)
        self.stop_atr_mult = i.float(2.0, "Stop Loss ATR Multiplier", minval=0.5, step=0.1, group=g)
        self.tp_atr_mult = i.float(3.0, "Take Profit ATR Multiplier", minval=0.5, step=0.1, group=g)
        self.use_trailing = i.bool(True, "Use Trailing Stop", group=g)
        self.trailing_atr_mult = i.float(1.5, "Trailing ATR Multiplier", minval=0.5, step=0.1, group=g)
        g = "Filters"
        self.adx_length = i.int(14, "ADX Period", minval=1, group=g)
        self.adx_threshold = i.int(20, "ADX Threshold", minval=10, maxval=50, group=g)
        self.volume_mult = i.float(1.2, "Volume Multiplier", minval=1.0, step=0.1, group=g)
        self.vwap_sum = 0.0
        self.vol_sum = 0.0
        self.vwap = NA
        self.fib_swH = NA
        self.fib_swHb = 0
        self.fib_swL = NA
        self.fib_swLb = 0

    def _hma(self, src, length):
        w1 = ta.wma(src, int(length / 2))
        w2 = ta.wma(src, length)
        return ta.wma(2 * w1 - w2, int(pmath.round(pmath.sqrt(length))))

    def _ma(self, src, length):
        if self.ribbon_type == "SMA":
            return ta.sma(src, length)
        if self.ribbon_type == "HMA":
            return self._hma(src, length)
        return ta.ema(src, length)

    def on_bar(self):
        st = self.strategy
        close, high, low, open_, volume = self.close, self.high, self.low, self.open, self.volume
        h_cvd = self.H("cvd")
        cvd_1 = h_cvd[1]
        hh_1 = self.H("hh")[1]
        ll_1 = self.H("ll")[1]
        atr = ta.atr(self.atr_length)
        ema_fast = ta.ema(close, self.trend_ema_fast)
        ema_slow = ta.ema(close, self.trend_ema_slow)
        ema_filter = ta.ema(close, self.trend_ema_filter)
        di_plus, di_minus, adx = ta.dmi(self.adx_length, self.adx_length)
        bb_basis = ta.sma(close, self.bb_length)
        bb_dev = self.bb_mult * ta.stdev(close, self.bb_length)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        rsi = ta.rsi(close, self.rsi_length)
        volume_sma = ta.sma(volume, 20)
        volume_spike = volume > volume_sma * self.volume_mult
        highest_high = ta.highest(high, self.breakout_length)
        lowest_low = ta.lowest(low, self.breakout_length)
        r1 = self._ma(close, self.ribbon[0])
        r2 = self._ma(close, self.ribbon[1])
        r3 = self._ma(close, self.ribbon[2])
        r4 = self._ma(close, self.ribbon[3])
        r5 = self._ma(close, self.ribbon[4])
        r6 = self._ma(close, self.ribbon[5])
        r7 = self._ma(close, self.ribbon[6])
        r8 = self._ma(close, self.ribbon[7])
        bull_count = int(r1 > r2) + int(r2 > r3) + int(r3 > r4) + int(r4 > r5) + int(r5 > r6) + int(r6 > r7) + int(r7 > r8)
        bear_count = int(r1 < r2) + int(r2 < r3) + int(r3 < r4) + int(r4 < r5) + int(r5 < r6) + int(r6 < r7) + int(r7 < r8)
        ribbon_bullish = bull_count >= (self.ribbon_threshold - 1)
        ribbon_bearish = bear_count >= (self.ribbon_threshold - 1)
        mtf_fast = self.security(None, self.mtf_timeframe, lambda v: ta.ema(v.close, self.mtf_ema_fast))
        mtf_slow = self.security(None, self.mtf_timeframe, lambda v: ta.ema(v.close, self.mtf_ema_slow))
        mtf_close = self.security(None, self.mtf_timeframe, lambda v: float(v.close))
        mtf_bullish = mtf_fast > mtf_slow and mtf_close > mtf_fast
        mtf_bearish = mtf_fast < mtf_slow and mtf_close < mtf_fast
        mtf_filter_long = (not self.use_mtf_filter) or mtf_bullish
        mtf_filter_short = (not self.use_mtf_filter) or mtf_bearish
        ribbon_filter_long = (not self.use_ma_ribbon) or ribbon_bullish
        ribbon_filter_short = (not self.use_ma_ribbon) or ribbon_bearish

        is_new_day = ta.change(self.time_fn("D")) != 0
        if self.bar_index == 0 or is_new_day:
            self.vwap_sum = 0.0
            self.vol_sum = 0.0
        self.vwap_sum += volume * self.hlc3
        self.vol_sum += volume
        self.vwap = self.vwap_sum / self.vol_sum if self.vol_sum > 0 else float(close)
        vwap = float(self.vwap)
        buy_volume = volume if close > open_ else 0
        sell_volume = volume if close < open_ else 0
        cvd = ta.cum(buy_volume - sell_volume)
        cvd_sma = ta.sma(cvd, self.cvd_length)
        cvd_bullish = cvd > cvd_sma and close < self.close[1] and cvd > cvd_1
        cvd_bearish = cvd < cvd_sma and close > self.close[1] and cvd < cvd_1
        volume_ratio = buy_volume / pmath.max(sell_volume, 1)
        strong_buying = volume_ratio > (1 + self.cvd_threshold)
        strong_selling = volume_ratio < (1 - self.cvd_threshold)
        price_above_vwap = close > vwap
        price_below_vwap = close < vwap
        vwap_cross_up = ta.crossover(close, vwap)
        vwap_cross_down = ta.crossunder(close, vwap)
        of_bullish = self.use_order_flow and ((cvd_bullish or strong_buying) and (vwap_cross_up or price_above_vwap))
        of_bearish = self.use_order_flow and ((cvd_bearish or strong_selling) and (vwap_cross_down or price_below_vwap))
        of_filter_long = (not self.use_order_flow) or of_bullish or price_above_vwap
        of_filter_short = (not self.use_order_flow) or of_bearish or price_below_vwap

        lb = self.fib_swing_lb + 1
        rng_hi = ta.highest(high, lb)
        rng_lo = ta.lowest(low, lb)
        fib_is_sh = high == rng_hi
        fib_is_sl = low == rng_lo
        if fib_is_sh and (high - rng_lo) >= self.fib_min_atr * atr:
            self.fib_swH = float(high)
            self.fib_swHb = self.bar_index
        if fib_is_sl and (rng_hi - low) >= self.fib_min_atr * atr:
            self.fib_swL = float(low)
            self.fib_swLb = self.bar_index
        swH, swL = float(self.fib_swH), float(self.fib_swL)
        fib_ok = (not na(swH)) and (not na(swL)) and self.fib_swHb > 0 and self.fib_swLb > 0
        fib_diff = swH - swL if fib_ok else 0.0
        fib_upswing = fib_ok and self.fib_swHb > self.fib_swLb
        f382 = swH - 0.382 * fib_diff if fib_ok else NA
        f500 = swH - 0.500 * fib_diff if fib_ok else NA
        f618 = swH - 0.618 * fib_diff if fib_ok else NA
        cr = high - low
        b_wick = (pmath.min(open_, close) - low) / cr if cr > 0 else 0.0
        s_wick = (high - pmath.max(open_, close)) / cr if cr > 0 else 0.0
        fz = self.fib_zone * atr
        sw_old = fib_ok and self.bar_index - self.fib_swHb >= 2 and self.bar_index - self.fib_swLb >= 2
        t_l382 = self.fib_use_382 and fib_upswing and not na(f382) and abs(low - f382) <= fz
        t_l500 = self.fib_use_500 and fib_upswing and not na(f500) and abs(low - f500) <= fz
        t_l618 = self.fib_use_618 and fib_upswing and not na(f618) and abs(low - f618) <= fz
        touch_l = t_l382 or t_l500 or t_l618
        near_l = f382 if t_l382 else f500 if t_l500 else f618
        bounce_l = b_wick >= self.fib_wick_min or (close > open_ and close > near_l)
        t_s382 = self.fib_use_382 and not fib_upswing and not na(f382) and abs(high - f382) <= fz
        t_s500 = self.fib_use_500 and not fib_upswing and not na(f500) and abs(high - f500) <= fz
        t_s618 = self.fib_use_618 and not fib_upswing and not na(f618) and abs(high - f618) <= fz
        touch_s = t_s382 or t_s500 or t_s618
        near_s = f382 if t_s382 else f500 if t_s500 else f618
        reject_s = s_wick >= self.fib_wick_min or (close < open_ and close < near_s)
        fib_bullish = self.use_fib and sw_old and touch_l and bounce_l
        fib_bearish = self.use_fib and sw_old and touch_s and reject_s
        fib_filter_long = (not self.use_fib) or fib_bullish or fib_upswing
        fib_filter_short = (not self.use_fib) or fib_bearish or (not fib_upswing)

        is_trending = adx > self.adx_threshold
        is_ranging = adx <= self.adx_threshold
        bullish_trend = ema_fast > ema_slow and close > ema_filter
        bearish_trend = ema_fast < ema_slow and close < ema_filter
        in_session = (not self.use_time_filter) or self.time_in_session(self.trading_session)
        ema_cross_up = ta.crossover(ema_fast, ema_slow)
        ema_cross_down = ta.crossunder(ema_fast, ema_slow)
        rsi_cross_up = ta.crossover(rsi, self.rsi_os)
        rsi_cross_down = ta.crossunder(rsi, self.rsi_ob)
        trend_long = is_trending and bullish_trend and ema_cross_up and volume_spike
        trend_short = is_trending and bearish_trend and ema_cross_down and volume_spike
        breakout_long = close > hh_1 and volume_spike and close > ema_filter
        breakout_short = close < ll_1 and volume_spike and close < ema_filter
        mr_long = is_ranging and close < bb_lower and rsi < self.rsi_os and rsi_cross_up
        mr_short = is_ranging and close > bb_upper and rsi > self.rsi_ob and rsi_cross_down
        long_condition = (trend_long or breakout_long or mr_long) and mtf_filter_long and ribbon_filter_long and of_filter_long and fib_filter_long and in_session
        short_condition = (trend_short or breakout_short or mr_short) and mtf_filter_short and ribbon_filter_short and of_filter_short and fib_filter_short and in_session

        if long_condition and st.position_size == 0:
            stop_loss = close - (atr * self.stop_atr_mult)
            take_profit = close + (atr * self.tp_atr_mult)
            st.entry("Long", st.long)
            if self.use_trailing:
                st.exit("Exit Long", "Long", stop=stop_loss, trail_offset=atr * self.trailing_atr_mult, trail_points=atr * self.trailing_atr_mult)
            else:
                st.exit("Exit Long", "Long", stop=stop_loss, limit=take_profit)
        if short_condition and st.position_size == 0:
            stop_loss = close + (atr * self.stop_atr_mult)
            take_profit = close - (atr * self.tp_atr_mult)
            st.entry("Short", st.short)
            if self.use_trailing:
                st.exit("Exit Short", "Short", stop=stop_loss, trail_offset=atr * self.trailing_atr_mult, trail_points=atr * self.trailing_atr_mult)
            else:
                st.exit("Exit Short", "Short", stop=stop_loss, limit=take_profit)
        h_cvd.set(cvd)
        self.H("hh").set(highest_high)
        self.H("ll").set(lowest_low)
