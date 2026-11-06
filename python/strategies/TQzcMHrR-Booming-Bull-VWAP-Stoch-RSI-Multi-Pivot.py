"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Booming Bull:VWAP + Stoch RSI + Multi-Pivot
Author       : The_Stock_Yogi
Source URL   : https://www.tradingview.com/script/TQzcMHrR-Booming-Bull-VWAP-Stoch-RSI-Multi-Pivot
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Inside the 09:15-15:00 IST window, a close crossing any of the previous day's classic pivot lines (P, R1-R3, S1-S3) in the direction of the VWAP side, with Stoch RSI
K above (below) D, enters when flat. The stop is the signal bar's low (high), the target 1.5R (or 1% of price), both fixed on the signal bar; everything is closed from 15:00 IST. The seven
crossover / crossunder calls of the chain are short-circuited by `or`, so each only advances its own history on the bars where it is evaluated (Pine v6 semantics, kept here).

Deviations from the original: none.
Not carried over: pivot / VWAP plots and bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class BoomingBull(Script):
    TITLE = "Booming Bull:VWAP + Stoch RSI + Multi-Pivot"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100, initial_capital=5000000, default_qty_type="percent_of_equity", default_qty_value=50)
    SOURCE = {"id": "TQzcMHrR", "author": "The_Stock_Yogi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TQzcMHrR-Booming-Bull-VWAP-Stoch-RSI-Multi-Pivot"}

    def init(self):
        self.efficiency_filter = self.input.bool(True, "Enable Efficiency Filter")
        self.only_central_pivot = self.input.bool(False, "Only Central Pivot")
        self.tz_offset = self.input.string("GMT+530", "Timezone Offset")
        self.session_input = self.input.session("0915-1500", "Trading Session Entry Window")
        self.profit_mode = self.input.string("Risk/Reward", "Profit Mode", options=["1% Price", "Risk/Reward"])
        self.rr_ratio = self.input.float(1.5, "Risk/Reward Ratio", minval=0.1)
        self.sl = 0.0
        self.tp = 0.0

    def on_bar(self):
        vwap_val = ta.vwap(self.hlc3)
        ph = self.security(None, "D", lambda v: v.high[1], lookahead=True)
        pl = self.security(None, "D", lambda v: v.low[1], lookahead=True)
        pc = self.security(None, "D", lambda v: v.close[1], lookahead=True)
        p = (ph + pl + pc) / 3
        r1 = (p * 2) - pl
        s1 = (p * 2) - ph
        r2 = p + (ph - pl)
        s2 = p - (ph - pl)
        r3 = ph + 2 * (p - pl)
        s3 = pl - 2 * (ph - p)
        rsi_val = ta.rsi(self.close, 14)
        stoch_k = ta.sma(ta.stoch(rsi_val, rsi_val, rsi_val, 14), 3)
        stoch_d = ta.sma(stoch_k, 3)
        in_session = not na(self.time_fn(None, self.session_input, self.tz_offset))
        c = self.close
        if self.only_central_pivot:
            pivot_cross_down = ta.crossunder(c, p)
            pivot_cross_up = ta.crossover(c, p)
        else:
            pivot_cross_down = (ta.crossunder(c, p) or ta.crossunder(c, r1) or ta.crossunder(c, r2) or ta.crossunder(c, r3)
                                or ta.crossunder(c, s1) or ta.crossunder(c, s2) or ta.crossunder(c, s3))
            pivot_cross_up = (ta.crossover(c, p) or ta.crossover(c, r1) or ta.crossover(c, r2) or ta.crossover(c, r3)
                              or ta.crossover(c, s1) or ta.crossover(c, s2) or ta.crossover(c, s3))
        stoch_cross_down = ta.crossunder(stoch_k, stoch_d)
        stoch_cross_up = ta.crossover(stoch_k, stoch_d)
        stoch_is_bearish = stoch_k < stoch_d
        stoch_is_bullish = stoch_k > stoch_d
        if self.efficiency_filter:
            sell_condition = in_session and self.close < vwap_val and stoch_is_bearish and pivot_cross_down
            buy_condition = in_session and self.close > vwap_val and stoch_is_bullish and pivot_cross_up
        else:
            sell_condition = in_session and self.close < vwap_val and stoch_cross_down and pivot_cross_down
            buy_condition = in_session and self.close > vwap_val and stoch_cross_up and pivot_cross_up
        st = self.strategy
        if sell_condition and st.position_size == 0:
            self.sl = float(self.high)
            risk = self.sl - self.close
            self.tp = self.close * 0.99 if self.profit_mode == "1% Price" else self.close - (risk * self.rr_ratio)
            st.entry("SELL", st.short)
            st.exit("Exit Short", "SELL", stop=self.sl, limit=self.tp)
        if buy_condition and st.position_size == 0:
            self.sl = float(self.low)
            risk = self.close - self.sl
            self.tp = self.close * 1.01 if self.profit_mode == "1% Price" else self.close + (risk * self.rr_ratio)
            st.entry("BUY", st.long)
            st.exit("Exit Long", "BUY", stop=self.sl, limit=self.tp)
        curr_time_minutes = self.hour(self.time, self.tz_offset) * 60 + self.minute(self.time, self.tz_offset)
        if curr_time_minutes >= 900:
            st.close_all(comment="EOD Exit at 15:00")
        self.plot(vwap_val, "VWAP", color=color.yellow, linewidth=2)
