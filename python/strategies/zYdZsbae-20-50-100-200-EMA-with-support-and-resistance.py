"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA and SR (20,50,100, 200 EMA with support and resistance)
Author       : ankurb171991
Source URL   : https://www.tradingview.com/script/zYdZsbae-20-50-100-200-EMA-with-support-and-resistance
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close above (below) all four EMAs that also breaks the previous bar's high (low) opens a long "Buy CE" (short
"Buy PE") with the previous bar's extreme as stop and an R:R target, once per day per side. NOTE the original's quirk, kept as written: the "if not ce_is_open" reset runs
on the entry bar, when the new trade is not yet counted as open, so the stop / target are cleared immediately; on later bars the exit block is skipped because they are na.
The trade therefore never gets an exit order and stays open (and blocks every other entry) for the rest of the history.

Deviations from the original: none.
Not carried over: the EMA, support / resistance plots and entry arrows (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class EmaAndSRzYdZsbae(Script):
    TITLE = "EMA and SR"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=100000, process_orders_on_close=True)
    SOURCE = {"id": "zYdZsbae", "author": "ankurb171991", "licence": "not stated",
              "url": "https://www.tradingview.com/script/zYdZsbae-20-50-100-200-EMA-with-support-and-resistance"}

    def init(self):
        self.rr_multiplier = self.input.float(3.0, "Risk Reward Ratio")
        self.show_dynamic_sr = self.input.bool(True, "Show Support/Resistance")
        self.swing_lookback = self.input.int(20, "Swing Detection Bars")
        self.one_trade_per_day = self.input.bool(True, "One Trade Per Day Per Type (CE/PE)?")
        self.use_trailing_sl = self.input.bool(False, "Use Trailing Stop Loss?")
        self.trailing_activation = self.input.float(1.0, "Trailing Activation % (profit before trailing starts)", minval=0.5, step=0.1)
        self.trailing_distance = self.input.float(0.5, "Trailing Distance % (distance from peak)", minval=0.1, step=0.1)
        self.last_traded_day = NA
        self.ce_traded_today = False
        self.pe_traded_today = False
        self.ce_sl = NA
        self.ce_target = NA
        self.pe_sl = NA
        self.pe_target = NA
        self.resistance_level = NA
        self.support_level = NA

    def on_bar(self):
        ema20 = ta.ema(self.close, 20)
        ema50 = ta.ema(self.close, 50)
        ema100 = ta.ema(self.close, 100)
        ema200 = ta.ema(self.close, 200)
        self.plot(ema20, "EMA 20", color=color.yellow, linewidth=2)
        self.plot(ema50, "EMA 50", color=color.blue, linewidth=2)
        self.plot(ema100, "EMA 100", color=color.white, linewidth=2)
        self.plot(ema200, "EMA 200", color=color.green, linewidth=2)
        st = self.strategy
        dom = self.dayofmonth()
        is_new_day = na(self.last_traded_day) or dom != self.last_traded_day
        if is_new_day:
            self.last_traded_day = dom
            self.ce_traded_today = False
            self.pe_traded_today = False
        ce_is_open = False
        pe_is_open = False
        for i in range(st.opentrades):
            if st.opentrades_entry_id(i) == "Buy CE":
                ce_is_open = True
            if st.opentrades_entry_id(i) == "Buy PE":
                pe_is_open = True
        prev_high = self.high[1]
        prev_low = self.low[1]
        prev_close = self.close[1]
        prev_valid = (not na(prev_high)) and (not na(prev_low)) and (not na(prev_close))
        emas_valid = (not na(ema20)) and (not na(ema50)) and (not na(ema100)) and (not na(ema200))
        ce_ema_filter = emas_valid and self.close > ema20 and self.close > ema50 and self.close > ema100 and self.close > ema200
        ce_breakout = prev_valid and self.close > prev_high
        pe_ema_filter = emas_valid and self.close < ema20 and self.close < ema50 and self.close < ema100 and self.close < ema200
        pe_breakdown = prev_valid and self.close < prev_low
        ce_can_trade = (not self.one_trade_per_day) or not self.ce_traded_today
        ce_entry = ce_ema_filter and ce_breakout and ce_can_trade and not ce_is_open and not pe_is_open
        if ce_entry:
            risk = self.close - prev_low
            if risk > 0:
                self.ce_sl = prev_low
                self.ce_target = self.close + self.rr_multiplier * risk
                st.entry("Buy CE", st.long, comment="CE Entry")
                self.ce_traded_today = True
        if ce_is_open and not na(self.ce_sl) and not na(self.ce_target):
            effective_sl = pmath.min(self.ce_sl, self.low) if (self.close < ema20 or self.close < ema50) else self.ce_sl
            if self.use_trailing_sl:
                act_price = st.opentrades_entry_price(0) * (1 + self.trailing_activation / 100)
                st.exit("Exit CE", from_entry="Buy CE", stop=effective_sl, limit=self.ce_target, trail_price=act_price,
                        trail_offset=self.trailing_distance, comment="exit")
            else:
                st.exit("Exit CE", from_entry="Buy CE", stop=effective_sl, limit=self.ce_target, comment="exit")
        if not ce_is_open:
            self.ce_sl = NA
            self.ce_target = NA
        pe_can_trade = (not self.one_trade_per_day) or not self.pe_traded_today
        pe_entry = pe_ema_filter and pe_breakdown and pe_can_trade and not pe_is_open and not ce_is_open
        if pe_entry:
            risk = prev_high - self.close
            if risk > 0:
                self.pe_sl = prev_high
                self.pe_target = self.close - self.rr_multiplier * risk
                st.entry("Buy PE", st.short, comment="PE Entry")
                self.pe_traded_today = True
        if pe_is_open and not na(self.pe_sl) and not na(self.pe_target):
            effective_sl = pmath.max(self.pe_sl, self.high) if (self.close > ema20 or self.close > ema50) else self.pe_sl
            if self.use_trailing_sl:
                act_price = st.opentrades_entry_price(0) * (1 - self.trailing_activation / 100)
                st.exit("Exit PE", from_entry="Buy PE", stop=effective_sl, limit=self.pe_target, trail_price=act_price,
                        trail_offset=self.trailing_distance, comment="exit")
            else:
                st.exit("Exit PE", from_entry="Buy PE", stop=effective_sl, limit=self.pe_target, comment="exit")
        if not pe_is_open:
            self.pe_sl = NA
            self.pe_target = NA
        swing_high = ta.pivothigh(self.high, self.swing_lookback, self.swing_lookback)
        swing_low = ta.pivotlow(self.low, self.swing_lookback, self.swing_lookback)
        if not na(swing_high):
            self.resistance_level = swing_high
        if not na(swing_low):
            self.support_level = swing_low
        self.plot(self.resistance_level if self.show_dynamic_sr else NA, "Resistance", color=color.orange)
        self.plot(self.support_level if self.show_dynamic_sr else NA, "Support", color=color.blue)
