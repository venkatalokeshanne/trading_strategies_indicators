"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC — Smart Pullback Liquidity + Adaptive RSI
Author       : jlall7892
Source URL   : https://www.tradingview.com/script/rZRYUxLb
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Long only. Trend: close over the 200 EMA, the 50 EMA over the 200 EMA and (optionally) a daily trend (daily close over the daily EMA 200, daily EMA 50 over EMA 200, daily RSI over 45 - request.security, lookahead off). A liquidity sweep (low under the lowest low of the previous lookback bars with a close back above it) followed within a few bars by a
close above that level, an RSI z-score that was below -1 on the previous bar and now crosses over -0.35, a higher close, a close not extended more than 1.5 ATR over the 50 EMA, an ADX and a volume filter, buys. Every bar two exit orders of 50 % each (take-profit 1 and 2 ATR multiples, common ATR stop) are re-issued from the average entry price (none while flat); a close under the 200 EMA closes the position.
Deviations from the original: none.
Not carried over: the sweep / buy markers and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, ta


class BtcSmartPullback(Script):
    TITLE = "BTC — Smart Pullback Liquidity + Adaptive RSI"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="percent", commission_value=0.05, default_qty_type="percent_of_equity", default_qty_value=2)
    SOURCE = {"id": "rZRYUxLb", "author": "jlall7892", "licence": "not stated", "url": "https://www.tradingview.com/script/rZRYUxLb"}

    def init(self):
        i = self.input
        self.rsi_len = i.int(14, "RSI longueur")
        self.lookback_low = i.int(20, "Lookback creux liquidité")
        self.reclaim_bars = i.int(5, "Réintégration max après sweep")
        self.ema_fast_len = i.int(50, "EMA rapide")
        self.ema_slow_len = i.int(200, "EMA lente")
        self.atr_len = i.int(14, "ATR longueur")
        self.stop_atr = i.float(1.8, "Stop ATR", step=0.1)
        self.tp1_atr = i.float(2.2, "TP1 ATR", step=0.1)
        self.tp2_atr = i.float(4.5, "TP2 ATR", step=0.1)
        self.use_daily_trend = i.bool(True, "Filtre tendance Daily")
        self.use_adx = i.bool(True, "Filtre ADX")
        self.adx_min = i.float(17, "ADX minimum", step=0.5)
        self.use_volume = i.bool(True, "Filtre volume")
        self.vol_len = i.int(50, "SMA volume")
        self.vol_mult = i.float(1.05, "Volume > SMA ×", step=0.05)

    def on_bar(self):
        st = self.strategy
        close, low = self.close, self.low
        rsi = ta.rsi(close, self.rsi_len)
        ema50 = ta.ema(close, self.ema_fast_len)
        ema200 = ta.ema(close, self.ema_slow_len)
        atr = ta.atr(self.atr_len)
        vol_sma = ta.sma(self.volume, self.vol_len)
        vol_ok = (not self.use_volume) or self.volume > vol_sma * self.vol_mult
        plus_di, minus_di, adx = ta.dmi(14, 14)
        adx_ok = (not self.use_adx) or adx > self.adx_min
        daily_close = self.security(None, "D", lambda v: v.close, lookahead=False)
        daily_ema50 = self.security(None, "D", lambda v: ta.ema(v.close, 50), lookahead=False)
        daily_ema200 = self.security(None, "D", lambda v: ta.ema(v.close, 200), lookahead=False)
        daily_rsi = self.security(None, "D", lambda v: ta.rsi(v.close, 14), lookahead=False)
        daily_trend_ok = daily_close > daily_ema200 and daily_ema50 > daily_ema200 and daily_rsi > 45
        trend_ok = close > ema200 and ema50 > ema200 and ((not self.use_daily_trend) or daily_trend_ok)
        rsi_mean = ta.sma(rsi, 50)
        rsi_dev = ta.stdev(rsi, 50)
        rsi_z = div(rsi - rsi_mean, rsi_dev) if rsi_dev != 0 else 0.0
        rsi_capitulation = rsi_z < -1.0
        cap_h = self.H("cap")
        rsi_capitulation_1 = cap_h[1]
        cap_h.set(rsi_capitulation)
        rsi_rebound = ta.crossover(rsi_z, -0.35)
        previous_low = ta.lowest(self.low[1], self.lookback_low)
        sweep = low < previous_low and close > previous_low
        bars_since_sweep = ta.barssince(sweep)
        reclaim_after_sweep = bars_since_sweep >= 0 and bars_since_sweep <= self.reclaim_bars and close > previous_low
        higher_close = close > self.close[1]
        not_extended = close < ema50 + atr * 1.5
        buy_signal = trend_ok and adx_ok and vol_ok and reclaim_after_sweep and bool(rsi_capitulation_1) and rsi_rebound and higher_close and not_extended
        if buy_signal:
            st.entry("Long", st.long)
        entry_price = st.position_avg_price
        stop_price = entry_price - atr * self.stop_atr
        tp1_price = entry_price + atr * self.tp1_atr
        tp2_price = entry_price + atr * self.tp2_atr
        st.exit("TP1", "Long", limit=tp1_price, stop=stop_price, qty_percent=50)
        st.exit("TP2", "Long", limit=tp2_price, stop=stop_price, qty_percent=50)
        exit_regime = st.position_size > 0 and close < ema200
        if exit_regime:
            st.close("Long", comment="Sortie régime cassé")
