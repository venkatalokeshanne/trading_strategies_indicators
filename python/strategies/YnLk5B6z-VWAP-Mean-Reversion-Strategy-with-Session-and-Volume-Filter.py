"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Mean Reversion + Session Filter
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/YnLk5B6z-VWAP-Mean-Reversion-Strategy-with-Session-and-Volume-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.vwap(hlc3) resets at each trading day's session start (symbol
session). The session window is [start, end) in New York time as in the original (`time <
sessionEnd`). barstate.isconfirmed is always true on historical bars.

Deviations from the original: none.
Not carried over: alert_message texts (alerts do not affect a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class VwapMeanReversionSession(Script):
    TITLE = "VWAP Mean Reversion + Session Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10,
                    commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "YnLk5B6z", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/YnLk5B6z-VWAP-Mean-Reversion-Strategy-with-Session-and-Volume-Filter"}

    def init(self):
        self.atr_len = self.input.int(14, "ATR Length", group="Entry")
        self.vwap_dist = self.input.float(1.5, "VWAP Distance (ATR mult)", group="Entry", step=0.1)
        self.vol_len = self.input.int(20, "Volume MA Length", group="Entry")
        self.sl_mult = self.input.float(1.5, "Stop ATR Multiplier", group="Risk", step=0.1)
        self.start_hour = self.input.int(9, "Session Start Hour (ET)", group="Session")
        self.start_min = self.input.int(45, "Session Start Min (ET)", group="Session")
        self.end_hour = self.input.int(15, "Session End Hour (ET)", group="Session")
        self.end_min = self.input.int(15, "Session End Min (ET)", group="Session")

    def on_bar(self):
        session_start = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(),
                                       self.start_hour, self.start_min, 0)
        session_end = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(),
                                     self.end_hour, self.end_min, 0)
        in_session = self.time >= session_start and self.time < session_end
        vwap_val = ta.vwap(self.hlc3)
        atr_val = ta.atr(self.atr_len)
        vol_avg = ta.sma(self.volume, self.vol_len)
        vol_weak = self.volume < vol_avg
        above_vwap = self.close > vwap_val + atr_val * self.vwap_dist
        below_vwap = self.close < vwap_val - atr_val * self.vwap_dist
        st = self.strategy
        long_cond = below_vwap and vol_weak and in_session and self.barstate.isconfirmed and st.position_size == 0
        short_cond = above_vwap and vol_weak and in_session and self.barstate.isconfirmed and st.position_size == 0
        if long_cond:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=self.close - atr_val * self.sl_mult, limit=vwap_val)
        if short_cond:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=self.close + atr_val * self.sl_mult, limit=vwap_val)
        self.plot(vwap_val, "VWAP", color=color.blue, linewidth=2)
        self.plot(vwap_val + atr_val * self.vwap_dist, "Upper Threshold", color=color.new(color.red, 60), linewidth=1)
        self.plot(vwap_val - atr_val * self.vwap_dist, "Lower Threshold", color=color.new(color.green, 60), linewidth=1)
        self.plotshape(long_cond)
        self.plotshape(short_cond)
