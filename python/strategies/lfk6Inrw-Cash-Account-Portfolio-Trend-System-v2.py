"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Cash Account Portfolio Trend System v2
Author       : junseok_bong
Source URL   : https://www.tradingview.com/script/lfk6Inrw-Cash-Account-Portfolio-Trend-System-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Long-only trend system for a cash account: the close must be above a rising regime MA, a MACD histogram zero-cross (breakout) and / or an RSI pullback recovery triggers the entry (with an optional volume and RSI-overbought veto) once the settlement and cool-down bars after the previous sale have passed. The position is closed (at the next open) after the minimum holding period when the close falls below the ATR trailing stop (highest high since entry minus a multiple of the ATR), the catastrophic stop, the trend-break MA or the regime MA, or on RSI weakness. The order size is the per-slot share of the equity.

Deviations from the original: none.
Not carried over: the wrong-asset warning, MA / stop / regime plots, the momentum quality score, the in-market statistics and the stats panel (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class CashAccountPortfolioTrend(Script):
    TITLE = "Cash Account Portfolio Trend System v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=4500, default_qty_type="fixed", commission_type="percent", commission_value=0.0, slippage=2, pyramiding=0)
    SOURCE = {"id": "lfk6Inrw", "author": "junseok_bong", "licence": "not stated",
              "url": "https://www.tradingview.com/script/lfk6Inrw-Cash-Account-Portfolio-Trend-System-v2"}

    def init(self):
        i = self.input
        g = "0. Portfolio & Account"
        self.slots = i.int(5, "Portfolio slots (max concurrent positions)", minval=1, maxval=20, group=g)
        self.cash_buffer = i.float(5.0, "Cash buffer (%)", minval=0, maxval=50, step=1, group=g)
        self.allow_frac = i.bool(True, "Allow fractional shares", group=g)
        g = "0b. Asset Class"
        self.asset_mode = i.string("Stocks / ETFs", "Asset class", options=["Stocks / ETFs", "High-volatility stock", "Manual"], group=g)
        g = "1. Trend Regime Filter"
        self.trend_len = i.int(200, "Regime MA length", minval=20, group=g)
        self.trend_type = i.string("SMA", "Regime MA type", options=["SMA", "EMA"], group=g)
        self.use_slope = i.bool(True, "Require regime MA rising", group=g)
        g = "2. Entry Trigger (MACD -- already EMA-based)"
        self.entry_mode = i.string("Breakout (MACD)", "Entry style", options=["Breakout (MACD)", "Pullback (RSI)", "Either (more trades)"], group=g)
        self.src_in = i.source(self.close, "Source", group=g)
        self.fast_len = i.int(12, "MACD fast EMA", minval=1, group=g)
        self.slow_len = i.int(26, "MACD slow EMA", minval=1, group=g)
        self.sig_len = i.int(9, "MACD signal EMA", minval=1, group=g)
        self.use_vol = i.bool(True, "Require above-average volume", group=g)
        self.vol_len = i.int(20, "Volume average length", minval=2, group=g)
        g = "2b. RSI"
        self.rsi_len = i.int(14, "RSI length", minval=2, group=g)
        self.use_veto = i.bool(True, "Veto entries when overbought", group=g)
        self.veto_lvl = i.float(78.0, "Overbought veto level", minval=50, maxval=95, step=1, group=g)
        self.dip_lvl = i.float(40.0, "Pullback: dip below", minval=10, maxval=50, step=1, group=g)
        self.rec_lvl = i.float(50.0, "Pullback: recover above", minval=30, maxval=70, step=1, group=g)
        self.dip_bars = i.int(10, "Pullback: dip must be within N bars", minval=2, maxval=40, group=g)
        self.use_rsi_exit = i.bool(False, "Exit on RSI weakness (not recommended)", group=g)
        self.rsi_exit_lvl = i.float(40.0, "RSI exit level", minval=10, maxval=60, step=1, group=g)
        g = "3. Exit Logic"
        self.atr_len = i.int(22, "ATR length", minval=1, group=g)
        self.atr_mult = i.float(3.0, "Trailing stop ATR multiple (Manual mode)", minval=0.5, step=0.25, group=g)
        self.exit_ma_len = i.int(50, "Trend-break exit MA", minval=2, group=g)
        self.exit_ma_type = i.string("SMA", "Trend-break MA type", options=["SMA", "EMA"], group=g)
        self.use_ma_exit = i.bool(True, "Exit on close below trend-break MA", group=g)
        self.hard_stop_pct = i.float(12.0, "Catastrophic stop % (Manual mode)", minval=1.0, step=0.5, group=g)
        g = "4. Cash Account Constraints"
        self.min_hold = i.int(1, "Minimum holding period (bars)", minval=1, group=g)
        self.settle_bars = i.int(1, "Settlement cooldown after a sale (bars)", minval=0, group=g)
        self.cooldown_bars = i.int(0, "Extra anti-churn cooldown (bars)", minval=0, group=g)
        g = "5. Display"
        i.bool(True, "Show moving averages", group=g)
        i.bool(True, "Show trailing stop", group=g)
        i.bool(True, "Shade regime background", group=g)
        i.bool(True, "Show stats panel", group=g)
        self.last_sell_bar = NA
        self.peak = NA
        self.hard_stop = NA

    def on_bar(self):
        st = self.strategy
        close, high, volume = self.close, self.high, self.volume
        is_high_vol = self.asset_mode == "High-volatility stock"
        is_manual = self.asset_mode == "Manual"
        atr_mult_eff = self.atr_mult if is_manual else (3.5 if is_high_vol else 3.0)
        hard_pct_eff = self.hard_stop_pct if is_manual else (18.0 if is_high_vol else 12.0)
        trend_ma = ta.ema(close, self.trend_len) if self.trend_type == "EMA" else ta.sma(close, self.trend_len)
        exit_ma = ta.ema(close, self.exit_ma_len) if self.exit_ma_type == "EMA" else ta.sma(close, self.exit_ma_len)
        macd = ta.ema(self.src_in, self.fast_len) - ta.ema(self.src_in, self.slow_len)
        sig = ta.ema(macd, self.sig_len)
        hist = macd - sig
        rsi = ta.rsi(self.src_in, self.rsi_len)
        atr = ta.atr(self.atr_len)
        vol_avg = ta.sma(volume, self.vol_len)
        slope = ta.change(trend_ma)
        vol_ok = (not self.use_vol) or volume > vol_avg
        regime_ok = close > trend_ma and ((not self.use_slope) or slope > 0)
        in_trade = st.position_size > 0
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        just_sold = st.position_size == 0 and (not na(pos_1)) and pos_1 > 0
        if just_sold:
            self.last_sell_bar = self.bar_index
        bars_since_sell = 999999 if na(self.last_sell_bar) else self.bar_index - self.last_sell_bar
        funds_settled = bars_since_sell >= self.settle_bars
        cooldown_over = bars_since_sell >= (self.settle_bars + self.cooldown_bars)
        bars_held = self.bar_index - st.opentrades_entry_bar_index(0) if in_trade else NA
        hold_met = in_trade and bars_held >= self.min_hold
        if in_trade:
            self.peak = float(high) if na(self.peak) else pmath.max(self.peak, float(high))
            if na(self.hard_stop):
                self.hard_stop = float(st.opentrades_entry_price(0) * (1.0 - hard_pct_eff / 100.0))
        else:
            self.peak = NA
            self.hard_stop = NA
        trail_stop = self.peak - atr_mult_eff * atr if in_trade else NA
        per_slot = div(st.equity * (1.0 - self.cash_buffer / 100.0), self.slots)
        raw_qty = div(per_slot, close)
        order_qty = raw_qty if self.allow_frac else float(int(raw_qty // 1))
        qty_ok = order_qty > 0
        breakout = ta.crossover(hist, 0) and macd > 0
        dip_cond = rsi < self.dip_lvl
        dipped = ta.barssince(dip_cond) <= self.dip_bars
        x_rec = ta.crossover(rsi, self.rec_lvl)
        pullback = dipped and x_rec and close > exit_ma
        x_rsi_exit = ta.crossunder(rsi, self.rsi_exit_lvl)
        if self.entry_mode == "Breakout (MACD)":
            trigger = breakout
        elif self.entry_mode == "Pullback (RSI)":
            trigger = pullback
        else:
            trigger = breakout or pullback
        veto_ok = (not self.use_veto) or rsi < self.veto_lvl
        long_signal = bool((not in_trade) and regime_ok and trigger and vol_ok and veto_ok and funds_settled and cooldown_over and qty_ok)
        exit_trail = in_trade and close < trail_stop
        exit_ma_brk = in_trade and self.use_ma_exit and close < exit_ma
        exit_hard = in_trade and close < self.hard_stop
        exit_regime = in_trade and close < trend_ma
        exit_rsi = in_trade and self.use_rsi_exit and x_rsi_exit
        exit_signal = hold_met and (exit_trail or exit_ma_brk or exit_hard or exit_regime or exit_rsi)
        if long_signal:
            st.entry("Long", st.long, qty=order_qty, comment="BUY")
        if exit_signal:
            st.close("Long", comment="Exit")
