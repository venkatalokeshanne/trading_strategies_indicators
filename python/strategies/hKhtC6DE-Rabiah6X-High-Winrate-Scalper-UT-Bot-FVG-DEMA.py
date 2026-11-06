"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rabiah6X - UT Bot + 1:1 Scalp Targets + DEMA + FVG (High Winrate Scalper)
Author       : Soheibhussen357
Source URL   : https://www.tradingview.com/script/hKhtC6DE-Rabiah6X-High-Winrate-Scalper-UT-Bot-FVG-DEMA
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A UT Bot ATR trailing stop is crossed by the close (optionally filtered by volume and a higher-timeframe SMA trend) to enter long / short (reversing). While in a position the
exit order carries the live trailing stop and a target fixed at the signal (risk x R:R). A close crossing the DEMA the wrong way or the RSI crossing back through the overbought / oversold level closes the trade at
the next open; those four cross tests are only evaluated while a position of the matching side is open (Pine v6's lazy `and`), so their previous-argument history skips bars exactly as in TradingView. The FVG / ADX /
expansion-candle conditions only classify the plotted labels (strong vs standard) and do not feed orders.

Deviations from the original: none for trading.
Not carried over: the DEMA / trailing-stop plots, FVG diamonds, buy / sell labels, exit crosses and bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, nz, pmath, ta


class RabiahScalper(Script):
    TITLE = "Rabiah6X - UT Bot + 1:1 Scalp Targets + DEMA + FVG"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "hKhtC6DE", "author": "Soheibhussen357", "licence": "not stated",
              "url": "https://www.tradingview.com/script/hKhtC6DE-Rabiah6X-High-Winrate-Scalper-UT-Bot-FVG-DEMA"}

    def init(self):
        g = "UT Bot Setup"
        self.keyvalue = self.input.float(2.0, "Key Value (Sensitivity)", step=0.1, group=g)
        self.atrperiod = self.input.int(10, "ATR Period", group=g)
        self.htf_filter_on = self.input.bool(False, "Enable Higher Timeframe Trend Filter", group=g)
        self.htf_res = self.input.timeframe("60", "Higher Timeframe", group=g)
        self.vol_filter_on = self.input.bool(False, "Enable Volume Filter (above average)", group=g)
        self.vol_len = self.input.int(20, "Volume MA Length", group=g)
        g = "DEMA Settings"
        self.dema_len = self.input.int(21, "DEMA Length", group=g)
        self.dema_src = self.input.source(self.close, "DEMA Source", group=g)
        g = "Early Exit Settings"
        self.rr_multiplier = self.input.float(1.0, "Risk:Reward Target (1.0 = 1:1)", step=0.1, group=g)
        self.use_dema_exit = self.input.bool(True, "Enable DEMA Fast Exit", group=g)
        self.use_rsi_exit = self.input.bool(True, "Enable RSI Reversal Exit", group=g)
        self.rsi_len = self.input.int(14, "RSI Length", group=g)
        self.rsi_overbought = self.input.int(70, "RSI Overbought Level (Long Exit)", group=g)
        self.rsi_oversold = self.input.int(30, "RSI Oversold Level (Short Exit)", group=g)
        self.stop = 0.0
        self.target_l = NA
        self.target_s = NA

    def on_bar(self):
        src = self.close
        ema1 = ta.ema(self.dema_src, self.dema_len)
        ema2 = ta.ema(ema1, self.dema_len)
        dema_val = 2 * ema1 - ema2
        rsi_val = ta.rsi(src, self.rsi_len)
        x_atr = ta.atr(self.atrperiod)
        n_loss = self.keyvalue * x_atr
        prev_stop = nz(self.stop, 0.0)
        close1 = self.close[1]
        if src > prev_stop and close1 > prev_stop:
            self.stop = pmath.max(prev_stop, src - n_loss)
        elif src < prev_stop and close1 < prev_stop:
            self.stop = pmath.min(prev_stop, src + n_loss)
        elif src > prev_stop:
            self.stop = src - n_loss
        else:
            self.stop = src + n_loss
        stop = self.stop
        htf_len = 50
        htf_close, htf_sma = self.security(None, self.htf_res, lambda v: (v.close, ta.sma(v.close, htf_len)))
        htf_trend_up = htf_close > htf_sma
        vol_ok = (self.volume > ta.sma(self.volume, self.vol_len)) if self.vol_filter_on else True
        htf_ok_long = htf_trend_up if self.htf_filter_on else True
        htf_ok_short = (not htf_trend_up) if self.htf_filter_on else True
        cross_up = ta.crossover(src, stop)
        cross_dn = ta.crossunder(src, stop)
        base_buy = cross_up and vol_ok and htf_ok_long
        base_sell = cross_dn and vol_ok and htf_ok_short
        st = self.strategy
        dema_exit_long = self.use_dema_exit and st.position_size > 0 and ta.crossunder(src, dema_val)
        dema_exit_short = self.use_dema_exit and st.position_size < 0 and ta.crossover(src, dema_val)
        rsi_exit_long = self.use_rsi_exit and st.position_size > 0 and ta.crossunder(rsi_val, self.rsi_overbought)
        rsi_exit_short = self.use_rsi_exit and st.position_size < 0 and ta.crossover(rsi_val, self.rsi_oversold)
        self.target_l = self.close + ((self.close - stop) * self.rr_multiplier) if base_buy else self.target_l
        self.target_s = self.close - ((stop - self.close) * self.rr_multiplier) if base_sell else self.target_s
        if base_buy:
            st.entry("Long", st.long)
        if st.position_size > 0:
            st.exit("TP/SL Long", from_entry="Long", limit=self.target_l, stop=stop)
        if base_sell:
            st.entry("Short", st.short)
        if st.position_size < 0:
            st.exit("TP/SL Short", from_entry="Short", limit=self.target_s, stop=stop)
        if dema_exit_long or rsi_exit_long:
            st.close("Long", comment="Early Exit")
        if dema_exit_short or rsi_exit_short:
            st.close("Short", comment="Early Exit")
        self.plot(dema_val, "DEMA 21", color=color.fuchsia, linewidth=2)
        self.plot(stop, "Trailing Stop", color=color.blue, linewidth=2)
