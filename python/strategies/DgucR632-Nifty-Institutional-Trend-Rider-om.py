"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Nifty Institutional Trend Rider
Author       : sojiritesh2003
Source URL   : https://www.tradingview.com/script/DgucR632-Nifty-Institutional-Trend-Rider-om
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. longStopPrice / shortStopPrice are ordinary (non-var) series that are reassigned
each bar; their [1] history comes from H(). The trailing stop ratchets from the close while in the
position (0 / 999999 when flat) and the exit is only issued while a position exists, so it first works on
the bar after the fill.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, nz, pmath, ta


class NiftyInstitutionalTrendRider(Script):
    TITLE = "Nifty Institutional Trend Rider"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "DgucR632", "author": "sojiritesh2003", "licence": "not stated",
              "url": "https://www.tradingview.com/script/DgucR632-Nifty-Institutional-Trend-Rider-om"}

    def init(self):
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_upper = self.input.int(60, "RSI Bullish (CE) Level")
        self.rsi_lower = self.input.int(40, "RSI Bearish (PE) Level")
        self.ema_len = self.input.int(20, "Trend Filter EMA")
        self.trail_perc = self.input.float(0.5, "Trailing Stop Loss (%)", step=0.1) / 100

    def on_bar(self):
        rsi_value = ta.rsi(self.close, self.rsi_len)
        vwap_value = ta.vwap(self.close)
        ema_value = ta.ema(self.close, self.ema_len)
        long_condition = self.close > vwap_value and self.close > ema_value and rsi_value > self.rsi_upper
        short_condition = self.close < vwap_value and self.close < ema_value and rsi_value < self.rsi_lower
        st = self.strategy
        if long_condition:
            st.entry("CE Entry", st.long)
        if short_condition:
            st.entry("PE Entry", st.short)
        prev_long = self.H("long_stop")[1]
        if st.position_size > 0:
            stop_value = self.close * (1 - self.trail_perc)
            long_stop_price = pmath.max(stop_value, nz(prev_long))
        else:
            long_stop_price = 0.0
        self.H("long_stop").set(long_stop_price)
        prev_short = self.H("short_stop")[1]
        if st.position_size < 0:
            stop_value = self.close * (1 + self.trail_perc)
            short_stop_price = pmath.min(stop_value, nz(999999 if prev_short == 0 else prev_short))
        else:
            short_stop_price = 999999
        self.H("short_stop").set(short_stop_price)
        if st.position_size > 0:
            st.exit("Exit CE", "CE Entry", stop=long_stop_price)
        if st.position_size < 0:
            st.exit("Exit PE", "PE Entry", stop=short_stop_price)
        self.plot(vwap_value, color=color.orange, title="VWAP (Institutional Avg)")
        self.plot(ema_value, color=color.blue, title="Trend EMA")
        self.plot(long_stop_price if st.position_size > 0 else NA, color=color.red, title="Trailing SL")
        self.plot(short_stop_price if st.position_size < 0 else NA, color=color.red, title="Trailing SL ")
