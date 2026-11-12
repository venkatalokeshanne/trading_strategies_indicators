"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold Sniper — Liquidity Sweep + RSI Divergence
Author       : bobd01003
Source URL   : https://www.tradingview.com/script/hOQRDd8y-Gold-Prime
Pine version : v6
Licence      : MPL-2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Two entry models inside a UTC session: a liquidity-sweep reversal (a bar that wicks beyond the delayed N-bar extreme and the next close back inside it) with a stop beyond the sweep depth and a risk:reward target, and an RSI divergence scalp (price making a new N-bar low/high against the RSI) with an ATR stop and target. Each takes a market entry at the next open while flat; a maximum holding time and the session end close the trade.

Deviations from the original: none.
Not carried over: signal shapes, SL / TP lines, labels, the stats dashboard and alert conditions (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class GoldSniper(Script):
    TITLE = "Gold Sniper — Liquidity Sweep + RSI Divergence"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=50, initial_capital=10000, commission_type="percent", commission_value=0.01, slippage=2)
    SOURCE = {"id": "hOQRDd8y", "author": "bobd01003", "licence": "MPL-2.0",
              "url": "https://www.tradingview.com/script/hOQRDd8y-Gold-Prime"}

    def init(self):
        i = self.input
        g = "═══ Strategy Selection ═══"
        self.use_liq_sweep = i.bool(True, "Enable Liquidity Sweep Reversal", group=g)
        self.use_rsi_diverg = i.bool(True, "Enable RSI Divergence Scalp", group=g)
        self.trade_direction = i.string("Both", "Trade Direction", options=["Long Only", "Short Only", "Both"], group=g)
        g = "═══ Liquidity Sweep Settings ═══"
        self.liq_lookback = i.int(30, "Lookback Period (bars)", minval=10, maxval=100, group=g)
        self.liq_buffer = i.int(3, "Buffer Bars Before Sweep", minval=1, maxval=10, group=g)
        self.liq_rr = i.float(2.0, "Reward : Risk Ratio", minval=1.0, maxval=5.0, step=0.1, group=g)
        self.liq_sl_mult = i.float(0.5, "SL Buffer (× sweep depth)", minval=0.1, maxval=2.0, step=0.1, group=g)
        self.liq_max_bars = i.int(20, "Max Hold (bars)", minval=5, maxval=60, group=g)
        g = "═══ RSI Divergence Settings ═══"
        self.rsi_len = i.int(14, "RSI Length", minval=5, maxval=30, group=g)
        self.rsi_oversold = i.float(40.0, "RSI Oversold Threshold", minval=20, maxval=50, group=g)
        self.rsi_overbought = i.float(60.0, "RSI Overbought Threshold", minval=50, maxval=80, group=g)
        self.rsi_div_lookback = i.int(10, "Divergence Lookback (bars)", minval=5, maxval=30, group=g)
        self.rsi_rr = i.float(1.5, "Reward : Risk Ratio", minval=1.0, maxval=4.0, step=0.1, group=g)
        self.rsi_atr_len = i.int(14, "ATR Length for SL/TP", minval=5, maxval=30, group=g)
        self.rsi_atr_mult = i.float(1.0, "ATR Multiplier for SL", minval=0.5, maxval=3.0, step=0.1, group=g)
        self.rsi_max_bars = i.int(15, "Max Hold (bars)", minval=5, maxval=40, group=g)
        g = "═══ Session Filter ═══"
        self.use_session_filt = i.bool(True, "Filter by Trading Session", group=g)
        self.session_start = i.int(8, "Session Start Hour (UTC)", minval=0, maxval=23, group=g)
        self.session_end = i.int(20, "Session End Hour (UTC)", minval=0, maxval=23, group=g)
        g = "═══ Risk Management ═══"
        self.risk_pct = i.float(1.0, "Risk per Trade (%)", minval=0.1, maxval=5.0, step=0.1, group=g)
        self.max_daily_trades = i.int(10, "Max Trades per Day", minval=1, maxval=50, group=g)
        self.daily_trades = 0
        self.prev_dow = NA
        self.entry_bar = 0
        self.active_strat = ""

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        if self.use_session_filt:
            h = self.hour(self.time, "UTC")
            session_active = h >= self.session_start and h < self.session_end
        else:
            session_active = True
        dow = self.dayofweek()
        if na(self.prev_dow) or dow != self.prev_dow:
            self.daily_trades = 0
        self.prev_dow = dow
        can_trade = self.daily_trades < self.max_daily_trades
        rsi_val = ta.rsi(close, self.rsi_len)
        atr_val = ta.atr(self.rsi_atr_len)
        run_high_s, run_low_s = ta.highest(high, self.liq_lookback), ta.lowest(low, self.liq_lookback)
        rh_h, rl_h = self.H("run_high"), self.H("run_low")
        run_high, run_low = rh_h[self.liq_buffer], rl_h[self.liq_buffer]
        rh_h.set(run_high_s)
        rl_h.set(run_low_s)
        low_1, high_1, close_1 = low[1], high[1], close[1]
        bull_sweep = low_1 < run_low and close > run_low and close > close_1
        bear_sweep = high_1 > run_high and close < run_high and close < close_1
        bull_sweep_depth = run_low - low_1
        bear_sweep_depth = high_1 - run_high
        price_low_s, rsi_low_s = ta.lowest(close, self.rsi_div_lookback), ta.lowest(rsi_val, self.rsi_div_lookback)
        price_high_s, rsi_high_s = ta.highest(close, self.rsi_div_lookback), ta.highest(rsi_val, self.rsi_div_lookback)
        pl_h, rl2_h, ph_h, rh2_h = self.H("price_low"), self.H("rsi_low"), self.H("price_high"), self.H("rsi_high")
        price_low_3, rsi_low_3, price_high_3, rsi_high_3 = pl_h[3], rl2_h[3], ph_h[3], rh2_h[3]
        pl_h.set(price_low_s)
        rl2_h.set(rsi_low_s)
        ph_h.set(price_high_s)
        rh2_h.set(rsi_high_s)
        bull_div = close < price_low_3 and rsi_val > rsi_low_3 and rsi_val < self.rsi_oversold
        bear_div = close > price_high_3 and rsi_val < rsi_high_3 and rsi_val > self.rsi_overbought
        can_long = self.trade_direction == "Both" or self.trade_direction == "Long Only"
        can_short = self.trade_direction == "Both" or self.trade_direction == "Short Only"
        liq_buy = self.use_liq_sweep and bull_sweep and bull_sweep_depth > 0 and session_active and can_trade and can_long
        liq_sell = self.use_liq_sweep and bear_sweep and bear_sweep_depth > 0 and session_active and can_trade and can_short
        rsi_buy = self.use_rsi_diverg and bull_div and session_active and can_trade and can_long
        rsi_sell = self.use_rsi_diverg and bear_div and session_active and can_trade and can_short
        no_position = st.position_size == 0
        liq_buy_sl = low_1 - bull_sweep_depth * self.liq_sl_mult
        liq_buy_tp = close + (close - liq_buy_sl) * self.liq_rr
        liq_sell_sl = high_1 + bear_sweep_depth * self.liq_sl_mult
        liq_sell_tp = close - (liq_sell_sl - close) * self.liq_rr
        rsi_buy_sl = close - atr_val * self.rsi_atr_mult
        rsi_buy_tp = close + atr_val * self.rsi_atr_mult * self.rsi_rr
        rsi_sell_sl = close + atr_val * self.rsi_atr_mult
        rsi_sell_tp = close - atr_val * self.rsi_atr_mult * self.rsi_rr
        if liq_buy and no_position:
            st.entry("Liq Long", st.long)
            st.exit("Liq Long TP/SL", "Liq Long", stop=liq_buy_sl, limit=liq_buy_tp)
            self.entry_bar = self.bar_index
            self.active_strat = "liq"
            self.daily_trades += 1
        if liq_sell and no_position:
            st.entry("Liq Short", st.short)
            st.exit("Liq Short TP/SL", "Liq Short", stop=liq_sell_sl, limit=liq_sell_tp)
            self.entry_bar = self.bar_index
            self.active_strat = "liq"
            self.daily_trades += 1
        if rsi_buy and no_position:
            st.entry("RSI Long", st.long)
            st.exit("RSI Long TP/SL", "RSI Long", stop=rsi_buy_sl, limit=rsi_buy_tp)
            self.entry_bar = self.bar_index
            self.active_strat = "rsi"
            self.daily_trades += 1
        if rsi_sell and no_position:
            st.entry("RSI Short", st.short)
            st.exit("RSI Short TP/SL", "RSI Short", stop=rsi_sell_sl, limit=rsi_sell_tp)
            self.entry_bar = self.bar_index
            self.active_strat = "rsi"
            self.daily_trades += 1
        max_bars_active = self.liq_max_bars if self.active_strat == "liq" else self.rsi_max_bars
        if (not no_position) and (self.bar_index - self.entry_bar) >= max_bars_active:
            st.close_all("Time Exit")
        if (not no_position) and self.use_session_filt and not session_active:
            st.close_all("Session End")
