"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VuManChu WT Zero Cross V1.1b
Author       : VuManChu
Source URL   : https://www.tradingview.com/script/85naPMk3
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (orders at the bar's close: process_orders_on_close). The WaveTrend wt1 (EMA of the channel index of hlc3, 9 / 27) crossing over zero buys, crossing under sells, optionally filtered by the 200 EMA side; an opposite position is closed first and the new one is entered with 2 % of equity. Both positions carry a stop at the higher-timeframe parabolic SAR (twice the chart timeframe in "Auto" mode: 2 for 1, 10 for 5, 30 for 15, 60 for 30, 120 for 60, 480 for 240, "2D" for D, otherwise 120), re-issued every bar.
Deviations from the original: none.
Not carried over: plots, arrows and alert conditions.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, ta


class WtZeroCross(Script):
    TITLE = "VuManChu WT Zero Cross V1.1b"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True, default_qty_type="percent_of_equity", default_qty_value=2)
    SOURCE = {"id": "85naPMk3", "author": "VuManChu", "licence": "not stated", "url": "https://www.tradingview.com/script/85naPMk3"}

    def init(self):
        i = self.input
        self.wt_channel_len = i.int(9, "WT Channel Length", minval=1)
        self.wt_average_len = i.int(27, "WT Average Length", minval=1)
        self.wt_ma_len = i.int(3, "WT MA Length", minval=1)
        self.wt_source = i.source(self.hlc3, "WT Source")
        self.enable_trend_filter = i.bool(False, "Enable EMA Filter")
        self.ema_length = i.int(200, "EMA Length")
        self.psar_start = i.float(0.0075, "PSAR Start")
        self.psar_inc = i.float(0.0075, "PSAR Increment")
        self.psar_max = i.float(0.075, "PSAR Maximum")
        self.psar_tf = i.string("Auto", "PSAR Timeframe", options=["Auto", "5", "10", "15", "30", "60", "120", "240", "480", "D"])

    def on_bar(self):
        st = self.strategy
        close = self.close
        if self.psar_tf != "Auto":
            selected = self.psar_tf
        else:
            selected = {"1": "2", "5": "10", "15": "30", "30": "60", "60": "120", "240": "480", "D": "2D"}.get(self.timeframe.period, "120")
        src = self.wt_source
        esa = ta.ema(src, self.wt_channel_len)
        de = ta.ema(abs(src - esa), self.wt_channel_len)
        ci = div(src - esa, 0.015 * de)
        wt1 = ta.ema(ci, self.wt_average_len)
        wt2 = ta.sma(wt1, self.wt_ma_len)
        long_signal = ta.crossover(wt1, 0)
        short_signal = ta.crossunder(wt1, 0)
        ema_filter = ta.ema(close, self.ema_length)
        long_allowed = (not self.enable_trend_filter) or close > ema_filter
        short_allowed = (not self.enable_trend_filter) or close < ema_filter
        psar_htf = self.security(None, selected, lambda v: ta.sar(self.psar_start, self.psar_inc, self.psar_max))
        if long_signal and long_allowed:
            if st.position_size < 0:
                st.close("Short")
            st.entry("Long", st.long)
        if short_signal and short_allowed:
            if st.position_size > 0:
                st.close("Long")
            st.entry("Short", st.short)
        st.exit("Long Stop", from_entry="Long", stop=psar_htf)
        st.exit("Short Stop", from_entry="Short", stop=psar_htf)
