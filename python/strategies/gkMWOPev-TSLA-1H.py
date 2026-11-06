"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TSLA Daily — Jayz_ze Combo D
Author       : jy819989
Source URL   : https://www.tradingview.com/script/gkMWOPev-TSLA-1H
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A "BlueWave" oscillator (EMA spread of a mean of RSI and raw stochastic plus a TCI term) and a smoothed money-flow index both above zero and rising, with the close above EMA50 and EMA200,
buy on the first bar of the run (not the bar after a run already held) at the next open. The stop is the lowest low of the last 10 bars, issued with the entry and re-issued every bar while long; a close under EMA50 exits.

Deviations from the original: none.
Not carried over: EMA plots, stop line, entry shape, below-EMA200 background and the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, pmath, ta


class JayzzeComboD(Script):
    TITLE = "TSLA Daily — Jayz_ze Combo D"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2000, default_qty_type="percent_of_equity", commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "gkMWOPev", "author": "jy819989", "licence": "not stated", "url": "https://www.tradingview.com/script/gkMWOPev-TSLA-1H"}

    def init(self):
        self.risk_pct = self.input.float(5.0, "Risk % per trade", minval=0.5, maxval=10)
        self.stop_bars = self.input.int(10, "Stop lookback (bars)", minval=5, maxval=30)
        self.length_fast = self.input.int(6, "BlueWave fast length")
        self.length_slow = self.input.int(35, "BlueWave slow length")
        self.rsi_len = self.input.int(14, "RSI length")
        self.stoch_len = self.input.int(14, "Stoch length")
        self.mfi_len = self.input.int(60, "MFI length")
        self.mfi_mult = self.input.float(0.8, "MFI multiplier")

    def on_bar(self):
        ema200 = S(ta.ema(self.close, 200))
        ema50 = S(ta.ema(self.close, 50))
        hlc3_val = self.hlc3
        n1 = ta.ema(hlc3_val, 10)
        n2 = ta.ema(pmath.abs(hlc3_val - n1), 10)
        ci = div(hlc3_val - n1, 0.015 * n2)
        tci = ta.ema(ci, 21)
        comb = (ta.rsi(self.close, self.rsi_len) + ta.stoch(self.close, self.high, self.low, self.stoch_len)) / 2
        blue_wave = S(ta.ema(comb, self.length_fast) - ta.ema(comb, self.length_slow) + tci / 2)
        mfi_raw = ta.mfi(hlc3_val, self.mfi_len) - 50
        money_flow = S(ta.ema(mfi_raw, 5) * self.mfi_mult)
        close = S(self.close)
        bw_slope = blue_wave[0] - blue_wave[1]
        mf_slope = money_flow[0] - money_flow[1]
        st = self.strategy
        entry_signal = (blue_wave[0] > 0 and money_flow[0] > 0 and bw_slope > 0 and mf_slope > 0
                        and close[0] > ema200[0] and close[0] > ema50[0] and st.position_size == 0)
        prev_signal = (blue_wave[1] > 0 and money_flow[1] > 0 and (blue_wave[1] - blue_wave[2]) > 0 and (money_flow[1] - money_flow[2]) > 0
                       and close[1] > ema200[1] and close[1] > ema50[1])
        struct_stop = ta.lowest(self.low, self.stop_bars)
        stop_dist = pmath.max(self.close - struct_stop, self.close * 0.005)
        risk_amt = st.equity * self.risk_pct / 100
        qty = div(risk_amt, stop_dist)
        if entry_signal and not prev_signal:
            st.entry("Long", st.long, qty=qty)
            st.exit("Stop", "Long", stop=struct_stop)
        if st.position_size > 0:
            st.exit("Stop", "Long", stop=struct_stop)
        if st.position_size > 0 and self.close < ema50[0]:
            st.close("Long", comment="EMA50")
        self.plot(ema50[0], "EMA50", color=color.orange)
        self.plot(ema200[0], "EMA200", color=color.purple, linewidth=2)
