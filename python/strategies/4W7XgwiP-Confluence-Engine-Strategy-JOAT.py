"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Confluence Engine Strategy [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/4W7XgwiP-Confluence-Engine-Strategy-JOAT
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A linear-regression close crossing its signal SMA, with the EMA trend, the higher-timeframe EMA bias
(request.security, lookahead off), a volume spike, RSI cap, ATR trending regime and a 0-100 confluence score, opens a long / short while flat and out of cooldown.
The ATR at the fill bar sets the take-profit / stop around the average entry price (the exit is issued from the bar after the fill); a timeout and an EMA trend flip close the trade.
Deviations from the original: none (the unused htfClose request.security call is dropped).
Not carried over: signal labels, TP/SL lines, EMA plots, the regime background and the last-bar dashboard table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class ConfluenceEngineJoat(Script):
    TITLE = "Confluence Engine Strategy [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=5, commission_type="percent",
                    commission_value=0.05, slippage=2)
    SOURCE = {"id": "4W7XgwiP", "author": "officialjackofalltrades", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/4W7XgwiP-Confluence-Engine-Strategy-JOAT"}

    def init(self):
        i = self.input
        g = "Entry Engine"
        self.lr_len = i.int(9, "LR Length", group=g, minval=3)
        self.sig_len = i.int(5, "LR Signal Length", group=g, minval=2)
        self.fast_ema_len = i.int(20, "Fast EMA", group=g, minval=5)
        self.slow_ema_len = i.int(50, "Slow EMA", group=g, minval=10)
        self.atr_len = i.int(14, "ATR Length", group=g, minval=3)
        self.reg_len = i.int(50, "Regime ATR Length", group=g, minval=20)
        self.conf_score = i.int(50, "Min Confluence Score", group=g, minval=0, maxval=100)
        self.longs = i.bool(True, "Trade Long", group=g)
        self.shorts = i.bool(True, "Trade Short", group=g)
        g = "Filters"
        self.vol_filt = i.bool(True, "Require Volume Spike", group=g)
        self.vol_len = i.int(20, "Volume SMA Length", group=g, minval=5)
        self.vol_mult = i.float(1.0, "Volume Multiplier", group=g, minval=0.5, step=0.1)
        self.rsi_len = i.int(14, "RSI Length", group=g, minval=2)
        self.rsi_bull_max = i.int(72, "RSI Max for Longs", group=g, minval=50, maxval=99)
        self.rsi_bear_min = i.int(28, "RSI Min for Shorts", group=g, minval=1, maxval=50)
        self.cooldown = i.int(3, "Cooldown Bars After Exit", group=g, minval=0)
        self.reg_filter = i.bool(True, "Regime Filter (no ranging)", group=g)
        self.reg_thresh = i.float(0.85, "Trending Regime Threshold", group=g, minval=0.5, maxval=1.5, step=0.05)
        g = "Risk Management"
        self.risk_pct = i.float(5.0, "Risk Per Trade (%)", group=g, minval=0.5, maxval=25, step=0.5)
        self.sl_mult = i.float(1.5, "SL  (ATR x)", group=g, minval=0.5, step=0.25)
        self.tp_mult = i.float(2.5, "TP  (ATR x)", group=g, minval=0.5, step=0.25)
        self.timeout = i.int(20, "Timeout Exit (bars)", group="Exit Logic", minval=3)
        self.htf_tf = i.timeframe("60", "HTF Bias Timeframe", group="Exit Logic")
        self.last_exit_bar = NA
        self.entry_atr = NA
        self.entry_tp = NA
        self.entry_sl = NA
        self.entry_bar = NA
        self.in_long = False
        self.in_short = False
        self.prev_pos = 0.0

    def score_l(self, trend_up, htf_bull, vol_sma, rsi_val, is_trending):
        trend_s = 25 if trend_up else 0
        htf_s = 20 if htf_bull else 0
        vol_s = 20 if self.volume > vol_sma * 1.2 else (10 if self.volume > vol_sma else 0)
        rsi_s = min((55.0 - rsi_val) * 0.5, 20.0) if rsi_val < 50 else 0.0
        reg_s = 15 if is_trending else 0
        return int(min(trend_s + htf_s + int(vol_s) + int(rsi_s) + reg_s, 100))

    def score_s(self, trend_dn, htf_bear, vol_sma, rsi_val, is_trending):
        trend_s = 25 if trend_dn else 0
        htf_s = 20 if htf_bear else 0
        vol_s = 20 if self.volume > vol_sma * 1.2 else (10 if self.volume > vol_sma else 0)
        rsi_s = min((rsi_val - 45.0) * 0.5, 20.0) if rsi_val > 50 else 0.0
        reg_s = 15 if is_trending else 0
        return int(min(trend_s + htf_s + int(vol_s) + int(rsi_s) + reg_s, 100))

    def on_bar(self):
        st = self.strategy
        close = self.close
        lr_close = ta.linreg(close, self.lr_len, 0)
        sig_line = ta.sma(lr_close, self.sig_len)
        fast_ema = ta.ema(close, self.fast_ema_len)
        slow_ema = ta.ema(close, self.slow_ema_len)
        trend_up = fast_ema > slow_ema
        trend_dn = fast_ema < slow_ema
        atr14 = ta.atr(self.atr_len)
        atr_slow = ta.atr(self.reg_len)
        den = max(atr_slow, self.syminfo.mintick) if not na(atr_slow) else NA
        atr_ratio = div(atr14, den) if (not na(den) and den != 0.0) else 0.0
        is_trending = atr_ratio > self.reg_thresh or not self.reg_filter
        rsi_val = ta.rsi(close, self.rsi_len)
        vol_sma = ta.sma(self.volume, self.vol_len)
        vol_ok = (not self.vol_filt) or self.volume > vol_sma * self.vol_mult
        htf_ema_f = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.fast_ema_len), lookahead=False)
        htf_ema_s = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.slow_ema_len), lookahead=False)
        htf_bull = htf_ema_f > htf_ema_s
        htf_bear = htf_ema_f < htf_ema_s
        warmup = max(self.slow_ema_len * 2, self.reg_len * 2)
        is_ready = self.bar_index >= warmup
        lr_cross = ta.crossover(lr_close, sig_line)
        lr_under = ta.crossunder(lr_close, sig_line)
        long_score = self.score_l(trend_up, htf_bull, vol_sma, rsi_val, is_trending) if lr_cross else 0
        short_score = self.score_s(trend_dn, htf_bear, vol_sma, rsi_val, is_trending) if lr_under else 0
        bull_sig = bool(lr_cross and trend_up and htf_bull and vol_ok and rsi_val < self.rsi_bull_max and is_trending
                        and long_score >= self.conf_score and self.longs and is_ready)
        bear_sig = bool(lr_under and trend_dn and htf_bear and vol_ok and rsi_val > self.rsi_bear_min and is_trending
                        and short_score >= self.conf_score and self.shorts and is_ready)
        cooldown_ok = na(self.last_exit_bar) or (self.bar_index - self.last_exit_bar >= self.cooldown)
        pos = st.position_size
        if pos > 0 and self.prev_pos == 0:
            self.in_long = True
            self.in_short = False
            self.entry_atr = float(atr14)
            self.entry_bar = self.bar_index
        if pos < 0 and self.prev_pos == 0:
            self.in_short = True
            self.in_long = False
            self.entry_atr = float(atr14)
            self.entry_bar = self.bar_index
        if pos == 0 and self.prev_pos != 0:
            self.in_long = False
            self.in_short = False
            self.last_exit_bar = self.bar_index
        if self.in_long and not na(self.entry_atr):
            self.entry_tp = st.position_avg_price + self.entry_atr * self.tp_mult
            self.entry_sl = st.position_avg_price - self.entry_atr * self.sl_mult
        if self.in_short and not na(self.entry_atr):
            self.entry_tp = st.position_avg_price - self.entry_atr * self.tp_mult
            self.entry_sl = st.position_avg_price + self.entry_atr * self.sl_mult
        if bull_sig and cooldown_ok and pos == 0:
            st.entry("Long", st.long, comment="CES L " + str(long_score))
        if bear_sig and cooldown_ok and pos == 0:
            st.entry("Short", st.short, comment="CES S " + str(short_score))
        if self.in_long and not na(self.entry_tp) and not na(self.entry_sl):
            st.exit("TP/SL Long", "Long", limit=self.entry_tp, stop=self.entry_sl)
        if self.in_short and not na(self.entry_tp) and not na(self.entry_sl):
            st.exit("TP/SL Short", "Short", limit=self.entry_tp, stop=self.entry_sl)
        if self.in_long and not na(self.entry_bar) and self.bar_index - self.entry_bar >= self.timeout:
            st.close("Long", comment="Timeout")
        if self.in_short and not na(self.entry_bar) and self.bar_index - self.entry_bar >= self.timeout:
            st.close("Short", comment="Timeout")
        if self.in_long and trend_dn:
            st.close("Long", comment="Trend Flip")
        if self.in_short and trend_up:
            st.close("Short", comment="Trend Flip")
        self.prev_pos = pos
