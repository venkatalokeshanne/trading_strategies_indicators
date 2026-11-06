"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AI MES London Open Breakout
Author       : lylerh
Source URL   : https://www.tradingview.com/script/xdRxul1F-AI-MES-London-Open-Breakout
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The high / low of the pre-London window (02:30-03:00 New York) is locked at the London open (03:00-06:00 ET). Inside London, while flat and under the per-session trade limit, a close through the locked range (when it is at least the minimum size) or through the last confirmed pivot, with RSI and volume filters and the higher-timeframe EMA bias (request.security, lookahead off), opens a trade at the next open. The stop is the wider of the pivot-plus-buffer and an ATR floor, the target R:R times the risk from the signal close. Everything closes when the sessions end.
Deviations from the original: none.
Not carried over: the alert messages and the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AiMesLondonOpen(Script):
    TITLE = "AI MES London Open Breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.62)
    SOURCE = {"id": "xdRxul1F", "author": "lylerh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xdRxul1F-AI-MES-London-Open-Breakout"}

    def init(self):
        i = self.input
        g = "Sessions"
        self.pre_start = i.int(2, "Pre-London Range Start Hour (ET)", group=g, minval=0, maxval=23)
        self.pre_min = i.int(30, "Pre-London Range Start Minute (ET)", group=g, minval=0, maxval=59)
        self.lond_start = i.int(3, "London Open Hour (ET)", group=g, minval=0, maxval=23)
        self.lond_start_min = i.int(0, "London Open Minute (ET)", group=g, minval=0, maxval=59)
        self.lond_end = i.int(6, "London Close Hour (ET)", group=g, minval=0, maxval=23)
        self.lond_end_min = i.int(0, "London Close Minute (ET)", group=g, minval=0, maxval=59)
        self.pivot_len = i.int(4, "Pivot Lookback (bars each side)", group="Structure", minval=2, maxval=10)
        self.htf_tf = i.timeframe("60", "HTF Timeframe", group="Higher Timeframe")
        self.htf_len = i.int(21, "HTF EMA Length", group="Higher Timeframe")
        g = "Momentum"
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.rsi_long_min = i.float(45, "RSI Min for Longs", group=g, step=1.0)
        self.rsi_short_max = i.float(55, "RSI Max for Shorts", group=g, step=1.0)
        g = "Volume"
        self.vol_len = i.int(20, "Volume MA Length", group=g)
        self.vol_mult = i.float(1.2, "Volume Multiplier", group=g, step=0.1)
        g = "Risk"
        self.risk_ratio = i.float(1.5, "Reward:Risk Ratio", group=g, step=0.1)
        self.stop_buffer = i.float(2.0, "Stop Buffer beyond pivot (pts)", group=g, step=0.25)
        self.atr_len = i.int(14, "ATR Length (for stop floor)", group=g)
        self.atr_mult = i.float(1.5, "ATR Stop Floor Multiplier", group=g, step=0.1)
        self.max_trades = i.int(2, "Max Trades Per Session", group=g, minval=1, maxval=5)
        g = "Filters"
        self.min_range = i.float(3.0, "Min Pre-London Range Size (pts)", group=g, step=0.5)
        self.use_htf = i.bool(True, "Use HTF Bias Filter", group=g)
        self.use_vol = i.bool(True, "Use Volume Filter", group=g)
        self.session_trades = 0
        self.pre_high = NA
        self.pre_low = NA
        self.pre_high_locked = NA
        self.pre_low_locked = NA
        self.last_piv_high = NA
        self.last_piv_low = NA
        self.entry_stop = NA
        self.entry_target = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        et = self.hour(self.time, "America/New_York") * 100 + self.minute(self.time, "America/New_York")
        pre_t = self.pre_start * 100 + self.pre_min
        lond_t = self.lond_start * 100 + self.lond_start_min
        lond_end_t = self.lond_end * 100 + self.lond_end_min
        in_pre = et >= pre_t and et < lond_t
        in_lond = et >= lond_t and et < lond_end_t
        in_any = in_pre or in_lond
        il_h, ia_h = self.H("in_lond"), self.H("in_any")
        in_lond_1, in_any_1 = il_h[1], ia_h[1]
        il_h.set(in_lond)
        ia_h.set(in_any)
        new_session = in_lond and not ((not na(in_lond_1)) and bool(in_lond_1))
        if new_session:
            self.session_trades = 0
        under_limit = self.session_trades < self.max_trades
        if in_pre:
            self.pre_high = float(high) if na(self.pre_high) else float(pmath.max(self.pre_high, high))
            self.pre_low = float(low) if na(self.pre_low) else float(pmath.min(self.pre_low, low))
        if new_session:
            self.pre_high_locked = self.pre_high
            self.pre_low_locked = self.pre_low
            self.pre_high = NA
            self.pre_low = NA
        range_size = NA if (na(self.pre_high_locked) or na(self.pre_low_locked)) else self.pre_high_locked - self.pre_low_locked
        valid_range = (not na(range_size)) and range_size >= self.min_range
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_len), lookahead=False)
        bull_bias = close > htf_ema
        bear_bias = close < htf_ema
        piv_high = ta.pivothigh(high, self.pivot_len, self.pivot_len)
        piv_low = ta.pivotlow(low, self.pivot_len, self.pivot_len)
        if not na(piv_high):
            self.last_piv_high = float(piv_high)
        if not na(piv_low):
            self.last_piv_low = float(piv_low)
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        break_high = (not na(self.last_piv_high)) and close > self.last_piv_high and close_1 <= self.last_piv_high
        break_low = (not na(self.last_piv_low)) and close < self.last_piv_low and close_1 >= self.last_piv_low
        rsi = ta.rsi(close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        avg_vol = ta.sma(self.volume, self.vol_len)
        high_vol = (not self.use_vol) or self.volume > avg_vol * self.vol_mult
        rsi_long = rsi >= self.rsi_long_min
        rsi_short = rsi <= self.rsi_short_max
        range_break_long = valid_range and close > self.pre_high_locked and close_1 <= self.pre_high_locked
        range_break_short = valid_range and close < self.pre_low_locked and close_1 >= self.pre_low_locked
        htf_long = (not self.use_htf) or bull_bias
        htf_short = (not self.use_htf) or bear_bias
        long_cond = bool(in_lond and under_limit and st.position_size == 0 and (range_break_long or break_high) and rsi_long and high_vol and htf_long)
        short_cond = bool(in_lond and under_limit and st.position_size == 0 and (range_break_short or break_low) and rsi_short and high_vol and htf_short)
        pivot_long_stop = self.last_piv_low - self.stop_buffer
        pivot_short_stop = self.last_piv_high + self.stop_buffer
        atr_long_stop = close - atr * self.atr_mult
        atr_short_stop = close + atr * self.atr_mult
        long_stop = pmath.min(pivot_long_stop, atr_long_stop)
        short_stop = pmath.max(pivot_short_stop, atr_short_stop)
        long_risk = close - long_stop
        short_risk = short_stop - close
        long_target = close + long_risk * self.risk_ratio
        short_target = close - short_risk * self.risk_ratio
        if st.position_size == 0:
            self.entry_stop = NA
            self.entry_target = NA
        if long_cond:
            self.entry_stop = float(long_stop)
            self.entry_target = float(long_target)
            st.entry("Long", st.long)
            self.session_trades += 1
        if short_cond:
            self.entry_stop = float(short_stop)
            self.entry_target = float(short_target)
            st.entry("Short", st.short)
            self.session_trades += 1
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=self.entry_stop, limit=self.entry_target)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=self.entry_stop, limit=self.entry_target)
        session_end = (not in_any) and (not na(in_any_1)) and bool(in_any_1)
        if session_end:
            st.close_all(comment="Session End")
