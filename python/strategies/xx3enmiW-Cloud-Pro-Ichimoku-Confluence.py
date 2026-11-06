"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ichimoku Confluence Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/xx3enmiW-Cloud-Pro-Ichimoku-Confluence
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A Tenkan / Kijun cross is classed strong / neutral / weak by where the Tenkan sits against the cloud under the current bar
(senkou spans of displacement - 1 bars ago); the entry and exit tiers are selectable, an optional higher-timeframe Tenkan > Kijun filter (request.security, lookahead off) gates the entry,
the position is sized from the stop distance (risk-based, capped) or a fixed share of equity, and exits are an ATR bracket re-issued from the close each bar (or fixed % / none) plus the opposite signal.
Deviations from the original: none.
Not carried over: Ichimoku / cloud / twist plots, signal shapes, the background tint and the last-bar dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class IchimokuConfluence(Script):
    TITLE = "Ichimoku Confluence Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent",
                    commission_value=0.1, slippage=2)
    SOURCE = {"id": "xx3enmiW", "author": "not stated", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xx3enmiW-Cloud-Pro-Ichimoku-Confluence"}

    def init(self):
        i = self.input
        self.trading_mode = i.string("Long", "Direction", options=["Long", "Short", "Both"], group="Trading Mode")
        g = "Ichimoku Settings"
        self.tenkan_len = i.int(9, "Tenkan-sen", group=g)
        self.kijun_len = i.int(26, "Kijun-sen", group=g)
        self.senkou_len = i.int(52, "Senkou Span B", group=g)
        self.displacement = i.int(26, "Displacement", group=g)
        tiers = ["Strong Only", "Strong + Neutral", "All (incl. Weak)"]
        self.entry_long = i.string("Strong + Neutral", "Entry Tier (Bullish)", options=tiers, group="Long Signals")
        self.exit_long = i.string("All (incl. Weak)", "Exit Tier (Bearish)", options=tiers, group="Long Signals")
        self.entry_short = i.string("Strong + Neutral", "Entry Tier (Bearish)", options=tiers, group="Short Signals")
        self.exit_short = i.string("All (incl. Weak)", "Exit Tier (Bullish)", options=tiers, group="Short Signals")
        g = "Multi-Timeframe Filter"
        self.use_mtf = i.bool(True, "Require HTF trend agreement", group=g)
        self.htf = i.timeframe("D", "Higher Timeframe", group=g)
        g = "Risk Management"
        self.stop_mode = i.string("ATR", "Stop Mode", options=["Fixed %", "ATR", "None"], group=g)
        self.tp_pct = i.float(0, "Take Profit % (Fixed mode)", minval=0, step=0.1, group=g)
        self.sl_pct = i.float(0, "Stop Loss % (Fixed mode)", minval=0, step=0.1, group=g)
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_mult_sl = i.float(1.5, "ATR Stop Multiplier", group=g)
        self.atr_mult_tp = i.float(3.0, "ATR Target Multiplier", group=g)
        g = "Position Sizing"
        self.sizing_mode = i.string("Risk-Based (Stop Distance)", "Sizing Mode", options=["Fixed % of Equity", "Risk-Based (Stop Distance)"], group=g)
        self.risk_pct = i.float(1.0, "Risk per Trade (% of equity)", minval=0.1, step=0.1, group=g)
        self.equity_pct = i.float(10, "Equity Allocation % (Fixed mode)", minval=1, step=1, group=g)
        self.max_pos_pct = i.float(50, "Max Position Size (% of equity cap)", minval=1, group=g)
        self.use_cloud_scaling = i.bool(False, "Scale size by cloud thickness (confidence)", group=g)
        self.cloud_scale_min = i.float(0.5, "Min Scale Factor", minval=0.1, step=0.1, group=g)
        self.cloud_scale_max = i.float(1.5, "Max Scale Factor", minval=0.1, step=0.1, group=g)

    @staticmethod
    def donchian(hi, lo, ln):
        h = ta.highest(hi, ln)
        l = ta.lowest(lo, ln)
        return (h + l) / 2.0 if not (na(h) or na(l)) else NA

    @staticmethod
    def tier_match(tier, strong, neutral, weak):
        if tier == "Strong Only":
            return strong
        if tier == "Strong + Neutral":
            return strong or neutral
        return strong or neutral or weak

    def on_bar(self):
        st = self.strategy
        close = self.close
        tenkan = self.donchian(self.high, self.low, self.tenkan_len)
        kijun = self.donchian(self.high, self.low, self.kijun_len)
        senkou_a = (tenkan + kijun) / 2.0 if not (na(tenkan) or na(kijun)) else NA
        senkou_b = self.donchian(self.high, self.low, self.senkou_len)
        ha, hb = self.H("senkou_a"), self.H("senkou_b")
        cloud_now_a = ha[self.displacement - 1]
        cloud_now_b = hb[self.displacement - 1]
        ha.set(senkou_a)
        hb.set(senkou_b)
        if self.displacement == 1:
            cloud_now_a, cloud_now_b = senkou_a, senkou_b
        cloud_top = max(cloud_now_a, cloud_now_b) if not (na(cloud_now_a) or na(cloud_now_b)) else NA
        cloud_bot = min(cloud_now_a, cloud_now_b) if not (na(cloud_now_a) or na(cloud_now_b)) else NA
        htf_tenkan = self.security(None, self.htf, lambda v: self.donchian(v.high, v.low, self.tenkan_len), lookahead=False)
        htf_kijun = self.security(None, self.htf, lambda v: self.donchian(v.high, v.low, self.kijun_len), lookahead=False)
        htf_bullish = htf_tenkan > htf_kijun
        bull_cross = ta.crossover(tenkan, kijun)
        bear_cross = ta.crossunder(tenkan, kijun)
        cross_level = tenkan if (bull_cross or bear_cross) else NA
        strong_bull = bull_cross and cross_level > cloud_top
        neutral_bull = bull_cross and cross_level <= cloud_top and cross_level >= cloud_bot
        weak_bull = bull_cross and cross_level < cloud_bot
        strong_bear = bear_cross and cross_level < cloud_bot
        neutral_bear = bear_cross and cross_level <= cloud_top and cross_level >= cloud_bot
        weak_bear = bear_cross and cross_level > cloud_top
        long_entry_sig = self.tier_match(self.entry_long, strong_bull, neutral_bull, weak_bull)
        long_exit_sig = self.tier_match(self.exit_long, strong_bear, neutral_bear, weak_bear)
        short_entry_sig = self.tier_match(self.entry_short, strong_bear, neutral_bear, weak_bear)
        short_exit_sig = self.tier_match(self.exit_short, strong_bull, neutral_bull, weak_bull)
        mtf_ok_long = (not self.use_mtf) or htf_bullish
        mtf_ok_short = (not self.use_mtf) or (not htf_bullish)
        allow_long = self.trading_mode in ("Long", "Both")
        allow_short = self.trading_mode in ("Short", "Both")
        atr_val = ta.atr(self.atr_len)
        equity = st.equity
        stop_dist = close * self.sl_pct / 100 if (self.stop_mode == "Fixed %" and self.sl_pct > 0) else atr_val * self.atr_mult_sl
        risk_amount = equity * self.risk_pct / 100
        qty_risk = div(risk_amount, stop_dist) if stop_dist > 0 else NA
        qty_fixed = div(equity * self.equity_pct / 100, close)
        qty_cap = div(equity * self.max_pos_pct / 100, close)
        thick = div(abs(cloud_now_a - cloud_now_b), atr_val) if atr_val > 0 else 1.0
        scale = max(self.cloud_scale_min, min(self.cloud_scale_max, thick)) if self.use_cloud_scaling else 1.0
        qty_raw = qty_risk if self.sizing_mode == "Risk-Based (Stop Distance)" else qty_fixed
        qty_final = NA if na(qty_raw) else min(qty_raw * scale, qty_cap)
        pos = st.position_size
        if allow_long and long_entry_sig and mtf_ok_long and pos <= 0 and not na(qty_final) and qty_final > 0:
            st.entry("Long", st.long, qty=qty_final)
        if allow_short and short_entry_sig and mtf_ok_short and pos >= 0 and not na(qty_final) and qty_final > 0:
            st.entry("Short", st.short, qty=qty_final)
        if pos > 0:
            if self.stop_mode == "ATR":
                st.exit("L Exit", "Long", stop=close - atr_val * self.atr_mult_sl, limit=close + atr_val * self.atr_mult_tp)
            elif self.stop_mode == "Fixed %":
                sl_level = st.position_avg_price * (1 - self.sl_pct / 100) if self.sl_pct > 0 else NA
                tp_level = st.position_avg_price * (1 + self.tp_pct / 100) if self.tp_pct > 0 else NA
                st.exit("L Exit", "Long", stop=sl_level, limit=tp_level)
            if long_exit_sig:
                st.close("Long", comment="Signal Exit")
        if pos < 0:
            if self.stop_mode == "ATR":
                st.exit("S Exit", "Short", stop=close + atr_val * self.atr_mult_sl, limit=close - atr_val * self.atr_mult_tp)
            elif self.stop_mode == "Fixed %":
                sl_level = st.position_avg_price * (1 + self.sl_pct / 100) if self.sl_pct > 0 else NA
                tp_level = st.position_avg_price * (1 - self.tp_pct / 100) if self.tp_pct > 0 else NA
                st.exit("S Exit", "Short", stop=sl_level, limit=tp_level)
            if short_exit_sig:
                st.close("Short", comment="Signal Exit")
