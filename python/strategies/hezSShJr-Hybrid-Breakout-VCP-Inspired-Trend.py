"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Hybrid Breakout
Author       : blitz_locked
Source URL   : https://in.tradingview.com/script/hezSShJr-Hybrid-Breakout-VCP-Inspired-Trend
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close; the stop entry still fills intrabar when the market trades through its price). A stacked up-trend (close over the 50 / 150 / 200 MAs in order, the 200 MA rising over one bar and the lookback, the 50 MA not falling), a squeeze (the 3-bar high-low range
as a percentile of the last 150, or a tight close range), and a volume expansion, inside the date range and while flat, place a buy-stop at the previous bar's highest high of the last 3 bars (the order is replaced on every new signal bar and stays until filled).
While long, three exit orders are re-issued each bar from the average entry price: 25 % with a take-profit at +10 %, 50 % at +20 %, and the rest at +30 %, all with the stop at -8 %.
Deviations from the original: none.
Not carried over: the entry markers (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, ta

START_DATE = 1514764800000     # timestamp("2018-01-01")
END_DATE = 4070908800000       # timestamp("2099-01-01")


class HybridBreakout(Script):
    TITLE = "Hybrid Breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.05, process_orders_on_close=True)
    SOURCE = {"id": "hezSShJr", "author": "blitz_locked", "licence": "not stated",
              "url": "https://in.tradingview.com/script/hezSShJr-Hybrid-Breakout-VCP-Inspired-Trend"}

    def init(self):
        i = self.input
        g = "Trend Filter"
        self.src = i.source(self.close, "MA Source", group=g)
        self.len50 = i.int(50, "Fast MA Length", group=g)
        self.len150 = i.int(150, "Mid MA Length", group=g)
        self.len200 = i.int(200, "Slow MA Length", group=g)
        self.ma_up_lookback = i.int(20, "Bars Slow MA Must Be Rising Over", group=g)
        g = "Volatility / Pivot Filter"
        self.atr_len = i.int(3, "Range Length", group=g)
        self.lookback = i.int(150, "Percentile Lookback", group=g)
        self.percentile_max = i.int(40, "Max Range Percentile (Squeeze)", minval=1, maxval=100, group=g)
        self.close_range_max = i.float(4, "Max Close-Range % (Tight Squeeze)", group=g)
        g = "Volume Filter"
        self.use_vol_filter = i.bool(True, "Require Volume Expansion on Breakout", group=g)
        self.vol_ma_len = i.int(20, "Volume MA Length", group=g)
        self.vol_mult = i.float(1.2, "Volume Must Exceed MA x", minval=1.0, step=0.1, group=g)
        self.breakout_lookback = i.int(3, "Stop-Entry High Lookback", minval=1, group="Entry")
        g = "Risk Management"
        self.stop_loss_pct = i.float(8.0, "Stop Loss %", minval=0.1, group=g) / 100
        self.take1_pct = i.float(10.0, "Take Profit 1 %", minval=0.1, group=g) / 100
        self.take2_pct = i.float(20.0, "Take Profit 2 %", minval=0.1, group=g) / 100
        self.take3_pct = i.float(30.0, "Take Profit 3 %", minval=0.1, group=g) / 100
        g = "Date Range"
        self.start_date = i.time(START_DATE, "Start", group=g)
        self.end_date = i.time(END_DATE, "End", group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_date_range = self.time >= self.start_date and self.time <= self.end_date
        ma50 = ta.sma(self.src, self.len50)
        ma150 = ta.sma(self.src, self.len150)
        ma200 = ta.sma(self.src, self.len200)
        h50, h200 = self.H("ma50"), self.H("ma200")
        ma50_1 = h50[1]
        ma200_1 = h200[1]
        ma200_n = h200[self.ma_up_lookback]
        h50.set(ma50)
        h200.set(ma200)
        bullish_trend = close > ma50 and ma50 > ma150 and ma150 > ma200 and ma200 > ma200_1 and ma200 > ma200_n and ma50 >= ma50_1
        h_range = ta.highest(self.high, self.atr_len)
        l_range = ta.lowest(self.low, self.atr_len)
        range_pct = div(h_range - l_range, h_range) * 100
        h_close = ta.highest(close, self.atr_len)
        l_close = ta.lowest(close, self.atr_len)
        close_range_pct = div(h_close - l_close, h_close) * 100
        range_percentile = ta.percentrank(range_pct, self.lookback)
        range_squeeze = range_percentile <= self.percentile_max
        close_squeeze = close_range_pct <= self.close_range_max
        pivot = range_squeeze or close_squeeze
        vol_ma = ta.sma(self.volume, self.vol_ma_len)
        volume_ok = (not self.use_vol_filter) or self.volume > vol_ma * self.vol_mult
        recent_high = ta.highest(self.high, self.breakout_lookback)
        rh = self.H("recent_high")
        recent_high_1 = rh[1]
        rh.set(recent_high)
        long_signal = bullish_trend and pivot and volume_ok and in_date_range
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long, stop=recent_high_1)
        avg_price = st.position_avg_price
        stop_level = avg_price * (1 - self.stop_loss_pct)
        target1 = avg_price * (1 + self.take1_pct)
        target2 = avg_price * (1 + self.take2_pct)
        target3 = avg_price * (1 + self.take3_pct)
        if st.position_size > 0:
            st.exit("TP1", "Long", qty_percent=25, stop=stop_level, limit=target1)
            st.exit("TP2", "Long", qty_percent=50, stop=stop_level, limit=target2)
            st.exit("TP3", "Long", qty_percent=100, stop=stop_level, limit=target3)
