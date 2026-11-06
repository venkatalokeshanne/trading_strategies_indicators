"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fibonacci Concept Execution Engine (Anchored)
Author       : QueenBee11_
Source URL   : https://www.tradingview.com/script/7TzVyaRI-Fibonacci-Concept-Execution-Engine
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). While the script's own "in trade" flag is off: with the close above both the 290 SMA and the 200 EMA (below both for shorts) a close crossing UNDER the 61.8 % retracement of the 20-bar range from its high (a close crossing OVER the retracement measured from the low for shorts) opens a trade with a fixed stop in ticks and a take-profit at the risk-reward multiple;
the entry and its exit order are issued together. The flag is then maintained by the script from the bar's high / low (stop or target touched, even on the signal bar itself): a bar touching the break-even level moves the stop to the entry price (the exit order is re-issued); the flag is cleared when the stop or target is touched.
Deviations from the original: none.
Not carried over: the trade lines and the statistics table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class FibConceptEngine(Script):
    TITLE = "Fibonacci Concept Execution Engine (Anchored)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = {}
    SOURCE = {"id": "7TzVyaRI", "author": "QueenBee11_", "licence": "not stated", "url": "https://www.tradingview.com/script/7TzVyaRI-Fibonacci-Concept-Execution-Engine"}

    def init(self):
        i = self.input
        g = "Fibonacci Settings"
        self.lookback = i.int(20, "Swing Lookback (Bars)", minval=5, group=g)
        self.fib_level = i.float(0.618, "Fibonacci Entry Level", step=0.01, group=g)
        g = "Moving Average Filters"
        self.use_ma = i.bool(True, "Use MA Filter (Above=Buy, Below=Sell)", group=g)
        self.sma_len = i.int(290, "SMA Length", minval=1, group=g)
        self.ema_len = i.int(200, "EMA Length", minval=1, group=g)
        g = "Trade Management"
        self.fixed_sl_ticks = i.int(100, "Fixed SL (Ticks)", minval=1, group=g)
        self.rr_ratio = i.float(2.0, "Risk:Reward Ratio", step=0.1, group=g)
        self.tp_ticks = i.int(0, "TP Ticks Buffer (Beyond Line)", minval=0, group=g)
        self.use_be = i.bool(True, "Enable Break Even (BE)", group=g)
        self.be_at_rr = i.float(1.0, "Trigger BE at RR (e.g., 1.0 = 1:1)", step=0.1, group=g)
        self.in_trade = False
        self.trade_dir = 0
        self.entry_p = NA
        self.sl_p = NA
        self.tp_p = NA
        self.be_p = NA
        self.be_active = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        sma_val = ta.sma(close, self.sma_len)
        ema_val = ta.ema(close, self.ema_len)
        long_ma_ok = (not self.use_ma) or (close > sma_val and close > ema_val)
        short_ma_ok = (not self.use_ma) or (close < sma_val and close < ema_val)
        high_ref = ta.highest(high, self.lookback)
        low_ref = ta.lowest(low, self.lookback)
        range_ref = high_ref - low_ref
        long_fib_level = high_ref - (range_ref * self.fib_level)
        short_fib_level = low_ref + (range_ref * self.fib_level)
        cross_dn = ta.crossunder(close, long_fib_level)
        cross_up = ta.crossover(close, short_fib_level)
        if not self.in_trade:
            long_condition = long_ma_ok and cross_dn
            short_condition = short_ma_ok and cross_up
            if long_condition or short_condition:
                self.in_trade = True
                self.trade_dir = 1 if long_condition else -1
                self.entry_p = float(close)
                self.be_active = False
                risk_dist = self.fixed_sl_ticks * mintick
                if long_condition:
                    self.sl_p = self.entry_p - risk_dist
                    self.tp_p = self.entry_p + (risk_dist * self.rr_ratio) + (self.tp_ticks * mintick)
                    self.be_p = self.entry_p + (risk_dist * self.be_at_rr)
                    st.entry("Long", st.long)
                    st.exit("Exit", "Long", stop=self.sl_p, limit=self.tp_p)
                else:
                    self.sl_p = self.entry_p + risk_dist
                    self.tp_p = self.entry_p - (risk_dist * self.rr_ratio) - (self.tp_ticks * mintick)
                    self.be_p = self.entry_p - (risk_dist * self.be_at_rr)
                    st.entry("Short", st.short)
                    st.exit("Exit", "Short", stop=self.sl_p, limit=self.tp_p)
        if self.in_trade:
            hit_sl = (self.trade_dir == 1 and low <= self.sl_p) or (self.trade_dir == -1 and high >= self.sl_p)
            hit_tp = (self.trade_dir == 1 and high >= self.tp_p) or (self.trade_dir == -1 and low <= self.tp_p)
            hit_be = (not self.be_active) and self.use_be and ((self.trade_dir == 1 and high >= self.be_p) or (self.trade_dir == -1 and low <= self.be_p))
            if hit_be:
                self.be_active = True
                self.sl_p = self.entry_p
                if self.trade_dir == 1:
                    st.exit("Exit", "Long", stop=self.sl_p, limit=self.tp_p)
                else:
                    st.exit("Exit", "Short", stop=self.sl_p, limit=self.tp_p)
            if hit_sl:
                self.in_trade = False
            elif hit_tp:
                self.in_trade = False
