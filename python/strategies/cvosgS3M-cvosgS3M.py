"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CryptoRSI
Author       : Konscio
Source URL   : https://www.tradingview.com/script/cvosgS3M
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Preset "Original": RSI(20) smoothed by SMA(10); long when it is above 60 while the
daily BITSTAMP:BTCUSD close is above its own daily EMA(50) (both through request.security, lookahead off); the long is
closed (next open) when the close crosses under its WMA(50). The "Agressif" preset (RSI 7, 80 / 70, no smoothing, RSI
exit) is kept. The smoothing method is a constant "SMA", so only that switch branch exists.

Deviations from the original: none (the market-filter symbol needs a data provider; AUXILIARY lists it).
Not carried over: the background colour and hlines (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class CryptoRsi(Script):
    TITLE = "CryptoRSI"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=1)
    SOURCE = {"id": "cvosgS3M", "author": "Konscio", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cvosgS3M"}

    def init(self):
        self.preset = self.input.string("Original", "Preset", options=["Original", "Agressif"])
        self.is_agressif = self.preset == "Agressif"
        self.rsi_period = 7 if self.is_agressif else 20
        self.buy_threshold = 80 if self.is_agressif else 60
        self.sell_threshold = 70 if self.is_agressif else 50
        self.use_wma_exit = False if self.is_agressif else True
        self.smooth_rsi_enabled = False if self.is_agressif else True
        self.market_filter_enabled = True
        self.wma_length = 50
        self.smooth_rsi_period = 10
        self.market_filter_ticker = "BITSTAMP:BTCUSD"
        self.market_filter_ema_period = 50

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_period)
        smooth_rsi = ta.sma(rsi, self.smooth_rsi_period)
        final_rsi = smooth_rsi if self.smooth_rsi_enabled else rsi
        market_close = self.security(self.market_filter_ticker, "D", lambda v: v.close)
        market_ema = self.security(self.market_filter_ticker, "D", lambda v: ta.ema(v.close, self.market_filter_ema_period))
        wma_exit = ta.wma(self.close, self.wma_length)
        market_above_ema = market_close > market_ema
        buy_condition = (not self.market_filter_enabled or market_above_ema) and final_rsi > self.buy_threshold
        sell_condition = ta.crossunder(self.close, wma_exit) if self.use_wma_exit else final_rsi < self.sell_threshold
        st = self.strategy
        if buy_condition:
            st.entry("Buy", st.long)
        if sell_condition:
            st.close("Buy")
        self.plot(final_rsi, "RSI", color=color.blue)
