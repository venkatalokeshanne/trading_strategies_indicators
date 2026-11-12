"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Swing Breakout Strategy (quant-core)
Author       : BitFundamental
Source URL   : https://www.tradingview.com/script/SFnKkOyk-Swing-Breakout-Strategy-quant-core
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long (flat only) when the close is above SMA50 and SMA200 with SMA50 over SMA200, breaks the
prior 50-bar closing high (the highest close of the 50 bars before this one) and volume is at least 1.5x its 50-bar
average. While a position is open at the close, peak (highest high since entry) and a ratcheting trail (peak - 4 ATR) are
updated and a stop exit at the trail is issued, so it first works on the bar after the fill; both vars reset when flat.

Deviations from the original: none.
Not carried over: the "developing" alert, alert() calls, MA / trail plots and backgrounds (no effect on orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class SwingBreakoutQuantCore(Script):
    TITLE = "Swing Breakout Strategy (quant-core)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.05, slippage=2, pyramiding=0)
    SOURCE = {"id": "SFnKkOyk", "author": "BitFundamental", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SFnKkOyk-Swing-Breakout-Strategy-quant-core"}

    def init(self):
        self.breakout_len = self.input.int(50, "Breakout lookback (N-day high)", minval=5)
        self.vol_mult = self.input.float(1.5, "Volume x 50d avg", minval=0.5, step=0.1)
        self.ma_fast = self.input.int(50, "Fast MA", minval=2)
        self.ma_slow = self.input.int(200, "Slow MA", minval=5)
        self.atr_len = self.input.int(14, "ATR length", minval=2)
        self.trail_mult = self.input.float(4.0, "ATR trailing multiple", minval=0.5, step=0.5)
        self.watch_pct = self.input.float(3.0, "Developing: % below breakout", minval=0.5, step=0.5)
        self.peak = NA
        self.trail = NA

    def on_bar(self):
        sma_f = ta.sma(self.close, self.ma_fast)
        sma_s = ta.sma(self.close, self.ma_slow)
        atrv = ta.atr(self.atr_len)
        vol_avg = ta.sma(self.volume, 50)
        prior_high = S(ta.highest(self.close, self.breakout_len))[1]
        warm = (not na(sma_s)) and (not na(vol_avg)) and (not na(prior_high))
        uptrend = self.close > sma_f and self.close > sma_s and sma_f > sma_s
        breakout = self.close > prior_high and self.volume >= self.vol_mult * vol_avg
        go_long = warm and uptrend and breakout
        st = self.strategy
        if go_long and st.position_size == 0:
            st.entry("Long", st.long)
        if st.position_size > 0:
            self.peak = float(self.high) if na(self.peak) else pmath.max(self.peak, self.high)
            cand = self.peak - self.trail_mult * atrv
            self.trail = cand if na(self.trail) else pmath.max(self.trail, cand)
            st.exit("Trail", from_entry="Long", stop=self.trail)
        else:
            self.peak = NA
            self.trail = NA
        self.plot(sma_f, "50 MA", color=color.orange)
        self.plot(sma_s, "200 MA", color=color.blue)
