"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Shihan's Pure PA + Vol + POC (V18.2)
Author       : SENMS141319
Source URL   : https://www.tradingview.com/script/RIv7js9Y-Shihan-s-Pure-PA-Vol-POC-V18-2
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The previous candle is classified as a hammer (long lower wick, small upper wick), a shooting star, or a balanced "micro POC" doji with wicks on
both sides; with above-average previous volume and the current close confirming (above the previous close, or beyond the previous range for the POC doji) a long / short is entered
with the previous extreme (plus 5 ticks) as stop and a 1.5R target, both re-issued on every signal bar (also when the side is already open). The Asia / Europe / US
session volume-weighted "POC" lines in the original are plots only and never feed an order, so they are not carried over.

Deviations from the original: none for trading.
Not carried over: the session POC plots, BUY / SELL labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, pmath, ta


class ShihanPurePA(Script):
    TITLE = "Shihan's Pure PA + Vol + POC (V18.2)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=5000, default_qty_type="percent_of_equity", default_qty_value=10, margin_long=5, margin_short=5)
    SOURCE = {"id": "RIv7js9Y", "author": "SENMS141319", "licence": "not stated",
              "url": "https://www.tradingview.com/script/RIv7js9Y-Shihan-s-Pure-PA-Vol-POC-V18-2"}

    def init(self):
        g = "--- 1. Core Trading Mode Selection ---"
        self.trade_mode = self.input.string("3. PA + POC (Dual Mode)", "Select Mode",
                                            options=["1. PA Mode (Hammer/Star)", "2. POC Mode (Doji Balance)", "3. PA + POC (Dual Mode)"], group=g)
        g = "--- 2. Pattern Anatomy & Hyperparameters ---"
        self.vol_mult = self.input.float(1.1, "Volume Threshold (volMult)", step=0.1, group=g)
        self.ham_wick_ratio = self.input.float(2.0, "Hammer: Min Lower Wick/Body Ratio", step=0.1, group=g)
        self.ham_head_ratio = self.input.float(1.2, "Hammer: Max Upper Wick/Body Ratio", step=0.1, group=g)
        self.star_wick_ratio = self.input.float(2.0, "Star: Min Upper Wick/Body Ratio", step=0.1, group=g)
        self.star_head_ratio = self.input.float(1.2, "Star: Max Lower Wick/Body Ratio", step=0.1, group=g)
        self.poc_wick_ratio = self.input.float(1.5, "Micro POC: Min Wick/Body Ratio", step=0.1, group=g)
        self.poc_sym_ratio = self.input.float(0.6, "Micro POC: Symmetry Requirement (0.1-1.0)", step=0.1, group=g)
        self.min_rr_filter = self.input.float(1.2, "Minimum Risk/Reward Filter (RR)", step=0.1, group=g)

    def on_bar(self):
        enable_pa = self.trade_mode in ("1. PA Mode (Hammer/Star)", "3. PA + POC (Dual Mode)")
        enable_poc = self.trade_mode in ("2. POC Mode (Doji Balance)", "3. PA + POC (Dual Mode)")
        p_open, p_close, p_high, p_low, p_vol = self.open[1], self.close[1], self.high[1], self.low[1], self.volume[1]
        p_body = pmath.abs(p_close - p_open)
        p_upper = p_high - pmath.max(p_open, p_close)
        p_lower = pmath.min(p_open, p_close) - p_low if p_low < pmath.min(p_open, p_close) else 0
        vol_sma = ta.sma(self.volume, 50)
        vol_base = self.H("vol_sma")[1]
        self.H("vol_sma").set(vol_sma)
        is_hammer = (p_lower >= p_body * self.ham_wick_ratio) and (p_upper <= p_body * self.ham_head_ratio) and (p_body > 0)
        is_star = (p_upper >= p_body * self.star_wick_ratio) and (p_lower <= p_body * self.star_head_ratio) and (p_body > 0)
        symmetry = div(pmath.min(p_upper, p_lower), pmath.max(p_upper, p_lower, 0.0001))
        is_poc = (p_upper >= p_body * self.poc_wick_ratio) and (p_lower >= p_body * self.poc_wick_ratio) and (symmetry >= self.poc_sym_ratio) and (p_body > 0)
        pa_buy = enable_pa and is_hammer and (self.close > p_close) and (p_vol > vol_base * self.vol_mult)
        pa_sell = enable_pa and is_star and (self.close < p_close) and (p_vol > vol_base * self.vol_mult)
        poc_buy = enable_poc and is_poc and (p_vol > vol_base * self.vol_mult) and (self.close > p_high)
        poc_sell = enable_poc and is_poc and (p_vol > vol_base * self.vol_mult) and (self.close < p_low)
        valid_buy = pa_buy or poc_buy
        valid_sell = pa_sell or poc_sell
        st = self.strategy
        tick = self.syminfo.mintick
        if valid_buy:
            sl = p_low - 5 * tick
            tp = self.close + (self.close - sl) * 1.5
            if div(tp - self.close, self.close - sl) >= self.min_rr_filter:
                st.entry("Long", st.long)
                st.exit("ExL", "Long", limit=tp, stop=sl)
        if valid_sell:
            sl = p_high + 5 * tick
            tp = self.close - (sl - self.close) * 1.5
            if div(self.close - tp, sl - self.close) >= self.min_rr_filter:
                st.entry("Short", st.short)
                st.exit("ExS", "Short", limit=tp, stop=sl)
