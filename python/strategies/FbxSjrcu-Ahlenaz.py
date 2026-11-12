"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XRP Price Action + Volume Strategy
Author       : alirichh
Source URL   : https://www.tradingview.com/script/FbxSjrcu-Ahlenaz
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long when EMA50 > EMA200 and a green close breaks the previous 20-bar high on 1.5x average
volume; short is the mirror. Both strategy.exit calls are unconditional ATR stops around the current close (1.5 ATR), so
bar i works with bar i-1's level (also on a fill bar) and reversals leave the other side's exit idle.

Deviations from the original: none.
Not carried over: the EMA plots, signal shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class XrpPriceActionVolume(Script):
    TITLE = "XRP Price Action + Volume Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "FbxSjrcu", "author": "alirichh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/FbxSjrcu-Ahlenaz"}

    def init(self):
        self.fast_ema = self.input.int(50, "Fast EMA")
        self.slow_ema = self.input.int(200, "Slow EMA")
        self.vol_length = self.input.int(20, "Volume SMA Length")
        self.breakout_lookback = self.input.int(20, "Resistance Lookback")
        self.risk_atr = self.input.float(1.5, "ATR Stop Multiplier")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.fast_ema)
        ema_slow = ta.ema(self.close, self.slow_ema)
        vol_ma = ta.sma(self.volume, self.vol_length)
        high_resistance = S(ta.highest(self.high, self.breakout_lookback))
        low_support = S(ta.lowest(self.low, self.breakout_lookback))
        atr = ta.atr(14)
        bull_trend = ema_fast > ema_slow
        bear_trend = ema_fast < ema_slow
        bull_breakout = self.close > high_resistance[1] and self.close > self.open and self.volume > vol_ma * 1.5
        bear_breakdown = self.close < low_support[1] and self.close < self.open and self.volume > vol_ma * 1.5
        buy_signal = bull_trend and bull_breakout
        sell_signal = bear_trend and bear_breakdown
        st = self.strategy
        if buy_signal:
            st.entry("BUY", st.long)
        if sell_signal:
            st.entry("SELL", st.short)
        long_stop = self.close - (atr * self.risk_atr)
        short_stop = self.close + (atr * self.risk_atr)
        st.exit("Exit Buy", "BUY", stop=long_stop)
        st.exit("Exit Sell", "SELL", stop=short_stop)
