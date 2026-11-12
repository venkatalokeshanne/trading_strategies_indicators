"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Trend-Momentum Strategy v6
Author       : SystemsOverFeelings
Source URL   : https://www.tradingview.com/script/OKxIjdsz
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The %K line (SMA3 of a stochastic taken on RSI itself) crossing up through the oversold level with positive Chaikin Money Flow, an ATR above its own average and the
close above the EMA200 goes long; %K crossing down through the overbought level with negative CMF and the same volatility filter goes short (no trend filter on the short side). Entries reverse
the position; there are no other exits.

Deviations from the original: none.
Not carried over: the BTC-only warning label, the CMF / stochastic RSI plots, trend background and signal characters (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta

START_PERIOD = 1514764800000     # timestamp("01-01-2018") read as UTC


class BtcTrendMomentum(Script):
    TITLE = "BTC Trend-Momentum Strategy v6"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=0, initial_capital=1000, commission_type="percent",
                    commission_value=0.075, slippage=0, margin_long=0, margin_short=0)
    SOURCE = {"id": "OKxIjdsz", "author": "SystemsOverFeelings", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OKxIjdsz"}

    def init(self):
        self.start_period = self.input.time(START_PERIOD, "Start Date")
        self.ema_length = self.input.int(200, "EMA Länge", group="Trendfilter (EMA)")
        g = "Volumen (CMF)"
        self.cmf_length = self.input.int(20, "CMF Länge", group=g)
        self.cmf_thresh = self.input.float(0.0, "CMF Schwelle (Long > x / Short < -x)", step=0.01, group=g)
        g = "Oszillator (Stochastic RSI)"
        self.rsi_length = self.input.int(14, "RSI Länge", group=g)
        self.stoch_length = self.input.int(14, "Stochastic Länge", group=g)
        self.smooth_k = self.input.int(3, "%K Glättung", group=g)
        self.smooth_d = self.input.int(3, "%D Glättung", group=g)
        self.oversold_lvl = self.input.int(20, "Oversold Level", group=g)
        self.overbought_lvl = self.input.int(80, "Overbought Level", group=g)
        g = "Volatilitätsfilter (optional)"
        self.use_vol_filter = self.input.bool(True, "Nur bei erhöhter Volatilität handeln", group=g)
        self.atr_len = self.input.int(14, "ATR Länge", group=g)
        self.vol_filter_len = self.input.int(20, "ATR-Vergleichs-MA Länge", group=g)

    def on_bar(self):
        ema_trend = ta.ema(self.close, self.ema_length)
        trend_up = self.close > ema_trend
        rng = self.high - self.low
        mfm = div(((self.close - self.low) - (self.high - self.close)), rng) if rng != 0 else 0.0
        mfv = mfm * self.volume
        cmf = div(ta.msum(mfv, self.cmf_length), ta.msum(self.volume, self.cmf_length))
        cmf_bull = cmf > self.cmf_thresh
        cmf_bear = cmf < -self.cmf_thresh
        rsi_val = ta.rsi(self.close, self.rsi_length)
        stoch = ta.stoch(rsi_val, rsi_val, rsi_val, self.stoch_length)
        k_line = ta.sma(stoch, self.smooth_k)
        d_line = ta.sma(k_line, self.smooth_d)
        stoch_long_trigger = ta.crossover(k_line, self.oversold_lvl)
        stoch_short_trigger = ta.crossunder(k_line, self.overbought_lvl)
        atr_val = ta.atr(self.atr_len)
        atr_ma = ta.sma(atr_val, self.vol_filter_len)
        vol_ok = (not self.use_vol_filter) or atr_val > atr_ma
        long_cond = cmf_bull and stoch_long_trigger and vol_ok and self.time > self.start_period and trend_up
        short_cond = cmf_bear and stoch_short_trigger and vol_ok and self.time > self.start_period
        st = self.strategy
        if long_cond:
            st.entry("Long", st.long)
        if short_cond:
            st.entry("Short", st.short)
        self.plot(cmf, "Chaikin Money Flow", color=color.blue, linewidth=2)
        self.plot(k_line, "Stoch RSI %K", color=color.orange, linewidth=2)
        self.plot(d_line, "Stoch RSI %D", color=color.fuchsia)
