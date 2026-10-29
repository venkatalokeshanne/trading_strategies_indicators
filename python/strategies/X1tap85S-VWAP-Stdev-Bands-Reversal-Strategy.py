"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Stdev Bands Reversal Strategy
Author       : EvilEddie
Source URL   : https://www.tradingview.com/script/X1tap85S-VWAP-Stdev-Bands-Reversal-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A daily-reset VWAP with standard-deviation bands arms a long (short) when the price tags the lower (upper) extreme band or closes beyond the second band; the next candle in the reversal direction that closes on the VWAP side where the move started fires the signal (a candle closing beyond the VWAP cancels it). A signal with the minimum reward:risk to the opposite second band reverses an open trade and places a resting limit entry at the signal close that expires after a few bars, with the swing stop and band target attached once filled; or a market entry with its exit at once.

Deviations from the original: none.
Not carried over: band plots and the previous-VWAP line (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class VwapStdevReversal(Script):
    TITLE = "VWAP Stdev Bands Reversal Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, process_orders_on_close=True, margin_long=1, margin_short=1,
                    commission_type="percent", commission_value=0.02, slippage=0)

    SOURCE = {"id": "X1tap85S", "author": "EvilEddie", "licence": "not stated",
              "url": "https://www.tradingview.com/script/X1tap85S-VWAP-Stdev-Bands-Reversal-Strategy"}

    def init(self):
        i = self.input
        self.dev_up1 = i.float(1.28, "Stdev above (1)")
        self.dev_dn1 = i.float(1.28, "Stdev below (1)")
        self.dev_up2 = i.float(2.01, "Stdev above (2)")
        self.dev_dn2 = i.float(2.01, "Stdev below (2)")
        self.dev_up3 = i.float(2.51, "Stdev above (3)")
        self.dev_dn3 = i.float(2.51, "Stdev below (3)")
        self.dev_up4 = i.float(3.09, "Stdev above (4)")
        self.dev_dn4 = i.float(3.09, "Stdev below (4)")
        self.dev_up5 = i.float(4.01, "Stdev above (5)")
        self.dev_dn5 = i.float(4.01, "Stdev below (5)")
        g = "Signals"
        self.extreme_band = i.int(3, "Most extreme band (1-5)", minval=1, maxval=5, group=g)
        self.second_band = i.int(2, "Second most extreme band (1-5)", minval=1, maxval=5, group=g)
        self.swing_len = i.int(5, "Swing lookback for stop (bars)", minval=1, group=g)
        self.arm_expiry = i.int(500, "Arm expiry (bars to wait for reversal)", minval=1, group=g)
        self.session_warmup = i.int(3, "Skip first N bars of session (VWAP warmup)", minval=0, group=g)
        self.session_cutoff = i.int(5, "Skip last N bars of session (end-of-day)", minval=0, group=g)
        g = "Strategy"
        self.min_rr = i.float(1.5, "Minimum Risk:Reward", minval=0, step=0.1, group=g)
        self.reverse_opp = i.bool(True, "Opposite signal closes/reverses trade", group=g)
        self.use_limit = i.bool(True, "Use resting limit entries (maker)", group=g)
        self.limit_expiry = i.int(3, "Limit order expiry (bars)", minval=1, group=g)
        self.risk_pct = i.float(1.0, "Risk per trade (% of equity)", minval=0.01, step=0.1, group=g)
        self.use_risk_size = i.bool(True, "Size by stop-loss risk (fixed-fractional)", group=g)
        self.max_leverage = i.float(5.0, "Max leverage (position notional / equity cap)", minval=0.1, step=0.5, group=g)
        self.vwapsum = NA
        self.volumesum = NA
        self.v2sum = NA
        self.bars_since_session = 0
        self.prev_session_len = NA
        self.running_len = 0
        self.arm_short = False
        self.arm_long = False
        self.short_age = 0
        self.long_age = 0
        self.long_limit_price = NA
        self.short_limit_price = NA
        self.long_order_age = NA
        self.short_order_age = NA
        self.long_stop_at_sig = NA
        self.short_stop_at_sig = NA
        self.long_tp_at_sig = NA
        self.short_tp_at_sig = NA

    def up_mult(self, n):
        return self.dev_up1 if n == 1 else self.dev_up2 if n == 2 else self.dev_up3 if n == 3 else self.dev_up4 if n == 4 else self.dev_up5

    def dn_mult(self, n):
        return self.dev_dn1 if n == 1 else self.dev_dn2 if n == 2 else self.dev_dn3 if n == 3 else self.dev_dn4 if n == 4 else self.dev_dn5

    def qty_for(self, entry_price, stop_price):
        st = self.strategy
        rpu = abs(entry_price - stop_price)
        eq = pmath.max(st.equity, 0)
        risk_qty = div(eq * self.risk_pct / 100, rpu) if (self.use_risk_size and rpu > 0 and eq > 0) else NA
        max_qty = div(eq * self.max_leverage, entry_price) if (entry_price > 0 and eq > 0) else NA
        if na(risk_qty):
            return NA
        return risk_qty if na(max_qty) else pmath.min(risk_qty, max_qty)

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        new_session = self.timeframe.change("D")
        hl2 = (high + low) / 2
        vol = self.volume
        self.vwapsum = hl2 * vol if new_session else nz(self.vwapsum) + hl2 * vol
        self.volumesum = float(vol) if new_session else nz(self.volumesum) + vol
        self.v2sum = vol * hl2 * hl2 if new_session else nz(self.v2sum) + vol * hl2 * hl2
        myvwap = div(self.vwapsum, self.volumesum)
        dev = pmath.sqrt(pmath.max(div(self.v2sum, self.volumesum) - myvwap * myvwap, 0))
        up_ext = myvwap + self.up_mult(self.extreme_band) * dev
        dn_ext = myvwap - self.dn_mult(self.extreme_band) * dev
        up2nd = myvwap + self.up_mult(self.second_band) * dev
        dn2nd = myvwap - self.dn_mult(self.second_band) * dev
        up_trigger0 = (high >= up_ext) or (close > up2nd)
        dn_trigger0 = (low <= dn_ext) or (close < dn2nd)
        self.bars_since_session = 0 if new_session else self.bars_since_session + 1
        warmup_ok = self.bars_since_session >= self.session_warmup
        if new_session:
            self.prev_session_len = self.running_len
            self.running_len = 0
        else:
            self.running_len += 1
        cutoff_ok = True if (na(self.prev_session_len) or self.session_cutoff == 0) else self.bars_since_session < (self.prev_session_len - self.session_cutoff)
        session_ok = warmup_ok and cutoff_ok
        up_trigger = up_trigger0 and session_ok
        dn_trigger = dn_trigger0 and session_ok
        if new_session:
            self.arm_short = False
            self.arm_long = False
            self.short_age = 0
            self.long_age = 0
        if self.arm_short:
            self.short_age += 1
            if self.short_age > self.arm_expiry:
                self.arm_short = False
        if self.arm_long:
            self.long_age += 1
            if self.long_age > self.arm_expiry:
                self.arm_long = False
        if up_trigger:
            self.arm_short = True
            self.short_age = 0
        if dn_trigger:
            self.arm_long = True
            self.long_age = 0
        bull_candle = close > open_
        bear_candle = close < open_
        long_signal = self.arm_long and bull_candle and close <= myvwap
        short_signal = self.arm_short and bear_candle and close >= myvwap
        long_cancel = self.arm_long and bull_candle and close > myvwap
        short_cancel = self.arm_short and bear_candle and close < myvwap
        if long_signal or long_cancel:
            self.arm_long = False
        if short_signal or short_cancel:
            self.arm_short = False
        long_stop = ta.lowest(low, self.swing_len)
        short_stop = ta.highest(high, self.swing_len)
        tp_long = up2nd
        tp_short = dn2nd
        long_risk = close - long_stop
        long_reward = tp_long - close
        long_rr = div(long_reward, long_risk) if long_risk > 0 else 0
        short_risk = short_stop - close
        short_reward = close - tp_short
        short_rr = div(short_reward, short_risk) if short_risk > 0 else 0
        long_ok = long_signal and long_rr >= self.min_rr
        short_ok = short_signal and short_rr >= self.min_rr
        flat = st.position_size == 0
        is_long = st.position_size > 0
        is_short = st.position_size < 0
        enter_long = long_ok and (flat or (self.reverse_opp and is_short))
        enter_short = short_ok and (flat or (self.reverse_opp and is_long))
        if enter_long:
            if is_short:
                st.close("Short")
            if self.use_limit:
                self.long_limit_price = float(close)
                self.long_stop_at_sig = long_stop
                self.long_tp_at_sig = tp_long
                self.long_order_age = 0
                q = self.qty_for(self.long_limit_price, self.long_stop_at_sig)
                if not na(q):
                    st.entry("Long", st.long, qty=q, limit=self.long_limit_price)
                else:
                    st.entry("Long", st.long, limit=self.long_limit_price)
            else:
                q = self.qty_for(close, long_stop)
                if not na(q):
                    st.entry("Long", st.long, qty=q)
                else:
                    st.entry("Long", st.long)
                st.exit("Long X", from_entry="Long", stop=long_stop, limit=tp_long)
        if enter_short:
            if is_long:
                st.close("Long")
            if self.use_limit:
                self.short_limit_price = float(close)
                self.short_stop_at_sig = short_stop
                self.short_tp_at_sig = tp_short
                self.short_order_age = 0
                q = self.qty_for(self.short_limit_price, self.short_stop_at_sig)
                if not na(q):
                    st.entry("Short", st.short, qty=q, limit=self.short_limit_price)
                else:
                    st.entry("Short", st.short, limit=self.short_limit_price)
            else:
                q = self.qty_for(close, short_stop)
                if not na(q):
                    st.entry("Short", st.short, qty=q)
                else:
                    st.entry("Short", st.short)
                st.exit("Short X", from_entry="Short", stop=short_stop, limit=tp_short)
        if self.use_limit:
            if (not na(self.long_order_age)) and st.position_size <= 0:
                self.long_order_age += 1
                if self.long_order_age > self.limit_expiry:
                    st.cancel("Long")
                    self.long_order_age = NA
            if is_long and not na(self.long_stop_at_sig):
                st.exit("Long X", from_entry="Long", stop=self.long_stop_at_sig, limit=self.long_tp_at_sig)
                self.long_stop_at_sig = NA
                self.long_order_age = NA
            if (not na(self.short_order_age)) and st.position_size >= 0:
                self.short_order_age += 1
                if self.short_order_age > self.limit_expiry:
                    st.cancel("Short")
                    self.short_order_age = NA
            if is_short and not na(self.short_stop_at_sig):
                st.exit("Short X", from_entry="Short", stop=self.short_stop_at_sig, limit=self.short_tp_at_sig)
                self.short_stop_at_sig = NA
                self.short_order_age = NA
