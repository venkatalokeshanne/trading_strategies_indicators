"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Qing EMA + MACD + Squeeze
Author       : not stated
Source URL   : https://www.tradingview.com/script/PxAUrVvp
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A long opens on a MACD(6, 14, 8) line-over-signal cross-over when no trade is open and 5 bars have passed since the last close; the size risks 1 % of equity over 1.2 ATR(10) (at least 1 unit). With "Use Signal Crossover for Exit" on (default) the long is closed when the 10 SMA crosses under the 50 SMA, otherwise an ATR stop / 2.5 ATR target exit order is attached. Shorts (off by default) need the price above the 50 and 200 EMA, a 6/12 EMA cross-under, a MACD cross-under, the RSI under its threshold and an optional higher-timeframe SMA bias.
The EMA-squeeze, flatness and volume-spike conditions of the source only feed shading and a marker, never an order, and are not carried over (neither are the plots, labels and tables).
Deviations from the original: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class QingEmaMacd(Script):
    TITLE = "Qing EMA + MACD + Squeeze)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="cash", default_qty_value=1000, initial_capital=10000, commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "PxAUrVvp", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/PxAUrVvp"}

    def init(self):
        i = self.input
        self.veryshort_period = i.int(6, "Very Short EMA (6) Period", minval=1)
        self.shortest_period = i.int(12, "Shortest EMA (12) Period", minval=1)
        self.short_period = i.int(20, "Short EMA (20) Period", minval=1)
        self.long_period = i.int(50, "Long EMA (50) Period", minval=1)
        self.longer_period = i.int(100, "Longer EMA (100) Period", minval=1)
        self.longest_period = i.int(200, "Longest EMA (200) Period", minval=1)
        self.fast = i.int(6, "MACD Fast Length", minval=2, group="MACD")
        self.slow = i.int(14, "MACD Slow Length", minval=2, group="MACD")
        self.sig_len = i.int(8, "MACD Signal Length", minval=2, group="MACD")
        g = "Entry Filters"
        self.sma_short = i.int(10, "Trend Filter Short SMA Length", minval=1, group=g)
        self.sma_long = i.int(50, "Trend Filter Long SMA Length", minval=1, group=g)
        self.higher_tf = i.timeframe("D", "Higher Timeframe", group=g)
        self.use_higher_tf = i.bool(False, "Use Higher Timeframe Filter?", group=g)
        self.sma_short_tf = i.int(10, "Higher TF Short SMA", minval=1, group=g)
        self.sma_long_tf = i.int(50, "Higher TF Long SMA", minval=1, group=g)
        self.cooldown_bars = i.int(5, "Cooldown Bars Between Trades", minval=1, group=g)
        self.rsi_period = i.int(14, "RSI Period", minval=1, group=g)
        self.rsi_bullish_threshold = i.int(55, "RSI Bullish Filter (e.g., >55)", minval=50, maxval=100, group=g)
        self.rsi_bearish_threshold = i.int(45, "RSI Bearish Filter (e.g., <45)", minval=0, maxval=50, group=g)
        g = "Risk Management"
        self.atr_period = i.int(10, "ATR Risk Period", minval=1, group=g)
        self.stop_loss_atr_factor = i.float(1.2, "ATR Stop Multiplier (1.2)", minval=0.1, step=0.1, group=g)
        self.take_profit_atr_factor = i.float(2.5, "ATR TP Multiplier (2.5)", minval=0.1, step=0.1, group=g)
        self.max_risk_pct = i.float(1.0, "Max Risk per Trade (%)", minval=0.1, step=0.1, group=g) / 100
        g = "Trade Control"
        self.allow_shorts = i.bool(False, "Allow Short Trades?", group=g)
        self.use_signal_exit = i.bool(True, "Use Signal Crossover for Exit?", group=g)
        self.last_trade_close_bar = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        h_ot = self.H("ot")
        ot_1 = h_ot[1]
        veryshort = ta.ema(close, self.veryshort_period)
        shortest = ta.ema(close, self.shortest_period)
        long_ = ta.ema(close, self.long_period)
        longest = ta.ema(close, self.longest_period)
        macd_val, signal_val, _ = ta.macd(close, self.fast, self.slow, self.sig_len)
        macd_up = ta.crossover(macd_val, signal_val)
        macd_down = ta.crossunder(macd_val, signal_val)
        sma_short_val = ta.sma(close, self.sma_short)
        sma_long_val = ta.sma(close, self.sma_long)
        sma_short_higher = self.security(None, self.higher_tf, lambda v: ta.sma(v.close, self.sma_short_tf))
        sma_long_higher = self.security(None, self.higher_tf, lambda v: ta.sma(v.close, self.sma_long_tf))
        trend_down_higher = sma_short_higher < sma_long_higher
        mtf_bias_short = trend_down_higher if self.use_higher_tf else True
        rsi = ta.rsi(close, self.rsi_period)
        rsi_bearish = rsi < self.rsi_bearish_threshold
        ots = st.opentrades
        if ots == 0 and (not na(ot_1)) and ot_1 != 0:
            self.last_trade_close_bar = self.bar_index
        can_trade = na(self.last_trade_close_bar) or (self.bar_index - self.last_trade_close_bar >= self.cooldown_bars)
        context_counter_trend_short = close > long_ and close > longest
        cross_vs = ta.crossunder(veryshort, shortest)
        enter_long = macd_up and can_trade and ots == 0
        enter_short = context_counter_trend_short and cross_vs and macd_down and can_trade and ots == 0 and mtf_bias_short and rsi_bearish and self.allow_shorts
        exit_long = ta.crossunder(sma_short_val, sma_long_val)
        exit_short = ta.crossover(sma_short_val, sma_long_val)
        a_tr = ta.atr(self.atr_period)
        atr_stop_distance = a_tr * self.stop_loss_atr_factor
        max_dollar_risk = st.equity * self.max_risk_pct
        qty = div(max_dollar_risk, atr_stop_distance) if atr_stop_distance > 0 else 1
        qty = pmath.max(1, qty)
        if enter_long:
            long_sl = close - atr_stop_distance
            long_tp = close + atr_stop_distance * self.take_profit_atr_factor
            st.entry("Long", st.long, qty=qty)
            if not self.use_signal_exit:
                st.exit("Long Exit TP/SL", "Long", stop=long_sl, limit=long_tp, comment="TP/SL Exit Long")
        if self.use_signal_exit and exit_long and st.position_size > 0:
            st.close("Long", comment="Signal Exit Long (SMA Cross)")
        if enter_short:
            short_sl = close + atr_stop_distance
            short_tp = close - atr_stop_distance * self.take_profit_atr_factor
            st.entry("Short", st.short, qty=qty)
            if not self.use_signal_exit:
                st.exit("Short Exit TP/SL", "Short", stop=short_sl, limit=short_tp, comment="TP/SL Exit Short")
        if self.use_signal_exit and exit_short and st.position_size < 0:
            st.close("Short", comment="Signal Exit Short (SMA Cross)")
        h_ot.set(ots)
