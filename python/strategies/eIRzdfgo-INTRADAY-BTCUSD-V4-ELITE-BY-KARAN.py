"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC V4 Multi-Engine FINAL FIXED
Author       : nzaucklandkaran
Source URL   : https://www.tradingview.com/script/eIRzdfgo-INTRADAY-BTCUSD-V4-ELITE-BY-KARAN
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. f_trend(tf) reads EMA20 / 50 / 200 of the 30-minute, 60-minute, 240-minute and daily bars through
request.security (lookahead off) and returns +1 for a stacked uptrend, -1 for a stacked downtrend; three of the four
agreeing is the higher-timeframe vote. On the chart, a stacked EMA20 > EMA50 > EMA200 trend with the vote, and either a
pullback candle (previous candle red but above EMA20, ATR above its SMA14) or a strong breakout candle, not extended more than
1 % beyond EMA20, enters when flat. Entry and strategy.exit (stop = bar low / high -/+ 0.2 %, 2 R target) are issued
together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the EMA plots and the trade-number labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BtcV4MultiEngine(Script):
    TITLE = "BTC V4 Multi-Engine FINAL FIXED"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "eIRzdfgo", "author": "nzaucklandkaran", "licence": "not stated",
              "url": "https://www.tradingview.com/script/eIRzdfgo-INTRADAY-BTCUSD-V4-ELITE-BY-KARAN"}

    def init(self):
        self.rr = self.input.float(2.0, "Risk Reward")
        self.sl_buffer = self.input.float(0.2, "SL Buffer (%)")

    def f_trend(self, tf):
        e20 = self.security(None, tf, lambda v: ta.ema(v.close, 20))
        e50 = self.security(None, tf, lambda v: ta.ema(v.close, 50))
        e200 = self.security(None, tf, lambda v: ta.ema(v.close, 200))
        if e20 > e50 and e50 > e200:
            return 1
        if e20 < e50 and e50 < e200:
            return -1
        return 0

    def on_bar(self):
        ema20 = ta.ema(self.close, 20)
        ema50 = ta.ema(self.close, 50)
        ema200 = ta.ema(self.close, 200)
        t30 = self.f_trend("30")
        t1h = self.f_trend("60")
        t4h = self.f_trend("240")
        t1d = self.f_trend("D")
        bull_votes = (1 if t30 == 1 else 0) + (1 if t1h == 1 else 0) + (1 if t4h == 1 else 0) + (1 if t1d == 1 else 0)
        bear_votes = (1 if t30 == -1 else 0) + (1 if t1h == -1 else 0) + (1 if t4h == -1 else 0) + (1 if t1d == -1 else 0)
        bull_htf = bull_votes >= 3
        bear_htf = bear_votes >= 3
        bull_trend = ema20 > ema50 and ema50 > ema200
        bear_trend = ema20 < ema50 and ema50 < ema200
        atr = ta.atr(14)
        atr_ma = ta.sma(atr, 14)
        vol_ok = atr > atr_ma
        candle_range = self.high - self.low
        strong_bull = self.close > self.high[1] and candle_range > atr
        strong_bear = self.close < self.low[1] and candle_range > atr
        c1, o1 = self.close[1], self.open[1]
        e20_prev = self.H("ema20")[1]
        self.H("ema20").set(ema20)
        pull_long = c1 < o1 and c1 > e20_prev
        pull_short = c1 > o1 and c1 < e20_prev
        late_long = self.close > ema20 * 1.01
        late_short = self.close < ema20 * 0.99
        pullback_buy = bull_trend and bull_htf and vol_ok and pull_long and not late_long
        breakout_buy = bull_trend and bull_htf and strong_bull and not late_long
        pullback_sell = bear_trend and bear_htf and vol_ok and pull_short and not late_short
        breakdown_sell = bear_trend and bear_htf and strong_bear and not late_short
        long_sl = self.low * (1 - self.sl_buffer / 100)
        short_sl = self.high * (1 + self.sl_buffer / 100)
        long_tp = self.close + (self.close - long_sl) * self.rr
        short_tp = self.close - (short_sl - self.close) * self.rr
        st = self.strategy
        if (pullback_buy or breakout_buy) and st.position_size == 0:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", "BUY", stop=long_sl, limit=long_tp)
        if (pullback_sell or breakdown_sell) and st.position_size == 0:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", "SELL", stop=short_sl, limit=short_tp)
        self.plot(ema20, color=color.blue)
        self.plot(ema50, color=color.green)
        self.plot(ema200, color=color.orange)
