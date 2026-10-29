"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Stock Breakout Momentum Strategy
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/n7sVlEUq-Stock-Breakout-Momentum-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close above the previous bar's 20-bar highest high (or below the lowest low), with the SMA50 trend and a volume filter, enters flat with
a stop an ATR multiple from the signal bar's OPEN and a profit target from the same open. While in the position the stop only ratchets toward the close (max / min with
close -/+ ATR multiple); after 20 bars a market close replaces the bracket order. The risk-percent sizing floors equity / close shares.

Deviations from the original: none.
Not carried over: the channel, stop, target and SMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, nz, pmath, ta


class StockBreakoutMomentum(Script):
    TITLE = "Stock Breakout Momentum Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05,
                    slippage=2, pyramiding=0, process_orders_on_close=False)
    SOURCE = {"id": "n7sVlEUq", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/n7sVlEUq-Stock-Breakout-Momentum-Strategy"}

    def init(self):
        self.breakout_length = self.input.int(20, "Breakout Lookback (bars)", minval=1)
        self.bars_in_trade = self.input.int(20, "Time-Based Exit (bars)", minval=1)
        self.atr_length = self.input.int(14, "ATR Length", minval=1)
        self.atr_multiplier = self.input.float(2.0, "ATR Trailing Stop Multiplier", minval=0.1)
        self.account_risk_pct = self.input.float(100.0, "Percent of Equity to Allocate per Trade (%)", minval=1.0, maxval=500.0)
        self.allow_short = self.input.bool(True, "Allow Short Entries")
        g = "Profit Target"
        self.use_profit_target = self.input.bool(True, "Use Profit Target", group=g)
        self.profit_target_atr_mult = self.input.float(3.0, "Profit Target ATR Multiplier", group=g)
        g = "Filters"
        self.use_trend_filter = self.input.bool(True, "Use Trend Filter", group=g)
        self.trend_length = self.input.int(50, "Trend SMA Length", group=g)
        self.use_volume_filter = self.input.bool(True, "Use Volume Filter", group=g)
        self.vol_length = self.input.int(20, "Volume SMA Length", group=g)
        self.volume_multiplier = self.input.float(1.2, "Volume Multiplier", group=g)
        self.long_sl = NA
        self.short_sl = NA
        self.long_tp = NA
        self.short_tp = NA
        self.entry_bar_index = NA
        self.just_entered = False

    def on_bar(self):
        highest_high = ta.highest(self.high, self.breakout_length)
        lowest_low = ta.lowest(self.low, self.breakout_length)
        hh1 = self.H("hh")[1]
        ll1 = self.H("ll")[1]
        self.H("hh").set(highest_high)
        self.H("ll").set(lowest_low)
        atr_value = ta.atr(self.atr_length)
        trend_sma = ta.sma(self.close, self.trend_length)
        vol_sma = ta.sma(self.volume, self.vol_length)
        data_ready = (not na(hh1)) and (not na(ll1)) and (not na(atr_value)) and ((not self.use_trend_filter) or not na(trend_sma)) \
            and ((not self.use_volume_filter) or not na(vol_sma))
        trend_ok_long = (not self.use_trend_filter) or self.close > trend_sma
        trend_ok_short = (not self.use_trend_filter) or self.close < trend_sma
        vol_ok = (not self.use_volume_filter) or self.volume > vol_sma * self.volume_multiplier
        long_breakout = data_ready and self.barstate.isconfirmed and self.close > hh1 and trend_ok_long and vol_ok
        short_breakout = self.allow_short and data_ready and self.barstate.isconfirmed and self.close < ll1 and trend_ok_short and vol_ok
        st = self.strategy
        available_equity = st.equity * (self.account_risk_pct / 100.0)
        shares = pmath.max(1, pmath.floor(div(available_equity, self.close))) if self.close > 0 else 1
        if long_breakout and st.position_size == 0:
            self.just_entered = True
            self.entry_bar_index = self.bar_index
            self.long_sl = self.open - atr_value * self.atr_multiplier
            self.long_tp = self.open + atr_value * self.profit_target_atr_mult if self.use_profit_target else NA
            st.entry("Long", st.long, qty=shares)
        if short_breakout and st.position_size == 0:
            self.just_entered = True
            self.entry_bar_index = self.bar_index
            self.short_sl = self.open + atr_value * self.atr_multiplier
            self.short_tp = self.open - atr_value * self.profit_target_atr_mult if self.use_profit_target else NA
            st.entry("Short", st.short, qty=shares)
        if st.position_size > 0:
            self.long_sl = pmath.max(nz(self.long_sl, self.open), self.close - atr_value * self.atr_multiplier)
        if st.position_size < 0:
            self.short_sl = pmath.min(nz(self.short_sl, self.open), self.close + atr_value * self.atr_multiplier)
        held = (not na(self.entry_bar_index)) and (self.bar_index - self.entry_bar_index) >= self.bars_in_trade
        time_exit_long = st.position_size > 0 and held
        time_exit_short = st.position_size < 0 and held
        if st.position_size > 0:
            if time_exit_long:
                st.close("Long", comment="Time Exit")
            else:
                st.exit("Trail Exit Long", "Long", stop=self.long_sl, limit=self.long_tp)
        if st.position_size < 0:
            if time_exit_short:
                st.close("Short", comment="Time Exit")
            else:
                st.exit("Trail Exit Short", "Short", stop=self.short_sl, limit=self.short_tp)
        if st.position_size == 0 and not self.just_entered:
            self.long_sl = NA
            self.short_sl = NA
            self.long_tp = NA
            self.short_tp = NA
            self.entry_bar_index = NA
        self.just_entered = False
        self.plot(highest_high, "20-Bar Highest High", color=color.green)
        self.plot(lowest_low, "20-Bar Lowest Low", color=color.red)
        self.plot(trend_sma, "Trend SMA", color=color.yellow)
