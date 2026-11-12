"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AGNI MOMENTUM - Ultimate Swing Strategy
Author       : The_Stock_Yogi
Source URL   : https://www.tradingview.com/script/yp4CqVVY-AGNI-MOMENTUM-Ultimate-Swing-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A Stoch-RSI K/D cross on the right side of the daily VWAP, inside the IST entry window,
enters when flat; the stop (ATR multiple) and target (risk x reward) are fixed at the signal close, the stop then trails
to the previous bar's low (long) / high (short) while a position is open. The exit orders are only issued while a
position exists (so they first work one bar after the fill) and everything is closed once the IST clock reaches 15:29.

Deviations from the original: none.
Not carried over: the cosmetic target/stop lines and VWAP plot.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class AgniMomentum(Script):
    TITLE = "AGNI MOMENTUM - Ultimate Swing Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "yp4CqVVY", "author": "The_Stock_Yogi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/yp4CqVVY-AGNI-MOMENTUM-Ultimate-Swing-Strategy"}

    def init(self):
        self.enable_buy = self.input.bool(True, "Allow BUY Trades?", group="Trade Direction")
        self.enable_sell = self.input.bool(False, "Allow SELL Trades?", group="Trade Direction")
        self.tz_offset = self.input.string("GMT+530", "Timezone Offset (IST)", group="Session")
        self.entry_session = self.input.session("0015-0000", "Entry Window", group="Session")
        self.exit_time = self.input.int(1529, "Forced Exit Time (HHMM)", group="Session")
        self.rr_ratio = self.input.float(3.0, "Risk/Reward Ratio", minval=1.0, group="Risk")
        self.atr_multiplier = self.input.float(1.5, "ATR SL Multiplier", group="Risk")
        self.use_trailing = self.input.bool(True, "Enable Trailing Stop?", group="Risk")
        self.stoch_len = self.input.int(14, "Stoch RSI Length", group="Indicators")
        self.smooth_k = self.input.int(3, "K Smoothing", group="Indicators")
        self.smooth_d = self.input.int(3, "D Smoothing", group="Indicators")
        self.entry_sl = NA
        self.entry_tp = NA

    def on_bar(self):
        vwap_val = ta.vwap(self.hlc3)
        rsi_val = ta.rsi(self.close, self.stoch_len)
        stoch_k = ta.sma(ta.stoch(rsi_val, rsi_val, rsi_val, self.stoch_len), self.smooth_k)
        stoch_d = ta.sma(stoch_k, self.smooth_d)
        atr_val = ta.atr(14)
        in_session = not na(self.time_fn(None, self.entry_session, self.tz_offset))
        curr_time = self.hour(self.time, self.tz_offset) * 100 + self.minute(self.time, self.tz_offset)
        cross_up = ta.crossover(stoch_k, stoch_d)
        cross_dn = ta.crossunder(stoch_k, stoch_d)
        long_trigger = cross_up and self.close > vwap_val and in_session and self.enable_buy
        short_trigger = cross_dn and self.close < vwap_val and in_session and self.enable_sell
        st = self.strategy
        if long_trigger and st.position_size == 0:
            self.entry_sl = self.close - (atr_val * self.atr_multiplier)
            risk = self.close - self.entry_sl
            self.entry_tp = self.close + (risk * self.rr_ratio)
            st.entry("Long", st.long, comment="Sentinel BUY")
        if short_trigger and st.position_size == 0:
            self.entry_sl = self.close + (atr_val * self.atr_multiplier)
            risk = self.entry_sl - self.close
            self.entry_tp = self.close - (risk * self.rr_ratio)
            st.entry("Short", st.short, comment="Sentinel SELL")
        low, high = S(self.low), S(self.high)
        if self.use_trailing and st.position_size > 0:
            self.entry_sl = pmath.max(self.entry_sl, low[1])
        if self.use_trailing and st.position_size < 0:
            self.entry_sl = pmath.min(self.entry_sl, high[1])
        if st.position_size > 0:
            st.exit("L Exit", "Long", stop=self.entry_sl, limit=self.entry_tp, comment_loss="SL/Trail", comment_profit="TP")
        if st.position_size < 0:
            st.exit("S Exit", "Short", stop=self.entry_sl, limit=self.entry_tp, comment_loss="SL/Trail", comment_profit="TP")
        if curr_time >= self.exit_time:
            st.close_all("EOD Exit")
        self.plot(self.entry_tp if st.position_size != 0 else NA, "Target Line", color=color.lime, linewidth=4)
        self.plot(self.entry_sl if st.position_size != 0 else NA, "Stop/Trail Line", color=color.red, linewidth=4)
