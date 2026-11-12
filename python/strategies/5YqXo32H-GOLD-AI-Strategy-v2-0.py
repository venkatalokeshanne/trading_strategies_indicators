"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 🥇 GOLD AI Strategy v2.0
Author       : francescodimichele
Source URL   : https://www.tradingview.com/script/5YqXo32H
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Two six-point scores (long / short) add one point each for: close vs the 200 EMA, 21 vs 55 EMA, RSI between 50 and the overbought level (or oversold and 50), MACD line vs signal, close vs the Bollinger basis, stochastic K over D below 80 (under D above 20).
A trade needs the score at the minimum, the close on the right side of the 200 EMA, a London (07:00 - 16:00) or New York (13:00 - 21:00) bar, a volume spike (1.2 x average) and a trigger event (EMA cross, MACD cross, RSI bounce from oversold + 5 / overbought - 5, a Bollinger squeeze break is computed but unused, or a stochastic cross). Fewer open trades than the maximum are allowed.
The entry carries an exit order with an ATR stop, an ATR target and a trailing stop whose activation distance and offset are ATR x trailing % x 10 ticks.
Deviations from the original: none.
Not carried over: the EMA / Bollinger plots, signal markers, labels and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class GoldAiStrategy(Script):
    TITLE = "🥇 GOLD AI Strategy v2.0"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=5, commission_type="percent", commission_value=0.04, slippage=3)
    SOURCE = {"id": "5YqXo32H", "author": "francescodimichele", "licence": "not stated", "url": "https://www.tradingview.com/script/5YqXo32H"}

    def init(self):
        i = self.input
        g = "📈 Trend Filter"
        self.ema_fast = i.int(21, "EMA Fast", minval=5, maxval=50, group=g)
        self.ema_slow = i.int(55, "EMA Slow", minval=20, maxval=200, group=g)
        self.ema_trend = i.int(200, "EMA Trend (200)", minval=50, maxval=500, group=g)
        g = "🎯 Entry Signals"
        self.rsi_len = i.int(14, "RSI Length", minval=5, maxval=30, group=g)
        self.rsi_ob = i.int(70, "RSI Overbought", minval=60, maxval=90, group=g)
        self.rsi_os = i.int(30, "RSI Oversold", minval=10, maxval=40, group=g)
        self.macd_fast = i.int(12, "MACD Fast", minval=3, maxval=30, group=g)
        self.macd_slow = i.int(26, "MACD Slow", minval=10, maxval=60, group=g)
        self.macd_sig = i.int(9, "MACD Signal", minval=3, maxval=20, group=g)
        self.bb_len = i.int(20, "BB Length", minval=10, maxval=50, group=g)
        self.bb_mult = i.float(2.0, "BB StdDev", minval=1.0, maxval=3.5, group=g)
        self.stoch_k = i.int(14, "Stoch %K", minval=5, maxval=30, group=g)
        self.stoch_d = i.int(3, "Stoch %D", minval=1, maxval=10, group=g)
        self.stoch_smooth = i.int(3, "Stoch Smooth", minval=1, maxval=10, group=g)
        g = "📊 Volatility / ATR"
        self.atr_len = i.int(14, "ATR Length", minval=5, maxval=30, group=g)
        self.atr_mult_sl = i.float(1.8, "ATR Mult. SL", minval=0.5, maxval=5.0, group=g)
        self.atr_mult_tp = i.float(3.0, "ATR Mult. TP", minval=1.0, maxval=8.0, group=g)
        self.vol_filter = i.bool(True, "Volume Filter", group=g)
        self.vol_ma_len = i.int(20, "Volume MA Length", minval=5, maxval=50, group=g)
        g = "🛡️ Risk Management"
        self.use_trailing = i.bool(True, "Use Trailing Stop", group=g)
        self.trail_perc = i.float(0.8, "Trailing % (ATR-based)", minval=0.1, maxval=5.0, group=g)
        self.max_trades = i.int(1, "Max Concurrent Trades", minval=1, maxval=3, group=g)
        self.score_min = i.int(4, "Min Signal Score (1-6)", minval=1, maxval=6, group=g)
        g = "⏰ Session Filter"
        self.use_session = i.bool(True, "Enable Session Filter", group=g)
        self.london_open = i.session("0700-1600", "London Session", group=g)
        self.ny_open = i.session("1300-2100", "New York Session", group=g)
        self.sl_price = NA
        self.tp_price = NA
        self.entry_px = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        ema_f = ta.ema(close, self.ema_fast)
        ema_s = ta.ema(close, self.ema_slow)
        ema_t = ta.ema(close, self.ema_trend)
        rsi = ta.rsi(close, self.rsi_len)
        macd_line, signal_line, hist_line = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_sig)
        bb_mid, bb_upper, bb_lower = ta.bb(close, self.bb_len, self.bb_mult)
        stoch_k_val = ta.sma(ta.stoch(close, high, low, self.stoch_k), self.stoch_smooth)
        stoch_d_val = ta.sma(stoch_k_val, self.stoch_d)
        atr = ta.atr(self.atr_len)
        vol_ma = ta.sma(self.volume, self.vol_ma_len)
        high_vol = self.volume > vol_ma * 1.2
        score_long = 0
        score_long += 1 if close > ema_t else 0
        score_long += 1 if ema_f > ema_s else 0
        score_long += 1 if (rsi > 50 and rsi < self.rsi_ob) else 0
        score_long += 1 if macd_line > signal_line else 0
        score_long += 1 if close > bb_mid else 0
        score_long += 1 if (stoch_k_val > stoch_d_val and stoch_k_val < 80) else 0
        score_short = 0
        score_short += 1 if close < ema_t else 0
        score_short += 1 if ema_f < ema_s else 0
        score_short += 1 if (rsi < 50 and rsi > self.rsi_os) else 0
        score_short += 1 if macd_line < signal_line else 0
        score_short += 1 if close < bb_mid else 0
        score_short += 1 if (stoch_k_val < stoch_d_val and stoch_k_val > 20) else 0
        ema_cross_up = ta.crossover(ema_f, ema_s)
        ema_cross_down = ta.crossunder(ema_f, ema_s)
        macd_cross_up = ta.crossover(macd_line, signal_line)
        macd_cross_down = ta.crossunder(macd_line, signal_line)
        rsi_bounce_up = ta.crossover(rsi, self.rsi_os + 5)
        rsi_bounce_down = ta.crossunder(rsi, self.rsi_ob - 5)
        stoch_cross_up = ta.crossover(stoch_k_val, stoch_d_val) and stoch_k_val < 40
        stoch_cross_dn = ta.crossunder(stoch_k_val, stoch_d_val) and stoch_k_val > 60
        in_london = self.time_in_session(self.london_open) if self.use_session else True
        in_ny = self.time_in_session(self.ny_open) if self.use_session else True
        in_session = in_london or in_ny
        vol_ok = high_vol if self.vol_filter else True
        long_signal = in_session and vol_ok and score_long >= self.score_min and (ema_cross_up or macd_cross_up or rsi_bounce_up or stoch_cross_up) and close > ema_t
        short_signal = in_session and vol_ok and score_short >= self.score_min and (ema_cross_down or macd_cross_down or rsi_bounce_down or stoch_cross_dn) and close < ema_t
        sl_distance = atr * self.atr_mult_sl
        tp_distance = atr * self.atr_mult_tp
        if long_signal and st.opentrades < self.max_trades:
            self.entry_px = float(close)
            self.sl_price = close - sl_distance
            self.tp_price = close + tp_distance
            st.entry("LONG", st.long, comment="🟢 LONG")
            if self.use_trailing:
                st.exit("EXIT_L", "LONG", stop=self.sl_price, limit=self.tp_price, trail_points=atr * self.trail_perc * 10, trail_offset=atr * self.trail_perc * 10)
            else:
                st.exit("EXIT_L", "LONG", stop=self.sl_price, limit=self.tp_price)
        if short_signal and st.opentrades < self.max_trades:
            self.entry_px = float(close)
            self.sl_price = close + sl_distance
            self.tp_price = close - tp_distance
            st.entry("SHORT", st.short, comment="🔴 SHORT")
            if self.use_trailing:
                st.exit("EXIT_S", "SHORT", stop=self.sl_price, limit=self.tp_price, trail_points=atr * self.trail_perc * 10, trail_offset=atr * self.trail_perc * 10)
            else:
                st.exit("EXIT_S", "SHORT", stop=self.sl_price, limit=self.tp_price)
