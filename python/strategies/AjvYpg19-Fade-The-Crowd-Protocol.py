"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fade The Crowd Protocol
Author       : BVLabs
Source URL   : https://www.tradingview.com/script/AjvYpg19-Fade-The-Crowd-Protocol
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A MACD / signal cross whose histogram sits on the "wrong" side of zero (a cross up with a positive histogram is faded as a short, a cross down as a long) while the bar touches
the VWMA, Choppiness is below its threshold and ADX is above its minimum, after a cooldown since the last exit, enters when flat. On the first script run with the position (the bar after the fill) the
take-profit (ATR% multiple of the fill price) and the tighter of the ATR% stop and the hard "plug" stop are computed from the fill price and the ATR% saved at the signal; the exit order is then re-issued every bar.

Deviations from the original: none.
Not carried over: the VWMA plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class FadeTheCrowd(Script):
    TITLE = "Fade The Crowd Protocol"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=50)
    SOURCE = {"id": "AjvYpg19", "author": "BVLabs", "licence": "not stated",
              "url": "https://www.tradingview.com/script/AjvYpg19-Fade-The-Crowd-Protocol"}

    def init(self):
        self.trade_dir = self.input.string("Both", "Allowed Directions", options=["Both", "Long Only", "Short Only"], group="Trade Direction")
        g = "Entry Filters"
        self.chop_len = self.input.int(7, "Choppiness Length", group=g)
        self.chop_thresh = self.input.float(100.0, "Choppiness Threshold (<)", group=g)
        self.adx_len = self.input.int(7, "ADX Length", group=g)
        self.adx_thresh = self.input.float(20.0, "ADX Threshold (>)", group=g)
        self.cooldown_bars = self.input.int(7, "Cooldown Timer (Bars)", group=g)
        g = "Indicator Settings"
        self.vwma_len = self.input.int(20, "VWMA Length", group=g)
        self.macd_fast = self.input.int(8, "MACD Fast", group=g)
        self.macd_slow = self.input.int(17, "MACD Slow", group=g)
        self.macd_sig = self.input.int(9, "MACD Signal", group=g)
        self.atr_len = self.input.int(7, "Fast ATR Length", group=g)
        g = "Exit Logic"
        self.tp_mult = self.input.float(3.0, "Take Profit Multiplier (1x ATR %)", group=g)
        self.sl_mult = self.input.float(2.0, "Stop Loss Multiplier (2x ATR %)", group=g)
        self.the_plug = self.input.float(1.3, "The Plug (Max Hard SL %)", group=g)
        self.last_exit_bar = NA
        self.sl_price = NA
        self.tp_price = NA
        self.stored_atr_pct = NA

    def on_bar(self):
        tr_sum = ta.msum(ta.tr(False), self.chop_len)
        high_range = ta.highest(self.high, self.chop_len)
        low_range = ta.lowest(self.low, self.chop_len)
        chop_val = div(100 * pmath.log10(div(tr_sum, high_range - low_range)), pmath.log10(self.chop_len))
        di_plus, di_minus, adx_val = ta.dmi(self.adx_len, self.adx_len)
        macd_line, sig_line, hist_line = ta.macd(self.close, self.macd_fast, self.macd_slow, self.macd_sig)
        vwma_val = ta.vwma(self.close, self.vwma_len)
        atr_val = ta.atr(self.atr_len)
        atr_pct = div(atr_val, self.close) * 100
        allow_long = self.trade_dir == "Both" or self.trade_dir == "Long Only"
        allow_short = self.trade_dir == "Both" or self.trade_dir == "Short Only"
        st = self.strategy
        pos_prev = self.H("pos")[1]
        self.H("pos").set(st.position_size)
        if st.position_size == 0 and (not na(pos_prev)) and pos_prev != 0:
            self.last_exit_bar = self.bar_index
        cooldown_ok = na(self.last_exit_bar) or self.bar_index - self.last_exit_bar >= self.cooldown_bars
        is_macd_cross = ta.cross(macd_line, sig_line)
        is_chop_valid = chop_val < self.chop_thresh
        is_adx_valid = adx_val > self.adx_thresh
        is_hist_below = hist_line < 0
        is_price_vwma_short = self.low <= vwma_val
        is_hist_above = hist_line > 0
        is_price_vwma_long = self.high >= vwma_val
        trigger_short = allow_short and is_macd_cross and is_hist_above and is_price_vwma_long and is_chop_valid and is_adx_valid and cooldown_ok and st.position_size == 0
        trigger_long = allow_long and is_macd_cross and is_hist_below and is_price_vwma_short and is_chop_valid and is_adx_valid and cooldown_ok and st.position_size == 0
        if trigger_short:
            self.stored_atr_pct = atr_pct
            st.entry("Short Entry", st.short)
        if trigger_long:
            self.stored_atr_pct = atr_pct
            st.entry("Long Entry", st.long)
        if st.position_size != 0:
            if pos_prev == 0 or na(pos_prev):
                fill_price = st.position_avg_price
                tp_dist_pct = self.stored_atr_pct * self.tp_mult / 100
                sl_dist_pct = self.stored_atr_pct * self.sl_mult / 100
                plug_dist_pct = self.the_plug / 100
                if st.position_size > 0:
                    self.tp_price = fill_price * (1 + tp_dist_pct)
                    self.sl_price = pmath.max(fill_price * (1 - sl_dist_pct), fill_price * (1 - plug_dist_pct))
                else:
                    self.tp_price = fill_price * (1 - tp_dist_pct)
                    self.sl_price = pmath.min(fill_price * (1 + sl_dist_pct), fill_price * (1 + plug_dist_pct))
            if st.position_size > 0:
                st.exit("Exit Order", "Long Entry", limit=self.tp_price, stop=self.sl_price, comment_profit="TP HIT", comment_loss="SL HIT")
            elif st.position_size < 0:
                st.exit("Exit Order", "Short Entry", limit=self.tp_price, stop=self.sl_price, comment_profit="TP HIT", comment_loss="SL HIT")
        self.plot(vwma_val, "VWMA 20", color=color.blue)
