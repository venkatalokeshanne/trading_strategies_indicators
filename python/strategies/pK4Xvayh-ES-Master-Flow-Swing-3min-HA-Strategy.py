"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ES Master Flow Swing [Strategy]
Author       : johnmurphy54180
Source URL   : https://www.tradingview.com/script/pK4Xvayh-ES-Master-Flow-Swing-3min-HA-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A Keltner channel breakout (close crossing the upper / lower band) in the direction of the EMA50 / EMA200 bias with ADX above a minimum, inside the cash session and while the daily-loss and consecutive-loss breakers allow, enters at the next open; an ATR trailing stop (initial 3 ATR from the signal bar's low / high, then a ratchet of 2.5 ATR from each bar's low / high) closes it, as do the end-of-day window and the risk halts.

Deviations from the original: none.
Not carried over: moving-average / MRC / VWAP / initial-balance plots, bar colouring, labels and the dashboard (display only; the initial-balance, MRC and VWAP values never feed the orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class EsMasterFlowSwing(Script):
    TITLE = "ES Master Flow Swing [Strategy]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=2.50, slippage=1)
    SOURCE = {"id": "pK4Xvayh", "author": "johnmurphy54180", "licence": "not stated",
              "url": "https://www.tradingview.com/script/pK4Xvayh-ES-Master-Flow-Swing-3min-HA-Strategy"}

    def init(self):
        i = self.input
        g = "Moving Averages"
        self.ema50_len = i.int(50, "EMA 50 Length", minval=1, group=g)
        self.ema200_len = i.int(200, "EMA 200 Length", minval=1, group=g)
        g = "Breakout & Signals"
        self.kc_len = i.int(20, "KC Length", group=g)
        self.kc_mult = i.float(2.0, "KC Multiplier", group=g)
        g = "Swing Management"
        self.sl_atr_mult = i.float(3.0, "Stop Loss (ATR Multiplier)", step=0.1, group=g)
        self.trail_mult = i.float(2.5, "Trailing Stop (ATR Multiplier)", step=0.1, group=g)
        self.adx_thresh = i.int(12, "Min ADX (Trending Threshold)", minval=1, group=g)
        g = "Risk Controls"
        self.use_session = i.bool(True, "Session Filter (Cash Only)", group=g)
        self.use_daily_loss = i.bool(True, "Daily Loss Limit", group=g)
        self.max_daily_loss = i.float(1000.0, "Max Daily Loss ($)", step=50.0, group=g)
        self.use_consec = i.bool(True, "Consecutive Loss Breaker", group=g)
        self.max_consec = i.int(3, "Max Consecutive Losses", group=g)
        self.day_start_equity = NA
        self.daily_pnl = 0.0
        self.daily_halted = False
        self.consec_losses = 0
        self.last_trade_count = 0
        self.trail_stop = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        ema50 = ta.ema(close, self.ema50_len)
        ema200 = ta.ema(close, self.ema200_len)
        atr = ta.atr(14)
        new_session = ta.change(self.time_fn("D")) != 0
        bias_bull = close > ema200 and close > ema50
        bias_bear = close < ema200 and close < ema50
        _, upper, lower = ta.kc(close, self.kc_len, self.kc_mult)
        breakout_bull = ta.crossover(close, upper)
        breakout_bear = ta.crossunder(close, lower)
        _, _, adx_val = ta.dmi(14, 14)
        is_trending = adx_val > self.adx_thresh
        in_session = (not self.use_session) or not na(self.time_fn(None, "0930-1515", "America/New_York"))
        eod_exit = self.use_session and not na(self.time_fn(None, "1510-1515", "America/New_York"))
        if na(self.day_start_equity):
            self.day_start_equity = st.equity
        if new_session:
            self.day_start_equity = st.equity
            self.daily_pnl = 0.0
            self.daily_halted = False
        self.daily_pnl = st.equity - self.day_start_equity
        if self.use_daily_loss and self.daily_pnl <= -self.max_daily_loss:
            self.daily_halted = True
        if st.closedtrades > self.last_trade_count:
            last_profit = st.closedtrades_profit(st.closedtrades - 1)
            self.consec_losses = self.consec_losses + 1 if last_profit < 0 else 0
            self.last_trade_count = st.closedtrades
        consec_halted = self.use_consec and self.consec_losses >= self.max_consec
        risk_ok = (not self.daily_halted) and not consec_halted
        confirmed = self.barstate.isconfirmed
        long_trigger = bias_bull and is_trending and breakout_bull
        short_trigger = bias_bear and is_trending and breakout_bear
        long_signal = confirmed and long_trigger and in_session and risk_ok and st.position_size == 0
        short_signal = confirmed and short_trigger and in_session and risk_ok and st.position_size == 0
        if st.position_size > 0:
            new_trail = low - (atr * self.trail_mult)
            self.trail_stop = low - (atr * self.sl_atr_mult) if na(self.trail_stop) else pmath.max(self.trail_stop, new_trail)
        if st.position_size < 0:
            new_trail = high + (atr * self.trail_mult)
            self.trail_stop = high + (atr * self.sl_atr_mult) if na(self.trail_stop) else pmath.min(self.trail_stop, new_trail)
        if st.position_size == 0:
            self.trail_stop = NA
        trail_hit_long = confirmed and st.position_size > 0 and (not na(self.trail_stop)) and low <= self.trail_stop
        trail_hit_short = confirmed and st.position_size < 0 and (not na(self.trail_stop)) and high >= self.trail_stop
        if long_signal:
            st.entry("Long", st.long, comment="BUY")
            self.trail_stop = low - (atr * self.sl_atr_mult)
        if short_signal:
            st.entry("Short", st.short, comment="SELL")
            self.trail_stop = high + (atr * self.sl_atr_mult)
        if trail_hit_long:
            st.close("Long", comment="Trail Exit")
        if trail_hit_short:
            st.close("Short", comment="Trail Exit")
        if eod_exit:
            st.close_all(comment="EOD")
        if (self.daily_halted or consec_halted) and st.position_size != 0:
            st.close_all(comment="Risk Halt")
