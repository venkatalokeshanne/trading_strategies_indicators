"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ULTIMATE TEMA/LSMA + IDEAL + REVERSAL + INSTITUTIONAL + DAVIN MA [DYNAMIC]
Author       : AhtishamQureshi
Source URL   : https://www.tradingview.com/script/gOQ0eQvL
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders fill at the signal bar's close: process_orders_on_close). A signal source is picked by priority (institutional zone from the 20-bar swing low / high, IDEAL sweeps / retests / oversold confluence, reversal consensus, Davin's moving-average dip buy, the TEMA / LSMA cross) and a position opens only when flat, sized as equity / close x percent.
While a position is open one exit order per side is re-issued every bar: ATR stop and target around the average price (the institutional multipliers apply when the CURRENT bar's signal source is institutional) and a trailing stop whose activation and offset are the ATR in ticks. A trade is closed after the maximum number of bars.
Instrument detection (gold / bitcoin / ethereum) reads the full ticker id as the source does.
Deviations from the original: none.
Not carried over: the Williams %R higher-timeframe request (its value is never used), plots, fills, signal shapes, the information table, and the CHoCH swing / liquidity-zone levels (they only feed plots).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class UltimateTemaLsma(Script):
    TITLE = "ULTIMATE TEMA/LSMA + IDEAL + REVERSAL + INSTITUTIONAL + DAVIN MA [DYNAMIC]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "gOQ0eQvL", "author": "AhtishamQureshi", "licence": "Mozilla Public License 2.0", "url": "https://www.tradingview.com/script/gOQ0eQvL"}

    def init(self):
        i = self.input
        self.tema_length = i.int(9, "TEMA Length", minval=1, maxval=50)
        self.lsma_length = i.int(25, "LSMA Length", minval=1, maxval=50)
        self.ema100_length = i.int(100, "EMA 100 Length", minval=50, maxval=200)
        self.tp_atr_mult = i.float(3.0, "TP ATR Mult", minval=2.0, maxval=5.0)
        self.sl_atr_mult = i.float(1.5, "SL ATR Mult", minval=1.0, maxval=3.0)
        self.trail_atr_mult = i.float(1.0, "Trail ATR Mult", minval=0.5, maxval=3.0)
        self.max_bars_in_trade = i.int(25, "Max Bars in Trade", minval=10, maxval=50)
        self.vol_length = i.int(20, "Volume MA Length", minval=10, maxval=30)
        self.min_vol_mult = i.float(1.2, "Volume Multiplier", minval=0.8, maxval=2.0)
        g = "Trend Filters"
        self.use_trend_exhaustion = i.bool(True, "Use Trend Exhaustion Filter", group=g)
        self.min_trend_bars = i.int(10, "Min Trend Bars", minval=5, maxval=30, group=g)
        self.momentum_divergence = i.bool(True, "Use Momentum Divergence", group=g)
        self.require_trend_alignment = i.bool(True, "Require All Indicators Aligned", group=g)
        self.use_trend_strength = i.bool(True, "Use Trend Strength Filter", group=g)
        self.trend_strength_threshold = i.float(0.5, "Trend Strength Threshold", minval=0.1, maxval=1.0, group=g)
        g = "Ideal Conditions"
        self.use_ideal = i.bool(True, "Use IDEAL Conditions (Priority)", group=g)
        self.pivot_lookback = i.int(5, "Pivot Lookback for Sweeps", minval=3, maxval=20, group=g)
        self.min_sweep_size_atr = i.float(0.3, "Min Sweep Size (ATR %)", minval=0.1, maxval=1.0, group=g)
        self.retest_tolerance = i.float(0.001, "Retest Tolerance (%)", minval=0.0005, maxval=0.01, group=g)
        self.max_test_count = i.int(3, "Max Tests Before Failure", minval=2, maxval=5, group=g)
        self.atr_test_percent = i.float(0.2, "ATR Test %", minval=0.1, maxval=0.5, group=g)
        g = "Reversal Strategy"
        self.enable_reversals = i.bool(True, "Enable Reversal Trades?", group=g)
        self.kama_length_rev = i.int(10, "KAMA Length", minval=5, maxval=20, group=g)
        self.adx_length = i.int(14, "ADX Length", minval=10, maxval=30, group=g)
        self.adx_strong_trend = i.float(20.0, "ADX Strong Trend", minval=15, maxval=30, group=g)
        self.rsi_length = i.int(14, "RSI Length", minval=10, maxval=30, group=g)
        self.rsi_ob = i.float(70.0, "RSI Overbought", minval=60, maxval=80, group=g)
        self.rsi_os = i.float(30.0, "RSI Oversold", minval=20, maxval=40, group=g)
        self.williams_length = i.int(14, "Williams %R Length", minval=10, maxval=30, group=g)
        self.williams_ob = i.float(-20.0, "Williams %R OB", minval=-30, maxval=-10, group=g)
        self.williams_os = i.float(-80.0, "Williams %R OS", minval=-90, maxval=-70, group=g)
        self.williams_htf_tf = i.timeframe("30", "Williams HTF", group=g)
        self.liquidity_zone_bars = i.int(8, "Liquidity Zone Bars", minval=5, maxval=15, group=g)
        self.min_vol_mult_rev = i.float(1.0, "Volume Multiplier (Rev)", minval=0.5, maxval=1.5, group=g)
        self.filter_long = i.bool(True, "Enable Long Filter?", group=g)
        self.filter_short = i.bool(True, "Enable Short Filter?", group=g)
        self.active_hours = i.bool(True, "Active Hours Filter?", group=g)
        g = "Institutional [DYNAMIC]"
        self.use_institutional = i.bool(True, "Use Institutional Logic (Overrides All)", group=g)
        self.inst_swing_lookback = i.int(20, "Swing Lookback (Zone Anchor)", minval=10, maxval=100, group=g)
        self.inst_zone_atr_width = i.float(0.5, "Zone Width (x ATR)", minval=0.1, maxval=2.0, group=g)
        self.inst_mid_atr_buffer = i.float(0.25, "Mid Zone Buffer (x ATR)", minval=0.1, maxval=1.0, group=g)
        self.inst_base_size = i.float(10.0, "Institutional Base Position %", minval=1.0, maxval=50.0, group=g)
        self.inst_size_scaling = i.bool(True, "Scale Size Within Zone?", group=g)
        self.use_vwap_mid = i.bool(True, "Use VWAP as Mid Price?", group=g)
        g = "Davin MA Strategy"
        self.use_davin = i.bool(True, "Use Davin's MA Strategy", group=g)
        self.davin_ma_long = i.int(200, "Davin Long MA", minval=100, maxval=300, group=g)
        self.davin_ma_short = i.int(10, "Davin Short MA", minval=5, maxval=50, group=g)
        self.davin_buy_dip = i.bool(True, "Davin Buy the Dip", group=g)
        self.davin_dip_trigger = i.int(14, "Davin Dip Trigger %", minval=5, maxval=30, group=g)
        self.davin_lower_close = i.bool(True, "Davin Exit on Lower Close", group=g)
        self.davin_buy_price = 0.0
        self.last_pivot_high = NA
        self.last_pivot_low = NA
        self.last_bull_bos = NA
        self.last_bear_bos = NA
        self.ema100_test_count = 0
        self.last_test_price = NA
        self.test_bar_index = NA
        self.trend_bars = 0
        self.current_trend_bullish = False
        self.trend_start_price = 0.0

    def on_bar(self):
        st = self.strategy
        close, high, low, open_, volume = self.close, self.high, self.low, self.open, self.volume
        tid = self.syminfo.tickerid
        base = self.syminfo.basecurrency
        is_gold = ("GC" in tid) or ("MGC" in tid) or ("GOLD" in tid) or tid == "XAUUSD" or (base == "XAU" and self.syminfo.currency == "USD")
        is_btc = ("BTC" in tid) or base == "BTC" or ("BITCOIN" in tid)
        is_eth = ("ETH" in tid) or base == "ETH" or ("ETHEREUM" in tid)
        if is_gold:
            inst_type = "GOLD"
        elif is_btc:
            inst_type = "BITCOIN"
        elif is_eth:
            inst_type = "ETHEREUM"
        else:
            inst_type = "OTHER"
        ad_pivot = 5 if inst_type == "GOLD" else 10 if inst_type == "BITCOIN" else 8 if inst_type == "ETHEREUM" else self.pivot_lookback
        ad_sweep = 0.3 if inst_type == "GOLD" else 0.5 if inst_type == "BITCOIN" else 0.4 if inst_type == "ETHEREUM" else self.min_sweep_size_atr
        ad_retest = 0.001 if inst_type == "GOLD" else 0.005 if inst_type == "BITCOIN" else 0.006 if inst_type == "ETHEREUM" else self.retest_tolerance
        ad_atr_test = 0.2 if inst_type == "GOLD" else 0.5 if inst_type == "BITCOIN" else 0.6 if inst_type == "ETHEREUM" else self.atr_test_percent

        # history of derived series: read the previous values before setting the current ones
        h_tema, h_lsma, h_ema100, h_kama, h_rsi = self.H("tema"), self.H("lsma"), self.H("ema100"), self.H("kama"), self.H("rsi")
        h_dbc = self.H("dbc")
        tema_1, tema_5 = h_tema[1], h_tema[5]
        lsma_1, lsma_10 = h_lsma[1], h_lsma[10]
        ema100_1, ema100_20 = h_ema100[1], h_ema100[20]
        kama_1 = h_kama[1]
        rsi_10 = h_rsi[10]
        dbc_1 = h_dbc[1]

        lsma = ta.linreg(close, self.lsma_length, 0)
        x1 = ta.ema(close, self.tema_length)
        x2 = ta.ema(x1, self.tema_length)
        x3 = ta.ema(x2, self.tema_length)
        tema = 3 * x1 - 3 * x2 + x3
        ema100 = ta.ema(close, self.ema100_length)
        atr = ta.atr(14)
        rsi = ta.rsi(close, 14)
        vol_ma = ta.sma(volume, self.vol_length)
        vwap_value = ta.vwap(close)

        davin_ma1 = ta.sma(close, self.davin_ma_long)
        davin_ma2 = ta.sma(close, self.davin_ma_short)
        davin_highest52 = ta.highest(high, 52)
        davin_overall_change = div(davin_highest52 - close, davin_highest52) * 100
        pos = st.position_size
        davin_buy_cond = ((close > davin_ma1 and close < davin_ma2 and pos == 0) or (pos == 0 and self.davin_buy_dip and davin_overall_change > self.davin_dip_trigger)) if self.use_davin else False
        davin_sell_cond = (close > davin_ma2 and pos > 0 and ((not self.davin_lower_close) or close < self.low[1])) if self.use_davin else False
        davin_stop_distance = div(self.davin_buy_price - close, close) if pos > 0 else NA
        davin_stop_cond = pos > 0 and davin_stop_distance > 0.15

        dyn_swing_high = ta.highest(high, self.inst_swing_lookback)
        dyn_swing_low = ta.lowest(low, self.inst_swing_lookback)
        dyn_buy_low = dyn_swing_low
        dyn_buy_high = dyn_swing_low + atr * self.inst_zone_atr_width
        dyn_sell_high = dyn_swing_high
        dyn_sell_low = dyn_swing_high - atr * self.inst_zone_atr_width
        dyn_mid_price = vwap_value if self.use_vwap_mid else (dyn_swing_high + dyn_swing_low) / 2
        dyn_mid_low = dyn_mid_price - atr * self.inst_mid_atr_buffer
        dyn_mid_high = dyn_mid_price + atr * self.inst_mid_atr_buffer
        dyn_range_width = atr * self.inst_zone_atr_width

        rsi_rev = ta.rsi(close, self.rsi_length)
        stoch_k = ta.sma(ta.stoch(close, high, low, 9), 6)
        stoch_d = ta.sma(stoch_k, 3)
        rsi1 = ta.rsi(close, 14)
        rsi1_lo = ta.lowest(rsi1, 14)
        rsi1_hi = ta.highest(rsi1, 14)
        stoch_rsi = div(rsi1 - rsi1_lo, rsi1_hi - rsi1_lo) * 100
        macd_line, signal_line, hist_line = ta.macd(close, 12, 26, 9)
        dmi_plus = ta.rma(pmath.max(ta.change(high), 0), self.adx_length)
        dmi_minus = ta.rma(-pmath.min(ta.change(low), 0), self.adx_length)
        trur = ta.rma(ta.tr(False), self.adx_length)
        plus_di = 100 * div(dmi_plus, trur)
        minus_di = 100 * div(dmi_minus, trur)
        dx = 100 * div(abs(plus_di - minus_di), plus_di + minus_di)
        adx = ta.rma(dx, self.adx_length)
        wl = self.williams_length
        williams = -100 * div(ta.highest(high, wl) - close, ta.highest(high, wl) - ta.lowest(low, wl))
        cci = div(close - ta.sma(close, 14), 0.015 * ta.dev(close, 14))
        kama_rev = ta.ema(close, self.kama_length_rev)
        kama_rising = kama_rev > kama_1
        kama_falling = kama_rev < kama_1
        vol_ma_rev = ta.sma(volume, self.vol_length)

        bearish_score = int(rsi_rev < 50) + int(stoch_k < 50 or stoch_k < stoch_d) + int(stoch_rsi < 50) + int(macd_line < signal_line) + int(williams < -50) + int(cci < 0)
        strong_bearish = bearish_score >= 3
        bullish_score = int(rsi_rev > 50) + int(stoch_k > 50 or stoch_k > stoch_d) + int(stoch_rsi > 50) + int(macd_line > signal_line) + int(williams > -50) + int(cci > 0)
        strong_bullish = bullish_score >= 3

        long_trend_rev = close > kama_rev and kama_rising and (adx > self.adx_strong_trend or plus_di > minus_di)
        short_trend_rev = close < kama_rev and kama_falling and (adx > self.adx_strong_trend or minus_di > plus_di)
        volume_ok_rev = volume > vol_ma_rev * self.min_vol_mult_rev

        pivot_high = ta.pivothigh(high, ad_pivot, ad_pivot)
        pivot_low = ta.pivotlow(low, ad_pivot, ad_pivot)
        if not na(pivot_high):
            self.last_pivot_high = pivot_high
        if not na(pivot_low):
            self.last_pivot_low = pivot_low
        lph, lpl = float(self.last_pivot_high), float(self.last_pivot_low)

        min_sweep = atr * ad_sweep
        high_1, low_1 = self.high[1], self.low[1]
        sweep_down = low < lpl and close > high_1 and (high_1 - low) > min_sweep
        sweep_up = high > lph and close < low_1 and (high - low_1) > min_sweep

        xup_ema = ta.crossover(close, ema100)
        xdn_ema = ta.crossunder(close, ema100)
        bull_bos = xup_ema and close > ema100
        bear_bos = xdn_ema and close < ema100
        if bull_bos:
            self.last_bull_bos = float(ema100)
        if bear_bos:
            self.last_bear_bos = float(ema100)
        lbb, lsb = float(self.last_bull_bos), float(self.last_bear_bos)
        bull_retest = (not na(lbb)) and close < lbb * (1 + ad_retest) and close > lbb * (1 - ad_retest) and close > open_
        bear_retest = (not na(lsb)) and close > lsb * (1 - ad_retest) and close < lsb * (1 + ad_retest) and close < open_

        if abs(close - ema100) < atr * ad_atr_test:
            if na(self.last_test_price) or (self.bar_index != self.test_bar_index and self.last_test_price != close):
                self.ema100_test_count += 1
                self.last_test_price = float(close)
                self.test_bar_index = self.bar_index
        if abs(close - ema100) > atr * 0.5:
            self.ema100_test_count = 0

        lower_high = high < lph and high > high_1
        higher_low = low > lpl and low < low_1

        p_tema = div(close - tema, tema) * 100
        p_lsma = div(close - lsma, lsma) * 100
        p_ema100 = div(close - ema100, ema100) * 100
        zone_score = (p_tema + p_lsma + p_ema100) / 3
        zt1 = 2.0 if inst_type == "GOLD" else 5.0 if inst_type == "BITCOIN" else 6.0 if inst_type == "ETHEREUM" else 2.0
        zt2 = 1.0 if inst_type == "GOLD" else 2.5 if inst_type == "BITCOIN" else 3.0 if inst_type == "ETHEREUM" else 1.0
        if zone_score <= -zt1:
            zone = "EXTREME_OVERSOLD"
        elif zone_score <= -zt2:
            zone = "OVERSOLD"
        elif zone_score <= 0.5:
            zone = "NEUTRAL_LOW"
        elif zone_score <= 1.5:
            zone = "NEUTRAL_HIGH"
        elif zone_score <= zt2:
            zone = "OVERBOUGHT"
        else:
            zone = "EXTREME_OVERBOUGHT"

        is_tema_bull = tema > tema_1
        is_lsma_bull = lsma > lsma_1
        is_ema100_bull = ema100 > ema100_1
        all_bullish = is_tema_bull and is_lsma_bull and is_ema100_bull
        all_bearish = (not is_tema_bull) and (not is_lsma_bull) and (not is_ema100_bull)
        if self.require_trend_alignment:
            long_allowed = all_bullish
            short_allowed = all_bearish
        else:
            long_allowed = tema > lsma and close > ema100
            short_allowed = tema < lsma and close < ema100

        tema_slope = tema - tema_5
        lsma_slope = lsma - lsma_10
        ema100_slope = ema100 - ema100_20
        trend_strength = (tema_slope + lsma_slope + ema100_slope) / 3
        normalized_strength = div(abs(trend_strength), atr)

        if self.bar_index == 0:
            self.trend_bars = 0
            self.current_trend_bullish = False
            self.trend_start_price = 0.0
        else:
            if all_bullish and ((not self.current_trend_bullish) or self.trend_start_price == 0.0):
                self.trend_bars = 1
                self.current_trend_bullish = True
                self.trend_start_price = float(close)
            elif all_bearish and (self.current_trend_bullish or self.trend_start_price == 0.0):
                self.trend_bars = 1
                self.current_trend_bullish = False
                self.trend_start_price = float(close)
            elif (self.current_trend_bullish and all_bullish) or ((not self.current_trend_bullish) and all_bearish):
                self.trend_bars += 1
            else:
                self.trend_bars = 0
                self.current_trend_bullish = False
                self.trend_start_price = 0.0

        trend_exhausted = False
        if self.trend_bars > 0 and self.trend_start_price > 0.0:
            c1 = self.trend_bars > self.min_trend_bars * 2
            c2 = normalized_strength < self.trend_strength_threshold
            c3 = (self.current_trend_bullish and not all_bullish) or ((not self.current_trend_bullish) and not all_bearish)
            rsi_div = False
            if self.momentum_divergence:
                if self.current_trend_bullish:
                    rsi_div = close > self.close[10] and rsi < rsi_10
                else:
                    rsi_div = close < self.close[10] and rsi > rsi_10
            trend_exhausted = c1 and (c2 or c3 or rsi_div)

        volume_ok = volume > vol_ma * self.min_vol_mult
        tema_x_up = ta.crossover(tema, lsma)
        tema_x_dn = ta.crossunder(tema, lsma)

        rev_long = (long_trend_rev and strong_bullish and volume_ok_rev and self.active_hours) if self.enable_reversals else False
        rev_short = (short_trend_rev and strong_bearish and volume_ok_rev and self.active_hours) if self.enable_reversals else False

        ideal_action = "WAIT"
        if self.use_ideal:
            if sweep_down and close > ema100 and volume_ok:
                ideal_action = "BUY"
            elif bull_retest and tema > lsma and volume_ok:
                ideal_action = "BUY"
            elif zone in ("EXTREME_OVERSOLD", "OVERSOLD") and close > ema100 and tema > lsma and volume_ok:
                ideal_action = "BUY"
            if bear_retest and tema < lsma and volume_ok:
                ideal_action = "SELL"
            elif lower_high and zone in ("OVERBOUGHT", "EXTREME_OVERBOUGHT") and tema < lsma:
                ideal_action = "SELL"
            elif self.ema100_test_count >= self.max_test_count and close < ema100 and tema < lsma and xdn_ema:
                ideal_action = "SELL"

        inst_action = "WAIT"
        inst_size = self.inst_base_size
        if close >= dyn_buy_low and close <= dyn_buy_high:
            inst_action = "ACCUMULATE"
            inst_size = self.inst_base_size * (1 + div(dyn_buy_high - close, dyn_range_width)) if self.inst_size_scaling and dyn_range_width > 0 else self.inst_base_size
        elif close >= dyn_sell_low and close <= dyn_sell_high:
            inst_action = "DISTRIBUTE"
            inst_size = self.inst_base_size * (1 + div(close - dyn_sell_low, dyn_range_width)) if self.inst_size_scaling and dyn_range_width > 0 else self.inst_base_size
        elif close >= dyn_mid_low and close <= dyn_mid_high:
            inst_action = "PROVIDE_LIQUIDITY"

        inst_long = False
        inst_short = False
        if self.use_institutional:
            if inst_action == "ACCUMULATE":
                inst_long = True
            elif inst_action == "DISTRIBUTE":
                inst_short = True

        davin_long = False
        davin_short = False
        if self.use_davin:
            if davin_buy_cond:
                davin_long = True
            if davin_sell_cond or davin_stop_cond:
                davin_short = True

        long_cond = False
        short_cond = False
        source = ""
        if self.use_institutional and inst_long:
            long_cond = True
            source = "INSTITUTIONAL"
        elif self.use_institutional and inst_short:
            short_cond = True
            source = "INSTITUTIONAL"
        elif self.use_ideal and ideal_action == "BUY" and pos == 0:
            long_cond = True
            source = "IDEAL"
        elif self.use_ideal and ideal_action == "SELL" and pos == 0:
            short_cond = True
            source = "IDEAL"
        elif self.enable_reversals and rev_long and pos == 0:
            long_cond = True
            source = "REVERSAL"
        elif self.enable_reversals and rev_short and pos == 0:
            short_cond = True
            source = "REVERSAL"
        elif self.use_davin and davin_long and pos == 0:
            long_cond = True
            source = "DAVIN MA"
        elif self.use_davin and davin_short and pos > 0:
            short_cond = True
            source = "DAVIN MA"
        else:
            if self.use_trend_exhaustion:
                long_cond = (long_allowed and tema_x_up and volume_ok) or (trend_exhausted and not self.current_trend_bullish and tema_x_up and volume_ok)
                short_cond = (short_allowed and tema_x_dn and volume_ok) or (trend_exhausted and self.current_trend_bullish and tema_x_dn and volume_ok)
            else:
                long_cond = long_allowed and tema_x_up and volume_ok
                short_cond = short_allowed and tema_x_dn and volume_ok
            source = "ORIGINAL" if (long_cond or short_cond) else ""

        if self.use_davin and dbc_1 == 1:
            self.davin_buy_price = float(open_)

        trail_offset = atr * self.trail_atr_mult
        long_sl = long_tp = short_sl = short_tp = NA
        avg = st.position_avg_price
        if pos > 0:
            if source == "INSTITUTIONAL":
                long_sl = avg - (self.sl_atr_mult * 1.5 * atr)
                long_tp = avg + (self.tp_atr_mult * 1.2 * atr)
            else:
                long_sl = avg - self.sl_atr_mult * atr
                long_tp = avg + self.tp_atr_mult * atr
        if pos < 0:
            if source == "INSTITUTIONAL":
                short_sl = avg + (self.sl_atr_mult * 1.5 * atr)
                short_tp = avg - (self.tp_atr_mult * 1.2 * atr)
            else:
                short_sl = avg + self.sl_atr_mult * atr
                short_tp = avg - self.tp_atr_mult * atr

        position_size = 10.0
        if source == "INSTITUTIONAL":
            position_size = inst_size
        elif source == "IDEAL":
            position_size = 15.0
        elif source == "REVERSAL":
            position_size = 12.5
        elif source == "DAVIN MA":
            position_size = 10.0

        if long_cond and pos == 0:
            st.entry("Long", st.long, qty=div(st.equity, close) * position_size / 100)
        if short_cond and pos == 0:
            st.entry("Short", st.short, qty=div(st.equity, close) * position_size / 100)
        if pos > 0:
            st.exit("Long Exit", "Long", stop=long_sl, limit=long_tp, trail_points=trail_offset, trail_offset=trail_offset)
        if pos < 0:
            st.exit("Short Exit", "Short", stop=short_sl, limit=short_tp, trail_points=trail_offset, trail_offset=trail_offset)
        if pos != 0 and self.bar_index - st.opentrades_entry_bar_index(0) >= self.max_bars_in_trade:
            st.close_all()

        h_tema.set(tema)
        h_lsma.set(lsma)
        h_ema100.set(ema100)
        h_kama.set(kama_rev)
        h_rsi.set(rsi)
        h_dbc.set(1 if davin_buy_cond else 0)
