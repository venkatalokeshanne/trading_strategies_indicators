"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Scott Barclay's Three Musksteers
Author       : Midgar-
Source URL   : https://www.tradingview.com/script/QTxR4wWi-Scott-Barclay-s-Three-Musksteers
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Three votes - EMA50 over / under EMA200, RSI crossing back over 30 / under 70, and the close crossing back inside the lower / upper Bollinger band - and a
2-of-3 majority gives the buy / sell signal. Long-only (default): a buy opens a long, a sell closes it; "Short" and "Both" modes mirror it. Fills at the next open.

Deviations from the original: none.
Not carried over: signal tags, the status table and the webhook alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class ThreeMusksteers(Script):
    TITLE = "Scott Barclay's Three Muskateers"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=0, margin_short=0, pyramiding=0, initial_capital=10000, default_qty_type="percent_of_equity")
    SOURCE = {"id": "QTxR4wWi", "author": "Midgar-", "licence": "not stated",
              "url": "https://www.tradingview.com/script/QTxR4wWi-Scott-Barclay-s-Three-Musksteers"}

    def init(self):
        self.trade_direction = self.input.string("Long", "Trade Direction", options=["Long", "Short", "Both"], group="Signal Settings")
        self.show_buy_sell = self.input.bool(False, "Show Buy/Sell Tags", group="Display")
        self.show_status_box = self.input.bool(False, "Show Signal Status Box", group="Display")
        self.signal_hold_bars = self.input.int(1, "Trade Signal Hold Bars", minval=1, group="Display")
        self.enable_bot = self.input.bool(True, "Enable Bot (Webhook)", group="BOT CONTROL")
        self.chart_pos = self.input.string("top", "Chart Position", options=["top", "bottom"], group="BOT CONTROL")

    def on_bar(self):
        rsi = ta.rsi(self.close, 14)
        ema_fast = ta.ema(self.close, 50)
        ema_slow = ta.ema(self.close, 200)
        basis = ta.sma(self.close, 20)
        stdev_val = ta.stdev(self.close, 20)
        dev = 2.0 * stdev_val
        upper_bb = basis + dev
        lower_bb = basis - dev
        trend_bull = ema_fast > ema_slow
        trend_bear = ema_fast < ema_slow
        mean_rev_bull = ta.crossover(rsi, 30)
        mean_rev_bear = ta.crossunder(rsi, 70)
        arb_bull = ta.crossover(self.close, lower_bb)
        arb_bear = ta.crossunder(self.close, upper_bb)
        bull_count = (1 if trend_bull else 0) + (1 if mean_rev_bull else 0) + (1 if arb_bull else 0)
        bear_count = (1 if trend_bear else 0) + (1 if mean_rev_bear else 0) + (1 if arb_bear else 0)
        buy_signal = bull_count >= 2
        sell_signal = bear_count >= 2
        allow_long = self.trade_direction == "Long" or self.trade_direction == "Both"
        allow_short = self.trade_direction == "Short" or self.trade_direction == "Both"
        long_only = self.trade_direction == "Long"
        short_only = self.trade_direction == "Short"
        st = self.strategy
        open_long_event = allow_long and buy_signal and st.position_size <= 0
        open_short_event = allow_short and sell_signal and st.position_size >= 0
        close_long_event = long_only and sell_signal and st.position_size > 0
        close_short_event = short_only and buy_signal and st.position_size < 0
        if close_long_event:
            st.close("Long", comment="Three Muskateers Sell")
        if close_short_event:
            st.close("Short", comment="Three Muskateers Buy")
        if open_long_event:
            st.entry("Long", st.long, comment="Three Muskateers Buy")
        if open_short_event:
            st.entry("Short", st.short, comment="Three Muskateers Sell")
