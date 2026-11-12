"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : FVG BOS 50-62 Entry Bot
Author       : barash_ferad
Source URL   : https://www.tradingview.com/script/mpawgWIA-FVG-BOS-50-62-Entry-Bot
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A three-candle fair value gap whose middle body is a displacement (> ATR multiple) and whose size exceeds an ATR fraction, formed together with a break of the latest swing
(pivot) high / low, becomes the active zone. The first bar that retraces into the 50 % / 62 % level while closing inside the zone enters at the next open with the stop below / above the zone and the target at the
configured reward / risk, both computed from the trigger level and placed together with the entry. The zone is consumed by the trade or invalidated by a close beyond it.

Deviations from the original: none.
Not carried over: the zone boxes and labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class FvgBosEntryBot(Script):
    TITLE = "FVG BOS 50-62 Entry Bot"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="percent", commission_value=0.02)
    SOURCE = {"id": "mpawgWIA", "author": "barash_ferad", "licence": "not stated",
              "url": "https://www.tradingview.com/script/mpawgWIA-FVG-BOS-50-62-Entry-Bot"}

    def init(self):
        self.swing_len = self.input.int(5, "Swing length", minval=1)
        self.atr_len = self.input.int(14, "ATR length", minval=1)
        self.disp_atr_mult = self.input.float(0.8, "Min displacement body (x ATR)", step=0.1)
        self.min_gap_atr_mult = self.input.float(0.15, "Min FVG size (x ATR)", step=0.01)
        self.sl_buffer_ticks = self.input.int(2, "SL buffer (ticks)", minval=0)
        self.rr_target = self.input.float(2.0, "Risk:Reward target", step=0.1)
        self.entry_mode = self.input.string("62%", "Entry trigger level", options=["50%", "62%"])
        self.use_close_for_bos = self.input.bool(True, "Use close for BOS (otherwise wick)")
        self.one_trade_at_a_time = self.input.bool(True, "Only 1 open trade at a time")
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.active_bull_top = NA
        self.active_bull_bottom = NA
        self.active_bear_top = NA
        self.active_bear_bottom = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        atr = ta.atr(self.atr_len)
        tick = self.syminfo.mintick
        ph = ta.pivothigh(high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_swing_high = ph
        if not na(pl):
            self.last_swing_low = pl
        bull_bos = (not na(self.last_swing_high)) and (close > self.last_swing_high if self.use_close_for_bos else high > self.last_swing_high)
        bear_bos = (not na(self.last_swing_low)) and (close < self.last_swing_low if self.use_close_for_bos else low < self.last_swing_low)
        mid_body = abs(close[1] - open_[1])
        bull_gap_top = float(low)
        bull_gap_bottom = high[2]
        bull_gap_size = bull_gap_top - bull_gap_bottom
        bear_gap_top = low[2]
        bear_gap_bottom = float(high)
        bear_gap_size = bear_gap_top - bear_gap_bottom
        bull_fvg = self.bar_index >= 2 and low > high[2]
        bear_fvg = self.bar_index >= 2 and high < low[2]
        bull_displacement_ok = mid_body > atr * self.disp_atr_mult
        bear_displacement_ok = mid_body > atr * self.disp_atr_mult
        bull_gap_ok = bull_gap_size > atr * self.min_gap_atr_mult
        bear_gap_ok = bear_gap_size > atr * self.min_gap_atr_mult
        valid_bull_now = bull_fvg and bull_displacement_ok and bull_gap_ok and bull_bos
        valid_bear_now = bear_fvg and bear_displacement_ok and bear_gap_ok and bear_bos
        if valid_bull_now:
            self.active_bull_top = bull_gap_top
            self.active_bull_bottom = bull_gap_bottom
        if valid_bear_now:
            self.active_bear_top = bear_gap_top
            self.active_bear_bottom = bear_gap_bottom
        abt, abb = self.active_bull_top, self.active_bull_bottom
        bt, bb = self.active_bear_top, self.active_bear_bottom
        bull50 = NA if (na(abt) or na(abb)) else abt - (abt - abb) * 0.50
        bull62 = NA if (na(abt) or na(abb)) else abt - (abt - abb) * 0.62
        bear50 = NA if (na(bt) or na(bb)) else bb + (bt - bb) * 0.50
        bear62 = NA if (na(bt) or na(bb)) else bb + (bt - bb) * 0.62
        bull_trigger_level = bull50 if self.entry_mode == "50%" else bull62
        bear_trigger_level = bear50 if self.entry_mode == "50%" else bear62
        bull_invalid = (not na(self.active_bull_bottom)) and close < self.active_bull_bottom
        bear_invalid = (not na(self.active_bear_top)) and close > self.active_bear_top
        if bull_invalid:
            self.active_bull_top = NA
            self.active_bull_bottom = NA
        if bear_invalid:
            self.active_bear_top = NA
            self.active_bear_bottom = NA
        flat_or_allowed = st.position_size == 0 if self.one_trade_at_a_time else True
        long_touch = (not na(self.active_bull_top)) and (not na(bull_trigger_level)) and low <= bull_trigger_level and close >= self.active_bull_bottom
        short_touch = (not na(self.active_bear_bottom)) and (not na(bear_trigger_level)) and high >= bear_trigger_level and close <= self.active_bear_top
        long_sl = NA if na(self.active_bull_bottom) else self.active_bull_bottom - self.sl_buffer_ticks * tick
        short_sl = NA if na(self.active_bear_top) else self.active_bear_top + self.sl_buffer_ticks * tick
        long_entry_price = bull_trigger_level
        short_entry_price = bear_trigger_level
        long_risk = NA if (na(long_sl) or na(long_entry_price)) else long_entry_price - long_sl
        short_risk = NA if (na(short_sl) or na(short_entry_price)) else short_sl - short_entry_price
        long_tp = NA if na(long_risk) else long_entry_price + long_risk * self.rr_target
        short_tp = NA if na(short_risk) else short_entry_price - short_risk * self.rr_target
        valid_long_trade = flat_or_allowed and long_touch and (not na(long_risk)) and long_risk > 0
        valid_short_trade = flat_or_allowed and short_touch and (not na(short_risk)) and short_risk > 0
        if valid_long_trade:
            st.entry("Long", st.long)
            st.exit("Long TP/SL", from_entry="Long", stop=long_sl, limit=long_tp)
            self.active_bull_top = NA
            self.active_bull_bottom = NA
        if valid_short_trade:
            st.entry("Short", st.short)
            st.exit("Short TP/SL", from_entry="Short", stop=short_sl, limit=short_tp)
            self.active_bear_top = NA
            self.active_bear_bottom = NA
