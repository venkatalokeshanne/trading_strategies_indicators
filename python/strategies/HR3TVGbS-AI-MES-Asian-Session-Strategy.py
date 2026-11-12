"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AI MES Asian Session Strategy
Author       : lylerh
Source URL   : https://www.tradingview.com/script/HR3TVGbS-AI-MES-Asian-Session-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The high / low of the first half hour of the Asian session (18:00-18:30 New York) is locked when the trading part (18:30-23:59) starts. Inside it, while flat and under the per-session limit, a range breakout (close beyond the range by a buffer, RSI and volume confirmation, higher-timeframe EMA bias via request.security with lookahead off) or a mean-revert fade (a tag of the range edge that closes back inside with an RSI extreme) opens a trade at the next open. Stops sit beyond the range (or the ATR floor, whichever is wider); breakouts aim at R:R times the risk, fades at the range midpoint. Everything closes when the session ends.
Deviations from the original: none.
Not carried over: alert messages and the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AiMesAsianSession(Script):
    TITLE = "AI MES Asian Session Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.62)
    SOURCE = {"id": "HR3TVGbS", "author": "lylerh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/HR3TVGbS-AI-MES-Asian-Session-Strategy"}

    def init(self):
        i = self.input
        g = "Session"
        self.rs_h = i.int(18, "Range Build Start Hour (ET)", group=g, minval=0, maxval=23)
        self.rs_m = i.int(0, "Range Build Start Minute (ET)", group=g, minval=0, maxval=59)
        self.re_h = i.int(18, "Range Build End Hour (ET)", group=g, minval=0, maxval=23)
        self.re_m = i.int(30, "Range Build End Minute (ET)", group=g, minval=0, maxval=59)
        self.ae_h = i.int(23, "Session End Hour (ET)", group=g, minval=0, maxval=23)
        self.ae_m = i.int(59, "Session End Minute (ET)", group=g, minval=0, maxval=59)
        g = "Range"
        self.min_range = i.float(3.0, "Min Range Size (pts)", group=g, step=0.5)
        self.max_range = i.float(20.0, "Max Range Size (pts)", group=g, step=0.5)
        self.break_buf = i.float(0.5, "Breakout Confirmation (pts)", group=g, step=0.25)
        self.mid_buf = i.float(1.0, "Mean Revert Entry Buffer (pts)", group=g, step=0.25)
        g = "Higher Timeframe"
        self.htf_tf = i.timeframe("60", "HTF Timeframe", group=g)
        self.htf_len = i.int(21, "HTF EMA Length", group=g)
        self.use_htf = i.bool(True, "Use HTF Bias Filter", group=g)
        g = "Momentum"
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.rsi_ob = i.float(62, "RSI Overbought (fade shorts)", group=g, step=1.0)
        self.rsi_os = i.float(38, "RSI Oversold (fade longs)", group=g, step=1.0)
        self.rsi_break_min = i.float(50, "RSI Min for breakout longs", group=g, step=1.0)
        self.rsi_break_max = i.float(50, "RSI Max for breakout shorts", group=g, step=1.0)
        g = "Volume"
        self.vol_len = i.int(20, "Volume MA Length", group=g)
        self.vol_break = i.float(1.2, "Volume Multiplier (breakout)", group=g, step=0.1)
        self.vol_fade = i.float(0.8, "Volume Multiplier (fade)", group=g, step=0.1)
        self.use_vol = i.bool(True, "Use Volume Filter", group=g)
        g = "Risk"
        self.rr = i.float(1.5, "Reward:Risk Ratio", group=g, step=0.1)
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_mult = i.float(1.5, "ATR Stop Multiplier", group=g, step=0.1)
        self.stop_buf = i.float(1.5, "Stop Buffer beyond range (pts)", group=g, step=0.25)
        self.max_trades = i.int(2, "Max Trades Per Session", group=g, minval=1, maxval=5)
        self.session_trades = 0
        self.range_high = NA
        self.range_low = NA
        self.high_locked = NA
        self.low_locked = NA
        self.range_mid = NA
        self.entry_stop = NA
        self.entry_target = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        et = self.hour(self.time, "America/New_York") * 100 + self.minute(self.time, "America/New_York")
        rs_t = self.rs_h * 100 + self.rs_m
        re_t = self.re_h * 100 + self.re_m
        ae_t = self.ae_h * 100 + self.ae_m
        in_build = et >= rs_t and et < re_t
        in_asian = et >= re_t and et <= ae_t
        in_any = in_build or in_asian
        ia_h, an_h = self.H("in_asian"), self.H("in_any")
        in_asian_1, in_any_1 = ia_h[1], an_h[1]
        ia_h.set(in_asian)
        an_h.set(in_any)
        new_session = in_asian and not ((not na(in_asian_1)) and bool(in_asian_1))
        if new_session:
            self.session_trades = 0
        under = self.session_trades < self.max_trades
        if in_build:
            self.range_high = float(high) if na(self.range_high) else float(pmath.max(self.range_high, high))
            self.range_low = float(low) if na(self.range_low) else float(pmath.min(self.range_low, low))
        if new_session:
            self.high_locked = self.range_high
            self.low_locked = self.range_low
            self.range_mid = (self.range_high + self.range_low) / 2
            self.range_high = NA
            self.range_low = NA
        hl, ll = self.high_locked, self.low_locked
        range_size = NA if (na(hl) or na(ll)) else hl - ll
        valid_range = (not na(range_size)) and range_size >= self.min_range and range_size <= self.max_range
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_len), lookahead=False)
        bull_bias = close > htf_ema
        bear_bias = close < htf_ema
        htf_long = (not self.use_htf) or bull_bias
        htf_short = (not self.use_htf) or bear_bias
        rsi = ta.rsi(close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        avg_vol = ta.sma(self.volume, self.vol_len)
        vol_break = (not self.use_vol) or self.volume > avg_vol * self.vol_break
        vol_fade = (not self.use_vol) or self.volume > avg_vol * self.vol_fade
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        breakout_long = (valid_range and close > hl + self.break_buf and close_1 <= hl + self.break_buf and rsi > self.rsi_break_min and vol_break and htf_long)
        breakout_short = (valid_range and close < ll - self.break_buf and close_1 >= ll - self.break_buf and rsi < self.rsi_break_max and vol_break and htf_short)
        tagged_high = high >= hl - self.mid_buf
        tagged_low = low <= ll + self.mid_buf
        fade_short = valid_range and tagged_high and close < hl and close_1 >= hl and rsi > self.rsi_ob and vol_fade and htf_short
        fade_long = valid_range and tagged_low and close > ll and close_1 <= ll and rsi < self.rsi_os and vol_fade and htf_long
        long_cond = bool(in_asian and under and st.position_size == 0 and (breakout_long or fade_long))
        short_cond = bool(in_asian and under and st.position_size == 0 and (breakout_short or fade_short))
        breakout_long_stop = ll - self.stop_buf
        breakout_short_stop = hl + self.stop_buf
        fade_long_stop = ll - self.stop_buf
        fade_short_stop = hl + self.stop_buf
        atr_long_stop = close - atr * self.atr_mult
        atr_short_stop = close + atr * self.atr_mult
        long_stop = pmath.min(fade_long_stop, atr_long_stop) if fade_long else pmath.min(breakout_long_stop, atr_long_stop)
        short_stop = pmath.max(fade_short_stop, atr_short_stop) if fade_short else pmath.max(breakout_short_stop, atr_short_stop)
        long_risk = close - long_stop
        short_risk = short_stop - close
        long_target = self.range_mid if fade_long else close + long_risk * self.rr
        short_target = self.range_mid if fade_short else close - short_risk * self.rr
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
