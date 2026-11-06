"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Universal Backtest Pro - Multi Strategy & Timeframe
Author       : Mukhlisilahi
Source URL   : https://www.tradingview.com/script/FRaZMTtI
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. One of five signal generators is selected (EMA9/21 cross with an EMA200 regime, RSI crossing its oversold / overbought lines the "wrong" way round as written, MACD cross,
Bollinger re-entry, SuperTrend flip, or a 5/10 SMA cross), computed on the OHLCV of the analysis timeframe (request.security). Inside the date window signals flip the position at the next open. While a
position exists a percentage stop, a percentage target and a trailing stop (half the target distance as activation, half the stop distance as offset, in ticks) are issued around position_avg_price, so
they first work on the bar after the fill.

Deviations from the original: the "2020-01-01T00:00:00" date strings (no zone) are read as GMT+0, written as timestamp("UTC", ...).
Not carried over: indicator plots, signal shapes, position background and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, ta

START_DATE = 1577836800000     # 2020-01-01T00:00:00 UTC
END_DATE = 1924991999000       # 2030-12-31T23:59:59 UTC


class UniversalBacktestPro(Script):
    TITLE = "Universal Backtest Pro - Multi Strategy & Timeframe"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent",
                    commission_value=0.01, slippage=2)
    SOURCE = {"id": "FRaZMTtI", "author": "Mukhlisilahi", "licence": "not stated", "url": "https://www.tradingview.com/script/FRaZMTtI"}

    def init(self):
        g = "1. Strategy Selection"
        self.strat_type = self.input.string("EMA Crossover", "Select Strategy", options=["EMA Crossover", "RSI Strategy", "MACD Strategy", "Bollinger Bands Breakout", "SuperTrend", "Custom"], group=g)
        self.tf_input = self.input.timeframe("D", "Analysis Timeframe", group=g)
        g = "2. EMA Parameters"
        self.ema_fast_len = self.input.int(9, "EMA Fast", group=g)
        self.ema_slow_len = self.input.int(21, "EMA Slow", group=g)
        self.regime_len = self.input.int(200, "Regime Filter EMA", group=g)
        g = "3. RSI Parameters"
        self.rsi_len = self.input.int(14, "RSI Period", group=g)
        self.rsi_ob = self.input.int(70, "Overbought", group=g)
        self.rsi_os = self.input.int(30, "Oversold", group=g)
        g = "4. MACD Parameters"
        self.macd_fast = self.input.int(12, "MACD Fast", group=g)
        self.macd_slow = self.input.int(26, "MACD Slow", group=g)
        self.macd_signal = self.input.int(9, "MACD Signal", group=g)
        g = "5. Bollinger Parameters"
        self.bb_len = self.input.int(20, "BB Length", group=g)
        self.bb_mult = self.input.float(2.0, "BB StdDev", group=g)
        g = "6. SuperTrend Parameters"
        self.st_len = self.input.int(10, "ATR Period", group=g)
        self.st_mult = self.input.float(3.0, "Multiplier", group=g)
        g = "7. Backtest Period"
        self.start_date = self.input.time(START_DATE, "Start Date", group=g)
        self.end_date = self.input.time(END_DATE, "End Date", group=g)
        g = "8. Risk Management"
        self.sl_pct = self.input.float(2.0, "Stop Loss %", minval=0.1, group=g) / 100
        self.tp_pct = self.input.float(4.0, "Take Profit %", minval=0.1, group=g) / 100
        self.use_ts = self.input.bool(True, "Enable Trailing Stop", group=g)

    def on_bar(self):
        in_date_range = self.time >= self.start_date and self.time <= self.end_date
        o, h, l, c, v = self.security(None, self.tf_input, lambda s: (s.open, s.high, s.low, s.close, s.volume))
        ema_f = ta.ema(c, self.ema_fast_len)
        ema_s = ta.ema(c, self.ema_slow_len)
        regime_ema = ta.ema(c, self.regime_len)
        cross_up = ta.crossover(ema_f, ema_s)
        cross_dn = ta.crossunder(ema_f, ema_s)
        ema_long = cross_up and c > regime_ema
        ema_short = cross_dn and c < regime_ema
        rsi_val = ta.rsi(c, self.rsi_len)
        rsi_long = ta.crossunder(rsi_val, self.rsi_os)
        rsi_short = ta.crossover(rsi_val, self.rsi_ob)
        macd_line, sig_line, _ = ta.macd(c, self.macd_fast, self.macd_slow, self.macd_signal)
        macd_long = ta.crossover(macd_line, sig_line)
        macd_short = ta.crossunder(macd_line, sig_line)
        bb_mid, bb_up, bb_low = ta.bb(c, self.bb_len, self.bb_mult)
        bb_long = ta.crossover(c, bb_low)
        bb_short = ta.crossunder(c, bb_up)
        st_val, st_dir = ta.supertrend(self.st_mult, self.st_len)
        d = ta.change(st_dir)
        st_long = d < 0
        st_short = d > 0
        long_cond = False
        short_cond = False
        if self.strat_type == "EMA Crossover":
            long_cond, short_cond = ema_long, ema_short
        elif self.strat_type == "RSI Strategy":
            long_cond, short_cond = rsi_long, rsi_short
        elif self.strat_type == "MACD Strategy":
            long_cond, short_cond = macd_long, macd_short
        elif self.strat_type == "Bollinger Bands Breakout":
            long_cond, short_cond = bb_long, bb_short
        elif self.strat_type == "SuperTrend":
            long_cond, short_cond = st_long, st_short
        elif self.strat_type == "Custom":
            sma5 = ta.sma(c, 5)
            sma10 = ta.sma(c, 10)
            long_cond = ta.crossover(sma5, sma10)
            short_cond = ta.crossunder(sma5, sma10)
        st = self.strategy
        if in_date_range:
            if long_cond:
                st.entry("Long", st.long)
            if short_cond:
                st.entry("Short", st.short)
        mintick = self.syminfo.mintick
        if st.position_size > 0:
            avg = st.position_avg_price
            sl_price = avg * (1 - self.sl_pct)
            tp_price = avg * (1 + self.tp_pct)
            st.exit("Exit Long", "Long", stop=sl_price, limit=tp_price,
                    trail_points=div(avg * self.tp_pct / 2, mintick) if self.use_ts else NA,
                    trail_offset=div(avg * self.sl_pct / 2, mintick) if self.use_ts else NA)
        if st.position_size < 0:
            avg = st.position_avg_price
            sl_price = avg * (1 + self.sl_pct)
            tp_price = avg * (1 - self.tp_pct)
            st.exit("Exit Short", "Short", stop=sl_price, limit=tp_price,
                    trail_points=div(avg * self.tp_pct / 2, mintick) if self.use_ts else NA,
                    trail_offset=div(avg * self.sl_pct / 2, mintick) if self.use_ts else NA)
        self.plot(ema_f if self.strat_type == "EMA Crossover" else NA, "EMA Fast", color=color.blue)
        self.plot(ema_s if self.strat_type == "EMA Crossover" else NA, "EMA Slow", color=color.orange)
