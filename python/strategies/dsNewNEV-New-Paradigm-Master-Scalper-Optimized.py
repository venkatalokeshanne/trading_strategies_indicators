"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : New Paradigm: Master Scalper (Optimized)
Author       : zizi48174
Source URL   : https://www.tradingview.com/script/dsNewNEV-New-Paradigm-Master-Scalper-Optimized
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Walls sit 2 x (asset implied move x multiplier) from the session VWAP of hlc3. A bar that
touches the lower wall, closes green on a volume spike (volume > 1.5 x SMA20) above EMA200 enters long; the upper-wall
mirror enters short (reversing). Both strategy.exit calls are unconditional (profit / loss in ticks around the fill
price), so they also work on the fill bar.

Known caveat: `in_session = time(...) != na` is kept literally. With IEEE comparison semantics (as Python / pinelib) a
number or na is always `!= na`, so the NY-session restriction never filters anything. If TradingView evaluates
`!= na` differently, trades outside 08:00-15:00 New York would be dropped there.

Deviations from the original: none.
Not carried over: the alert() calls and the plots (no effect on orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class MasterScalper(Script):
    TITLE = "New Paradigm: Master Scalper (Optimized)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000)
    SOURCE = {"id": "dsNewNEV", "author": "zizi48174", "licence": "not stated",
              "url": "https://www.tradingview.com/script/dsNewNEV-New-Paradigm-Master-Scalper-Optimized"}

    def init(self):
        self.asset_type = self.input.string("Gold", "Asset Class", options=["NQ", "ES", "Gold"])
        self.vol_multiplier = self.input.float(1.0, "Global Vol Multiplier", step=0.1)
        self.tp_ticks = self.input.int(100, "Take Profit (Ticks)", step=10)
        self.sl_ticks = self.input.int(100, "Stop Loss (Ticks)", step=10)
        self.use_trend_filter = self.input.bool(True, "Use 200 EMA Trend Filter")
        self.use_session = self.input.bool(True, "Restrict to NY Session (08:00-15:00 EST)")

    def on_bar(self):
        t = self.time_fn(None, "0800-1500", "America/New_York")
        in_session = (t != NA) if self.use_session else True
        base_iv = 9.0 if self.asset_type == "NQ" else (7.5 if self.asset_type == "ES" else 5.0)
        final_iv = base_iv * self.vol_multiplier
        vwap_val = ta.vwap(self.hlc3)
        lower_target = vwap_val - (final_iv * 2)
        upper_target = vwap_val + (final_iv * 2)
        vol_ma = ta.sma(self.volume, 20)
        is_vol_spike = self.volume > vol_ma * 1.5
        ema200 = ta.ema(self.close, 200)
        trend_long = self.close > ema200 if self.use_trend_filter else True
        trend_short = self.close < ema200 if self.use_trend_filter else True
        bull_fade = (self.low <= lower_target * 1.001) and (self.close > self.open) and is_vol_spike and trend_long and in_session
        bear_fade = (self.high >= upper_target * 0.999) and (self.close < self.open) and is_vol_spike and trend_short and in_session
        st = self.strategy
        if bull_fade:
            st.entry("Long", st.long, comment="Fade L")
        if bear_fade:
            st.entry("Short", st.short, comment="Fade S")
        st.exit("Exit L", "Long", profit=self.tp_ticks, loss=self.sl_ticks)
        st.exit("Exit S", "Short", profit=self.tp_ticks, loss=self.sl_ticks)
        self.plot(vwap_val, "VWAP", color=color.gray)
        self.plot(lower_target, "Green Wall", color=color.green, linewidth=2)
        self.plot(upper_target, "Red Wall", color=color.red, linewidth=2)
