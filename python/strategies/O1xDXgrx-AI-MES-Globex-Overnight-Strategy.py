"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AI MES Globex Overnight Strategy
Author       : lylerh
Source URL   : https://www.tradingview.com/script/O1xDXgrx-AI-MES-Globex-Overnight-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The high / low of the first half hour of the Globex session (18:00-18:30 New York) is locked when the trading part starts. Inside it (outside the 08:15-08:45 news blackout), while flat and under the per-session limit, a range breakout, a pivot-break trend entry (with the higher-timeframe EMA bias via request.security, lookahead off, RSI and volume filters) or a fade of the range edge opens a trade at the next open; stops use the pivot (or the ATR floor, whichever is wider), targets R:R times the risk or the range midpoint for pure fades. Everything closes when the sessions end. As in the source the trading condition `etTime < globexEnd or etTime >= globexStart` is combined with `etTime >= rangeEnd`, so the part after midnight is never traded.
Deviations from the original: none.
Not carried over: alert messages and the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AiMesGlobexOvernight(Script):
    TITLE = "AI MES Globex Overnight Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.62)
    SOURCE = {"id": "O1xDXgrx", "author": "lylerh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/O1xDXgrx-AI-MES-Globex-Overnight-Strategy"}

    def init(self):
        i = self.input
        g = "Session"
        self.gs_h = i.int(18, "Globex Start Hour (ET)", group=g, minval=0, maxval=23)
        self.gs_m = i.int(0, "Globex Start Minute (ET)", group=g, minval=0, maxval=59)
        self.re_h = i.int(18, "Range Build End Hour (ET)", group=g, minval=0, maxval=23)
        self.re_m = i.int(30, "Range Build End Minute (ET)", group=g, minval=0, maxval=59)
        self.ge_h = i.int(9, "Globex End Hour (ET)", group=g, minval=0, maxval=23)
        self.ge_m = i.int(30, "Globex End Minute (ET)", group=g, minval=0, maxval=59)
        g = "Range"
        self.min_range = i.float(3.0, "Min Range Size (pts)", group=g, step=0.5)
        self.max_range = i.float(25.0, "Max Range Size (pts)", group=g, step=0.5)
        self.break_buf = i.float(0.75, "Breakout Confirmation (pts)", group=g, step=0.25)
        self.fade_buf = i.float(1.0, "Fade Entry Buffer (pts)", group=g, step=0.25)
        g = "Higher Timeframe"
        self.htf_tf = i.timeframe("60", "HTF Timeframe", group=g)
        self.htf_len = i.int(21, "HTF EMA Length", group=g)
        self.use_htf = i.bool(True, "Use HTF Bias Filter", group=g)
        g = "Momentum"
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.rsi_ob = i.float(65, "RSI Overbought (fade threshold)", group=g, step=1.0)
        self.rsi_os = i.float(35, "RSI Oversold (fade threshold)", group=g, step=1.0)
        self.rsi_break_min = i.float(52, "RSI Min for breakout longs", group=g, step=1.0)
        self.rsi_break_max = i.float(48, "RSI Max for breakout shorts", group=g, step=1.0)
        g = "Volume"
        self.vol_len = i.int(20, "Volume MA Length", group=g)
        self.vol_break = i.float(1.3, "Volume Multiplier (breakout)", group=g, step=0.1)
        self.vol_fade = i.float(0.7, "Volume Multiplier (fade)", group=g, step=0.1)
        self.use_vol = i.bool(True, "Use Volume Filter", group=g)
        self.pivot_len = i.int(4, "Pivot Lookback (bars each side)", group="Structure", minval=2, maxval=10)
        g = "Risk"
        self.rr = i.float(1.5, "Reward:Risk Ratio", group=g, step=0.1)
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_mult = i.float(2.0, "ATR Stop Multiplier (wider overnight)", group=g, step=0.1)
        self.stop_buf = i.float(2.0, "Stop Buffer beyond range (pts)", group=g, step=0.25)
        self.max_trades = i.int(2, "Max Trades Per Session", group=g, minval=1, maxval=5)
        g = "News Blackout"
        self.use_news = i.bool(True, "Use News Blackout Window", group=g)
        self.bo_s_h = i.int(8, "Blackout Start Hour (ET)", group=g, minval=0, maxval=23)
        self.bo_s_m = i.int(15, "Blackout Start Minute (ET)", group=g, minval=0, maxval=59)
        self.bo_e_h = i.int(8, "Blackout End Hour (ET)", group=g, minval=0, maxval=23)
        self.bo_e_m = i.int(45, "Blackout End Minute (ET)", group=g, minval=0, maxval=59)
        self.session_trades = 0
        self.range_high = NA
        self.range_low = NA
        self.high_locked = NA
        self.low_locked = NA
        self.range_mid = NA
        self.last_piv_high = NA
        self.last_piv_low = NA
        self.entry_stop = NA
        self.entry_target = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        et = self.hour(self.time, "America/New_York") * 100 + self.minute(self.time, "America/New_York")
        gs_t = self.gs_h * 100 + self.gs_m
        re_t = self.re_h * 100 + self.re_m
        ge_t = self.ge_h * 100 + self.ge_m
        bo_s = self.bo_s_h * 100 + self.bo_s_m
        bo_e = self.bo_e_h * 100 + self.bo_e_m
        in_build = et >= gs_t and et < re_t
        in_globex = (et >= re_t) and (et < ge_t or et >= gs_t)
        in_any = in_build or in_globex
        in_blackout = self.use_news and et >= bo_s and et < bo_e
        ig_h, an_h = self.H("in_globex"), self.H("in_any")
        in_globex_1, in_any_1 = ig_h[1], an_h[1]
        ig_h.set(in_globex)
        an_h.set(in_any)
        new_session = in_globex and not ((not na(in_globex_1)) and bool(in_globex_1))
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
        piv_high = ta.pivothigh(high, self.pivot_len, self.pivot_len)
        piv_low = ta.pivotlow(low, self.pivot_len, self.pivot_len)
        if not na(piv_high):
            self.last_piv_high = float(piv_high)
        if not na(piv_low):
            self.last_piv_low = float(piv_low)
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        pivot_break_high = (not na(self.last_piv_high)) and close > self.last_piv_high and close_1 <= self.last_piv_high
        pivot_break_low = (not na(self.last_piv_low)) and close < self.last_piv_low and close_1 >= self.last_piv_low
        rsi = ta.rsi(close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        avg_vol = ta.sma(self.volume, self.vol_len)
        vol_break = (not self.use_vol) or self.volume > avg_vol * self.vol_break
        vol_fade = (not self.use_vol) or self.volume > avg_vol * self.vol_fade
        range_break_long = (valid_range and close > hl + self.break_buf and close_1 <= hl + self.break_buf and rsi > self.rsi_break_min and vol_break and htf_long)
        range_break_short = (valid_range and close < ll - self.break_buf and close_1 >= ll - self.break_buf and rsi < self.rsi_break_max and vol_break and htf_short)
        trend_long = pivot_break_high and bull_bias and rsi > self.rsi_break_min and vol_break
        trend_short = pivot_break_low and bear_bias and rsi < self.rsi_break_max and vol_break
        breakout_long = range_break_long or trend_long
        breakout_short = range_break_short or trend_short
        tagged_high = high >= hl - self.fade_buf
        tagged_low = low <= ll + self.fade_buf
        fade_short = valid_range and tagged_high and close < hl and close_1 >= hl and rsi > self.rsi_ob and vol_fade and htf_short
        fade_long = valid_range and tagged_low and close > ll and close_1 <= ll and rsi < self.rsi_os and vol_fade and htf_long
        long_cond = bool(in_globex and under and st.position_size == 0 and (not in_blackout) and (breakout_long or fade_long))
        short_cond = bool(in_globex and under and st.position_size == 0 and (not in_blackout) and (breakout_short or fade_short))
        atr_long_stop = close - atr * self.atr_mult
        atr_short_stop = close + atr * self.atr_mult
        piv_long_stop = atr_long_stop if na(self.last_piv_low) else self.last_piv_low - self.stop_buf
        piv_short_stop = atr_short_stop if na(self.last_piv_high) else self.last_piv_high + self.stop_buf
        long_stop = pmath.min(piv_long_stop, atr_long_stop)
        short_stop = pmath.max(piv_short_stop, atr_short_stop)
        long_risk = close - long_stop
        short_risk = short_stop - close
        long_target = self.range_mid if (fade_long and not breakout_long) else close + long_risk * self.rr
        short_target = self.range_mid if (fade_short and not breakout_short) else close - short_risk * self.rr
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
