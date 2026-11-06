"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold Swing More Trades 50 SL 100 TP
Author       : buckz121
Source URL   : https://www.tradingview.com/script/8b1AgVrV-Gold-Swing-More-Trades-50-SL-100-TP
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A pullback "reclaim" candle through EMA20 in the direction of the VWAP / EMA20-over-EMA50 trend, with RSI
confirmation, inside the Mon-Fri trade session and after a bar cooldown, enters at the bar close (process_orders_on_close) and
reverses an open opposite trade. The bracket (50 pips stop, 100 pips target, pip = 0.1) is fixed on the signal bar.

Deviations from the original: none.
Not carried over: signal tags / labels, shapes, alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, ta


class GoldSwing(Script):
    TITLE = "Gold Swing More Trades 50 SL 100 TP"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=500, default_qty_type="fixed", default_qty_value=0.1, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "8b1AgVrV", "author": "buckz121", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8b1AgVrV-Gold-Swing-More-Trades-50-SL-100-TP"}

    def init(self):
        self.ema_fast_len = self.input.int(20, "Fast EMA", minval=1)
        self.ema_slow_len = self.input.int(50, "Slow EMA", minval=1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.rsi_long_min = self.input.int(54, "RSI Long Min", minval=1, maxval=100)
        self.rsi_short_max = self.input.int(46, "RSI Short Max", minval=1, maxval=100)
        self.enable_longs = self.input.bool(True, "Enable Longs")
        self.enable_shorts = self.input.bool(True, "Enable Shorts")
        self.use_session_filter = self.input.bool(True, "Use Session Filter")
        self.trade_session = self.input.session("0600-2000", "Trade Session")
        self.cooldown_bars = self.input.int(2, "Cooldown Bars", minval=0, maxval=50)
        self.sl_pips = self.input.float(50.0, "SL Pips", minval=0.1, step=0.1)
        self.tp_pips = self.input.float(100.0, "TP Pips", minval=0.1, step=0.1)
        self.pip_size = self.input.float(0.1, "Pip Size", minval=0.00001, step=0.00001)
        self.show_trade_tag = self.input.bool(True, "Show Signal Tag")
        self.tag_atr_offset = self.input.float(0.45, "Tag ATR Offset", minval=0.05, step=0.05)
        self.tag_size = self.input.string("small", "Tag Size", options=["tiny", "small", "normal"])
        self.last_trade_bar = NA

    def on_bar(self):
        session_string = self.trade_session + ":23456"
        ema_fast = S(ta.ema(self.close, self.ema_fast_len))
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        vwap_val = ta.vwap(self.hlc3)
        in_session = not na(self.time_fn(None, session_string))
        session_ok = in_session if self.use_session_filter else True
        ema_fast_rising = ema_fast[0] > ema_fast[2]
        ema_fast_falling = ema_fast[0] < ema_fast[2]
        bull_trend = self.close > vwap_val and ema_fast[0] > ema_slow and ema_fast_rising
        bear_trend = self.close < vwap_val and ema_fast[0] < ema_slow and ema_fast_falling
        bull_reclaim = self.low <= ema_fast[0] and self.close > ema_fast[0] and self.close > self.open
        bear_reclaim = self.high >= ema_fast[0] and self.close < ema_fast[0] and self.close < self.open
        rsi_long_ok = rsi_val >= self.rsi_long_min
        rsi_short_ok = rsi_val <= self.rsi_short_max
        cooldown_ok = na(self.last_trade_bar) or (self.bar_index - self.last_trade_bar > self.cooldown_bars)
        st = self.strategy
        long_signal = self.enable_longs and session_ok and cooldown_ok and bull_trend and bull_reclaim and rsi_long_ok and st.position_size <= 0
        short_signal = self.enable_shorts and session_ok and cooldown_ok and bear_trend and bear_reclaim and rsi_short_ok and st.position_size >= 0
        if long_signal:
            entry_price = self.close
            st.entry("L", st.long)
            st.exit("LX", from_entry="L", stop=entry_price - (self.sl_pips * self.pip_size), limit=entry_price + (self.tp_pips * self.pip_size))
            self.last_trade_bar = self.bar_index
        if short_signal:
            entry_price = self.close
            st.entry("S", st.short)
            st.exit("SX", from_entry="S", stop=entry_price + (self.sl_pips * self.pip_size), limit=entry_price - (self.tp_pips * self.pip_size))
            self.last_trade_bar = self.bar_index
        self.plot(vwap_val, "VWAP", color=color.yellow, linewidth=2)
        self.plot(ema_fast[0], "EMA 20", color=color.aqua, linewidth=2)
        self.plot(ema_slow, "EMA 50", color=color.orange, linewidth=2)
