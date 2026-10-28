"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : LL: Momentum and Curl Master
Author       : ycelestine77
Source URL   : https://www.tradingview.com/script/yhoK9cH4-LL-Momentum-and-Curl-Master
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Positive (negative) 20-bar momentum with a rising (falling) SMA50, the EMA200 side and a 1.2x volume spike enters when flat. The stop is a fixed ATR multiple beyond the signal bar's
extreme; the target is 2x that ATR multiple from position_avg_price. The exit orders are only issued while a position exists (they work from the bar after the fill) and re-use the latest ATR for the target.

Deviations from the original: none.
Not carried over: alert() messages, the CALL / PUT labels and the status table.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class LlMomentumCurl(Script):
    TITLE = "LL: Momentum and Curl Master"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "yhoK9cH4", "author": "ycelestine77", "licence": "not stated",
              "url": "https://www.tradingview.com/script/yhoK9cH4-LL-Momentum-and-Curl-Master"}

    def init(self):
        self.use_trend_filter = self.input.bool(True, "Enable 200 EMA Trend Guardrail", group="Trend Filter")
        self.ema_length = self.input.int(200, "Macro Trend EMA Length", group="Trend Filter")
        self.atr_length = self.input.int(14, "ATR Length", group="Risk Management")
        self.long_stop_mult = self.input.float(2.0, "Long Stop (ATR Mult)", group="Risk Management")
        self.short_stop_mult = self.input.float(1.5, "Short Stop (ATR Mult)", group="Risk Management")
        self.alert_bot_id = self.input.string("default", "Bot/Webhook ID Filter", group="Automation Alerts")
        self.long_stop_price = NA
        self.short_stop_price = NA

    def on_bar(self):
        macro_ema = ta.ema(self.close, self.ema_length)
        atr = ta.atr(self.atr_length)
        mom = ta.mom(self.close, 20)
        sma_chg = ta.change(ta.sma(self.close, 50))
        base_long_signal = mom > 0 and sma_chg > 0
        base_short_signal = mom < 0 and sma_chg < 0
        vol_average = ta.sma(self.volume, 20)
        volume_filter = self.volume > (vol_average * 1.2)
        if self.use_trend_filter:
            long_condition = base_long_signal and self.close > macro_ema and volume_filter
            short_condition = base_short_signal and self.close < macro_ema and volume_filter
        else:
            long_condition = base_long_signal and volume_filter
            short_condition = base_short_signal and volume_filter
        st = self.strategy
        long_triggered = long_condition and st.position_size == 0
        short_triggered = short_condition and st.position_size == 0
        if long_triggered:
            st.entry("Long", st.long)
            self.long_stop_price = self.low - (atr * self.long_stop_mult)
        if short_triggered:
            st.entry("Short", st.short)
            self.short_stop_price = self.high + (atr * self.short_stop_mult)
        if st.position_size > 0:
            long_profit_price = st.position_avg_price + (atr * (self.long_stop_mult * 2))
            st.exit("Exit Long", "Long", stop=self.long_stop_price, limit=long_profit_price)
        if st.position_size < 0:
            short_profit_price = st.position_avg_price - (atr * (self.short_stop_mult * 2))
            st.exit("Exit Short", "Short", stop=self.short_stop_price, limit=short_profit_price)
        self.plot(macro_ema, "Macro Trend EMA", color=color.blue, linewidth=2)
