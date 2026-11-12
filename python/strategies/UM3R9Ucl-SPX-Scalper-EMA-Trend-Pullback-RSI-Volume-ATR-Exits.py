"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SPX Scalper: EMA Trend + Pullback + RSI/Volume + ATR Exits (v5)
Author       : moneymakersach
Source URL   : https://www.tradingview.com/script/UM3R9Ucl-SPX-Scalper-EMA-Trend-Pullback-RSI-Volume-ATR-Exits
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In the regular session, a pullback to the fast EMA in an EMA9/21 trend (with the EMA200 filter) plus an RSI 50 cross and a volume
confirmation enters (a signal against the open side reverses it). Both strategy.exit calls run unconditionally every bar with ATR stop / target levels around the
position average price (na while flat, so inactive; the old average applies on a reversal bar). trail_points is given without trail_offset, which in Pine
creates no trailing stop. A time stop and a session-end exit close everything at the next open.

Deviations from the original: none.
Not carried over: the signal shapes and the VolOK character plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class SPXScalper(Script):
    TITLE = "SPX Scalper: EMA Trend + Pullback + RSI/Volume + ATR Exits (v5)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, commission_type="percent", commission_value=0.0, initial_capital=100000,
                    default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "UM3R9Ucl", "author": "moneymakersach", "licence": "not stated",
              "url": "https://www.tradingview.com/script/UM3R9Ucl-SPX-Scalper-EMA-Trend-Pullback-RSI-Volume-ATR-Exits"}

    def init(self):
        self.fast_len = self.input.int(9, "Fast EMA", minval=1)
        self.slow_len = self.input.int(21, "Slow EMA", minval=1)
        self.trend_len = self.input.int(200, "Trend Filter EMA (optional)", minval=1)
        self.use_trend200 = self.input.bool(True, "Require price above/below EMA(Trend)")
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.rsi_long = self.input.int(50, "RSI long trigger (cross above)")
        self.rsi_short = self.input.int(50, "RSI short trigger (cross below)")
        self.vol_len = self.input.int(20, "Volume MA Length", minval=1)
        self.vol_mult = self.input.float(1.10, "Volume confirmation multiplier", step=0.05)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.stop_atr = self.input.float(1.0, "Stop = ATR *", step=0.1)
        self.target_atr = self.input.float(1.3, "Target = ATR *", step=0.1)
        self.trail_atr = self.input.float(0.8, "Trail = ATR * (0 disables)", step=0.1)
        self.max_bars = self.input.int(18, "Time stop (bars). 0 disables", minval=0)
        self.session_filter = self.input.bool(True, "Trade only regular session (US equities hours)")
        self.trade_session = self.input.session("0930-1600", "Session (exchange time)")
        self.bars_in_trade = 0

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        trend_ema = ta.ema(self.close, self.trend_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        atr = ta.atr(self.atr_len)
        in_session = (not self.session_filter) or not na(self.time_fn(None, self.trade_session, self.syminfo.timezone))
        vol_ok = self.volume > vol_ma * self.vol_mult
        trend_up = fast_ema > slow_ema
        trend_down = fast_ema < slow_ema
        up_ok = (not self.use_trend200) or self.close > trend_ema
        down_ok = (not self.use_trend200) or self.close < trend_ema
        pullback_long = self.low <= fast_ema and self.close > fast_ema
        pullback_short = self.high >= fast_ema and self.close < fast_ema
        rsi_long_cross = ta.crossover(rsi, self.rsi_long)
        rsi_short_cross = ta.crossunder(rsi, self.rsi_short)
        long_signal = in_session and trend_up and up_ok and pullback_long and rsi_long_cross and vol_ok
        short_signal = in_session and trend_down and down_ok and pullback_short and rsi_short_cross and vol_ok
        st = self.strategy
        if long_signal:
            st.entry("L", st.long)
        if short_signal:
            st.entry("S", st.short)
        in_pos = st.position_size != 0
        self.bars_in_trade = self.bars_in_trade + 1 if in_pos else 0
        avg = st.position_avg_price
        long_stop = avg - atr * self.stop_atr
        long_limit = avg + atr * self.target_atr
        short_stop = avg + atr * self.stop_atr
        short_limit = avg - atr * self.target_atr
        trail_points = atr * self.trail_atr if self.trail_atr > 0 else NA
        st.exit("L-exit", from_entry="L", stop=long_stop, limit=long_limit, trail_points=trail_points)
        st.exit("S-exit", from_entry="S", stop=short_stop, limit=short_limit, trail_points=trail_points)
        if self.max_bars > 0 and in_pos and self.bars_in_trade >= self.max_bars:
            st.close_all(comment="TimeStop")
        if self.session_filter and not in_session and in_pos:
            st.close_all(comment="SessionEnd")
        self.plot(fast_ema, "Fast EMA", color=color.lime)
        self.plot(slow_ema, "Slow EMA", color=color.red)
        self.plot(trend_ema if self.use_trend200 else NA, "Trend EMA", color=color.blue)
