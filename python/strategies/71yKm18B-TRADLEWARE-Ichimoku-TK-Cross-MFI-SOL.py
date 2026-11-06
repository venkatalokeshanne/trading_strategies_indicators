"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TRADLEWARE-Ichimoku TK-Cross + MFI SOL
Author       : cs_lev
Source URL   : https://www.tradingview.com/script/71yKm18B-TRADLEWARE-Ichimoku-TK-Cross-MFI-SOL
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Long only: the Tenkan (20) crossing over the Kijun (60) with the close above the displaced Ichimoku cloud and the MFI above its gate, inside the date range, buys at the next open; the close below the Kijun exits at the next open,
and a stop at the bottom of the displaced cloud is re-issued at every bar of the position and works from the next bar.

Deviations from the original: none.
Not carried over: the cloud plots and BUY / SELL labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class IchimokuTkMfi(Script):
    TITLE = "TRADLEWARE-Ichimoku TK-Cross + MFI SOL"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=99.95, commission_type="percent", commission_value=0.1, slippage=3,
                    pyramiding=0, process_orders_on_close=False)
    SOURCE = {"id": "71yKm18B", "author": "cs_lev", "licence": "not stated",
              "url": "https://www.tradingview.com/script/71yKm18B-TRADLEWARE-Ichimoku-TK-Cross-MFI-SOL"}

    def init(self):
        g = "Date Range"
        self.start_year = self.input.int(2022, "Start year", minval=2000, maxval=2099, group=g)
        self.start_month = self.input.int(1, "Start month", minval=1, maxval=12, group=g)
        self.start_day = self.input.int(1, "Start day", minval=1, maxval=31, group=g)
        self.end_year = self.input.int(2099, "End year", minval=2000, maxval=2099, group=g)
        self.end_month = self.input.int(12, "End month", minval=1, maxval=12, group=g)
        self.end_day = self.input.int(31, "End day", minval=1, maxval=31, group=g)
        g = "Ichimoku"
        self.tenkan_len = self.input.int(20, "Tenkan length", minval=1, group=g)
        self.kijun_len = self.input.int(60, "Kijun length", minval=1, group=g)
        self.senkou_b_len = self.input.int(120, "Senkou B length", minval=1, group=g)
        g = "Money Flow Filter"
        self.mfi_len = self.input.int(14, "MFI length", minval=1, group=g)
        self.mfi_min = self.input.float(50.0, "MFI minimum (money flow gate)", minval=0, maxval=100, group=g)
        self.use_stop_loss = self.input.bool(True, "Stop-loss at cloud bottom", group="Stop Loss")

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        time_condition = (self.time >= self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
                          and self.time <= self.timestamp(self.end_year, self.end_month, self.end_day, 23, 59))
        displacement = self.kijun_len
        tenkan = (ta.highest(high, self.tenkan_len) + ta.lowest(low, self.tenkan_len)) / 2.0
        kijun = (ta.highest(high, self.kijun_len) + ta.lowest(low, self.kijun_len)) / 2.0
        lead_a = (tenkan + kijun) / 2.0
        lead_b = (ta.highest(high, self.senkou_b_len) + ta.lowest(low, self.senkou_b_len)) / 2.0
        la_h, lb_h = self.H("la"), self.H("lb")
        la_d = la_h[displacement]
        lb_d = lb_h[displacement]
        la_h.set(lead_a)
        lb_h.set(lead_b)
        cloud_top_now = pmath.max(la_d, lb_d)
        cloud_bottom_now = pmath.min(la_d, lb_d)
        mfi = ta.mfi(self.hlc3, self.mfi_len)
        tk_cross_up = ta.crossover(tenkan, kijun)
        above_cloud = close > cloud_top_now
        mfi_ok = mfi > self.mfi_min
        long_condition = tk_cross_up and above_cloud and mfi_ok and time_condition
        exit_condition = close < kijun and time_condition
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
        if exit_condition and st.position_size > 0:
            st.close("Long")
        if self.use_stop_loss and st.position_size > 0:
            st.exit("Stop", from_entry="Long", stop=cloud_bottom_now)
        self.plot(lead_a, "Senkou A", color=color.teal, offset=displacement)
        self.plot(lead_b, "Senkou B", color=color.red, offset=displacement)
