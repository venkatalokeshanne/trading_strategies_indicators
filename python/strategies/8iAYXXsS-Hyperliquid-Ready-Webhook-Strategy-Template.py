"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Hyperliquid-Ready Webhook Strategy Template [PopsPineDev]
Author       : PopsPineDev
Source URL   : https://www.tradingview.com/script/8iAYXXsS-Hyperliquid-Ready-Webhook-Strategy-Template
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A fast / slow EMA cross with an RSI side filter opens a position at the close; the ATR stop and target are measured from the signal close. With the trailing option the stop ratchets toward price (only when the improvement is at least a fraction of an ATR) and the exit order is re-issued every bar with the trailed stop.

Deviations from the original: none.
Not carried over: the JSON webhook payloads (alert messages and alert() calls), the payload preview table and the plotted stop / target levels (output only, no effect on trades).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class HyperliquidWebhookTemplate(Script):
    TITLE = "Hyperliquid-Ready Webhook Strategy Template [PopsPineDev]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=5, commission_type="percent", commission_value=0.045,
                    slippage=2, process_orders_on_close=True)
    SOURCE = {"id": "8iAYXXsS", "author": "PopsPineDev", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8iAYXXsS-Hyperliquid-Ready-Webhook-Strategy-Template"}

    def init(self):
        i = self.input
        g = "Strategy"
        self.fast_len = i.int(21, "Fast EMA", minval=1, group=g)
        self.slow_len = i.int(55, "Slow EMA", minval=2, group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=2, group=g)
        self.rsi_long_min = i.int(50, "RSI ≥ for Longs", minval=0, maxval=100, group=g)
        self.rsi_short_max = i.int(50, "RSI ≤ for Shorts", minval=0, maxval=100, group=g)
        self.allow_longs = i.bool(True, "Enable Longs", group=g)
        self.allow_shorts = i.bool(True, "Enable Shorts", group=g)
        g = "Risk (ATR-based)"
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        self.sl_mult = i.float(1.5, "Stop-Loss  × ATR", minval=0.1, step=0.1, group=g)
        self.tp_mult = i.float(3.0, "Take-Profit × ATR", minval=0.1, step=0.1, group=g)
        g = "Trailing Stop (modify_sl events)"
        self.use_trail = i.bool(True, "ATR Trailing Stop (ratchet)", group=g)
        self.trail_mult = i.float(2.0, "Trail × ATR", minval=0.1, step=0.1, group=g)
        self.min_imp = i.float(0.25, "Min improvement to re-alert (× ATR)", minval=0.0, step=0.05, group=g)
        g = "Webhook Payload"
        i.string("hl_webhook_template", "Strategy ID (ownership tag)", group=g)
        i.float(5.0, "Position Size (% of equity)", minval=0.1, maxval=100, step=0.5, group=g)
        i.int(3, "Leverage (sent to backend)", minval=1, maxval=50, group=g)
        i.string("REPLACE_WITH_LONG_RANDOM_TOKEN", "Webhook Token", group=g)
        self.sl_stored = NA
        self.tp_stored = NA
        self.trail_sl = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema_fast = ta.ema(close, self.fast_len)
        ema_slow = ta.ema(close, self.slow_len)
        rsi_val = ta.rsi(close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        cross_up = ta.crossover(ema_fast, ema_slow)
        cross_dn = ta.crossunder(ema_fast, ema_slow)
        long_signal = bool(self.allow_longs and cross_up and rsi_val >= self.rsi_long_min)
        short_signal = bool(self.allow_shorts and cross_dn and rsi_val <= self.rsi_short_max)
        long_sl = close - atr_val * self.sl_mult
        long_tp = close + atr_val * self.tp_mult
        short_sl = close + atr_val * self.sl_mult
        short_tp = close - atr_val * self.tp_mult
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        if long_signal:
            self.sl_stored = float(long_sl)
            self.tp_stored = float(long_tp)
            self.trail_sl = float(long_sl)
            st.entry("Long", st.long)
        if short_signal:
            self.sl_stored = float(short_sl)
            self.tp_stored = float(short_tp)
            self.trail_sl = float(short_sl)
            st.entry("Short", st.short)
        if self.use_trail and in_long and not long_signal and not short_signal:
            cand_l = close - atr_val * self.trail_mult
            if cand_l > self.trail_sl + atr_val * self.min_imp:
                self.trail_sl = float(cand_l)
        if self.use_trail and in_short and not long_signal and not short_signal:
            cand_s = close + atr_val * self.trail_mult
            if cand_s < self.trail_sl - atr_val * self.min_imp:
                self.trail_sl = float(cand_s)
        if (long_signal or in_long) and not short_signal:
            stop_l = self.trail_sl if self.use_trail else self.sl_stored
            st.exit("Long-X", "Long", stop=stop_l, limit=self.tp_stored)
        if (short_signal or in_short) and not long_signal:
            stop_s = self.trail_sl if self.use_trail else self.sl_stored
            st.exit("Short-X", "Short", stop=stop_s, limit=self.tp_stored)
