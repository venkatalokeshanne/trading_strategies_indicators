"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AI MES Structure Break Strategy
Author       : lylerh
Source URL   : https://www.tradingview.com/script/AzGi4Rwo-AI-MES-Structure-Break-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Inside two New York sessions (morning 09:30-11:30, afternoon 13:30-15:30; at most N trades per session window) a close through the last confirmed pivot high (low) with the close above (below) a higher-timeframe EMA (request.security, lookahead off), RSI beyond the midline and a volume surge opens a long (short) at the next open. The stop sits a buffer beyond the opposite pivot and the target is R:R times the risk from the signal close; the exit is issued while the trade is open. Everything is closed when a session ends.
Deviations from the original: none.
Not carried over: the alert messages and the last-bar status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class AiMesStructureBreak(Script):
    TITLE = "AI MES Structure Break Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.62)
    SOURCE = {"id": "AzGi4Rwo", "author": "lylerh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/AzGi4Rwo-AI-MES-Structure-Break-Strategy"}

    def init(self):
        i = self.input
        self.htf_tf = i.timeframe("15", "HTF Timeframe", group="Higher Timeframe")
        self.htf_ema_len = i.int(21, "HTF EMA Length", group="Higher Timeframe")
        self.pivot_len = i.int(3, "Pivot Lookback (bars each side)", group="Structure", minval=2, maxval=10)
        self.rsi_len = i.int(14, "RSI Length", group="Momentum")
        self.rsi_mid = i.float(50, "RSI Midline", group="Momentum")
        self.vol_len = i.int(20, "Volume MA Length", group="Volume")
        self.vol_mult = i.float(1.3, "Volume Multiplier", group="Volume", step=0.1)
        self.risk_ratio = i.float(1.5, "Reward:Risk Ratio", group="Risk", step=0.1)
        self.stop_buffer = i.float(1.0, "Stop Buffer (points beyond pivot)", group="Risk", step=0.25)
        self.max_trades = i.int(2, "Max Trades Per Session Window", group="Risk", minval=1, maxval=5)
        g = "Sessions"
        self.use_s1 = i.bool(True, "Use Morning Session", group=g)
        self.s1_start = i.int(9, "Morning Start Hour (ET)", group=g, minval=0, maxval=23)
        self.s1_end = i.int(11, "Morning End Hour (ET)", group=g, minval=0, maxval=23)
        self.s1_min = i.int(30, "Morning Start Minute", group=g, minval=0, maxval=59)
        self.s1_end_min = i.int(30, "Morning End Minute", group=g, minval=0, maxval=59)
        self.use_s2 = i.bool(True, "Use Afternoon Session", group=g)
        self.s2_start = i.int(13, "Afternoon Start Hour (ET)", group=g, minval=0, maxval=23)
        self.s2_end = i.int(15, "Afternoon End Hour (ET)", group=g, minval=0, maxval=23)
        self.s2_min = i.int(30, "Afternoon Start Minute", group=g, minval=0, maxval=59)
        self.s2_end_min = i.int(30, "Afternoon End Minute", group=g, minval=0, maxval=59)
        self.window_trades = 0
        self.last_piv_high = NA
        self.last_piv_low = NA
        self.entry_stop = NA
        self.entry_target = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        et_time = self.hour(self.time, "America/New_York") * 100 + self.minute(self.time, "America/New_York")
        t_h = self.H("et_time")
        et_1 = t_h[1]
        t_h.set(et_time)
        s1_start_t = self.s1_start * 100 + self.s1_min
        s1_end_t = self.s1_end * 100 + self.s1_end_min
        s2_start_t = self.s2_start * 100 + self.s2_min
        s2_end_t = self.s2_end * 100 + self.s2_end_min
        in_morning = self.use_s1 and et_time >= s1_start_t and et_time < s1_end_t
        in_afternoon = self.use_s2 and et_time >= s2_start_t and et_time < s2_end_t
        in_session = in_morning or in_afternoon
        prev_morning = self.use_s1 and (et_1 < s1_start_t or et_1 >= s1_end_t) and in_morning
        prev_afternoon = self.use_s2 and (et_1 < s2_start_t or et_1 >= s2_end_t) and in_afternoon
        new_window = prev_morning or prev_afternoon
        if new_window:
            self.window_trades = 0
        under_limit = self.window_trades < self.max_trades
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_ema_len), lookahead=False)
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
        avg_vol = ta.sma(self.volume, self.vol_len)
        high_vol = self.volume > avg_vol * self.vol_mult
        rsi_long = rsi > self.rsi_mid
        rsi_short = rsi < self.rsi_mid
        long_cond = bool(break_high and bull_bias and rsi_long and high_vol and in_session and under_limit and st.position_size == 0)
        short_cond = bool(break_low and bear_bias and rsi_short and high_vol and in_session and under_limit and st.position_size == 0)
        long_stop = self.last_piv_low - self.stop_buffer
        short_stop = self.last_piv_high + self.stop_buffer
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
            self.window_trades += 1
        if short_cond:
            self.entry_stop = float(short_stop)
            self.entry_target = float(short_target)
            st.entry("Short", st.short)
            self.window_trades += 1
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=self.entry_stop, limit=self.entry_target)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=self.entry_stop, limit=self.entry_target)
        sess_h = self.H("in_session")
        in_session_1 = sess_h[1]
        sess_h.set(in_session)
        session_end = (not in_session) and (not na(in_session_1)) and bool(in_session_1)
        if session_end:
            st.close_all(comment="Session End")
