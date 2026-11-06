"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EB ICT One Trade Setup For Life - 70% Filter Model v2
Author       : robmagnaye14
Source URL   : https://www.tradingview.com/script/5IMl4euK-EB-ICT-One-Trade-Setup-For-Life-70-Filter-Model-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A liquidity sweep of the latest swing high / low inside a kill zone starts a setup; a displacement candle, fair value gap, market-structure shift (close beyond the 10-bar extreme) and break
of structure (20-bar extreme) must follow within 40 bars, then a retest of the gap with a rejection candle (and the EMA200 slope) enters once per sweep at the next open. The stop is beyond the sweep level plus an ATR
buffer and the target is risk x reward, fixed on the signal bar.

Known caveat: the four ta.highest / ta.lowest calls (MSS and BOS) sit inside `and` chains, so in Pine v6 they only run - and their windows and [1] history only advance - on the bars where the preceding conditions held (LESSONS P5);
pinelib keeps exactly that, so the 10 / 20-bar windows hold only the values fed on those bars. If TradingView computes them from the whole bar history the structure-shift timing would differ.

Deviations from the original: none.
Not carried over: zone boxes, labels and the EMA plot (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class EbIctOneTrade(Script):
    TITLE = "EB ICT One Trade Setup For Life - 70% Filter Model v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="percent_of_equity", default_qty_value=0.5, commission_type="percent", commission_value=0.01)
    SOURCE = {"id": "5IMl4euK", "author": "robmagnaye14", "licence": "not stated", "url": "https://www.tradingview.com/script/5IMl4euK-EB-ICT-One-Trade-Setup-For-Life-70-Filter-Model-v2"}

    def init(self):
        self.risk_rr = self.input.float(1.5, "Risk Reward", step=0.25)
        self.min_score = self.input.float(85.0, "Minimum Entry Score", step=5)
        self.ema_len = self.input.int(200, "EMA Trend Length")
        self.swing_len = self.input.int(5, "Swing Length")
        self.atr_len = self.input.int(14, "ATR Length")
        self.sl_atr_buffer = self.input.float(0.4, "SL ATR Buffer", step=0.1)
        self.use_kill_zone = self.input.bool(True, "Use Kill Zones")
        self.use_trend_filter = self.input.bool(True, "Use EMA 200 Filter")
        self.use_rejection = self.input.bool(True, "Require Rejection Candle")
        self.max_bars_setup = self.input.int(40, "Max Bars After Sweep")
        self.show_zones = self.input.bool(True, "Show Zones")
        self.london_session = self.input.session("0700-1200", "London KZ")
        self.ny_session = self.input.session("1300-2000", "NY KZ")
        self.last_high = NA
        self.last_low = NA
        self.dir = 0
        self.sweep_found = False
        self.displacement_found = False
        self.fvg_found = False
        self.mss_found = False
        self.bos_found = False
        self.traded = False
        self.sweep_level = NA
        self.sweep_bar = NA
        self.fvg_top = NA
        self.fvg_bot = NA
        self.fvg_bar = NA

    def on_bar(self):
        in_london = not na(self.time_fn(None, self.london_session))
        in_ny = not na(self.time_fn(None, self.ny_session))
        in_kz = in_london or in_ny
        session_ok = in_kz if self.use_kill_zone else True
        ema200 = S(ta.ema(self.close, self.ema_len))
        atr = ta.atr(self.atr_len)
        bull_trend = self.close > ema200[0] and ema200[0] > ema200[5]
        bear_trend = self.close < ema200[0] and ema200[0] < ema200[5]
        ph = ta.pivothigh(self.high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(self.low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_high = ph
        if not na(pl):
            self.last_low = pl
        buy_sweep = session_ok and (not na(self.last_low)) and self.low < self.last_low and self.close > self.last_low
        sell_sweep = session_ok and (not na(self.last_high)) and self.high > self.last_high and self.close < self.last_high
        if buy_sweep:
            self.dir = 1
            self.sweep_found = True
            self.displacement_found = False
            self.fvg_found = False
            self.mss_found = False
            self.bos_found = False
            self.traded = False
            self.sweep_level = float(self.low)
            self.sweep_bar = self.bar_index
        if sell_sweep:
            self.dir = -1
            self.sweep_found = True
            self.displacement_found = False
            self.fvg_found = False
            self.mss_found = False
            self.bos_found = False
            self.traded = False
            self.sweep_level = float(self.high)
            self.sweep_bar = self.bar_index
        setup_alive = self.sweep_found and self.bar_index - self.sweep_bar <= self.max_bars_setup
        body = pmath.abs(self.close - self.open)
        avg_body = ta.sma(pmath.abs(self.close - self.open), 20)
        range_big = self.high - self.low > atr * 0.8
        bull_disp = setup_alive and self.dir == 1 and self.close > self.open and body > avg_body * 1.8 and range_big
        bear_disp = setup_alive and self.dir == -1 and self.close < self.open and body > avg_body * 1.8 and range_big
        if bull_disp or bear_disp:
            self.displacement_found = True
        high, low = S(self.high), S(self.low)
        bull_fvg = self.displacement_found and self.dir == 1 and self.low > high[2]
        bear_fvg = self.displacement_found and self.dir == -1 and self.high < low[2]
        if bull_fvg:
            self.fvg_top = float(self.low)
            self.fvg_bot = high[2]
            self.fvg_bar = self.bar_index
            self.fvg_found = True
        if bear_fvg:
            self.fvg_top = low[2]
            self.fvg_bot = float(self.high)
            self.fvg_bar = self.bar_index
            self.fvg_found = True
        fvg_active = self.fvg_found and self.bar_index - self.fvg_bar <= 25
        bull_mss = False
        if setup_alive and self.dir == 1:
            bull_mss = self.close > S(ta.highest(self.high, 10))[1]
        bear_mss = False
        if setup_alive and self.dir == -1:
            bear_mss = self.close < S(ta.lowest(self.low, 10))[1]
        if bull_mss or bear_mss:
            self.mss_found = True
        bull_bos = False
        if setup_alive and self.dir == 1 and self.mss_found:
            bull_bos = self.close > S(ta.highest(self.high, 20))[1]
        bear_bos = False
        if setup_alive and self.dir == -1 and self.mss_found:
            bear_bos = self.close < S(ta.lowest(self.low, 20))[1]
        if bull_bos or bear_bos:
            self.bos_found = True
        bull_retest = fvg_active and self.dir == 1 and self.low <= self.fvg_top and self.close > self.fvg_bot
        bear_retest = fvg_active and self.dir == -1 and self.high >= self.fvg_bot and self.close < self.fvg_top
        bull_reject = self.close > self.open and self.close > high[1]
        bear_reject = self.close < self.open and self.close < low[1]
        reject_ok_buy = bull_reject if self.use_rejection else True
        reject_ok_sell = bear_reject if self.use_rejection else True
        score = 0.0
        score += 25 if self.sweep_found else 0
        score += 20 if self.displacement_found else 0
        score += 10 if self.fvg_found else 0
        score += 20 if self.mss_found else 0
        score += 15 if self.bos_found else 0
        score += 10 if (bull_retest or bear_retest) else 0
        trend_ok_buy = bull_trend if self.use_trend_filter else True
        trend_ok_sell = bear_trend if self.use_trend_filter else True
        buy_signal = score >= self.min_score and self.dir == 1 and bull_retest and self.mss_found and self.bos_found and trend_ok_buy and reject_ok_buy
        sell_signal = score >= self.min_score and self.dir == -1 and bear_retest and self.mss_found and self.bos_found and trend_ok_sell and reject_ok_sell
        buy_sl = pmath.min(self.sweep_level, self.low) - atr * self.sl_atr_buffer
        sell_sl = pmath.max(self.sweep_level, self.high) + atr * self.sl_atr_buffer
        buy_risk = self.close - buy_sl
        sell_risk = sell_sl - self.close
        buy_tp = self.close + buy_risk * self.risk_rr
        sell_tp = self.close - sell_risk * self.risk_rr
        mintick = self.syminfo.mintick
        st = self.strategy
        if buy_signal and not self.traded and buy_risk > mintick:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", "BUY", stop=buy_sl, limit=buy_tp)
            self.traded = True
        if sell_signal and not self.traded and sell_risk > mintick:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", "SELL", stop=sell_sl, limit=sell_tp)
            self.traded = True
        self.plot(ema200[0], "EMA 200", color=color.gray)
