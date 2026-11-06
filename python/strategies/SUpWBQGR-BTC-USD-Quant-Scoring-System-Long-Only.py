"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Quant Scoring System Long Only
Author       : not stated
Source URL   : https://www.tradingview.com/script/SUpWBQGR
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A score of five normalised factors (EMA 20/100 gap in ATR units, 1-bar rate of change, stretch from the volume-weighted average, volume, and the slope of the 20-bar regression line, each z-scored over 20 bars and clamped to +/-3) scaled by 7 must exceed 2 with the fast EMA over the slow one and the close over the slow EMA to buy with all the equity (leverage 1). While long, an exit order holds the larger of the 2 ATR stop and the 2 % hard stop with a target 300.5 ATR above the average price (so effectively no target); the position closes when the score drops under 0 or the close falls under the fast EMA. Once the high has run 8 % above the entry the strategy enters runner mode: only the hard stop stays and the exit is a close when the 4-hour close is under its EMA(50) while that EMA is falling.
Deviations from the original: none.
Not carried over: plots, bar colours and the threshold lines.
────────────────────────────────────────────────────────────────────────
"""


from pinelib import NA, Script, div, na, pmath, ta


def _clamp(x, lo, hi):
    return pmath.max(lo, pmath.min(hi, x))


class QuantScoring(Script):
    TITLE = "Quant Scoring System Long Only"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=92, pyramiding=0, commission_type="percent", commission_value=0.02)
    SOURCE = {"id": "SUpWBQGR", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/SUpWBQGR"}

    def init(self):
        i = self.input
        self.leverage = i.float(1.0, "Leverage", minval=1.0, step=0.5)
        self.len_fast = i.int(20, "Fast Length")
        self.len_slow = i.int(100, "Slow Length")
        self.len_mom = i.int(1, "Momentum Length")
        self.len_vol = i.int(10, "Volatility Length")
        self.len_z = i.int(20, "ZScore Length")
        self.long_th = i.float(2.0, "Long Score Threshold", step=0.1)
        self.exit_th = i.float(0.0, "Exit Score Threshold", step=0.1)
        self.atr_len = i.int(14, "ATR Length")
        self.atr_sl = i.float(2.0, "Stop ATR", step=0.1)
        self.atr_tp = i.float(300.5, "Target ATR", step=0.1)
        self.hard_sl_pct = i.float(2.0, "Hard Stop %", minval=0.1, step=0.1)
        self.big_trade_pct = i.float(8.0, "Runner Trigger Profit %", minval=0.1, step=0.1)
        self.htf_tf = i.timeframe("240", "Runner Higher Timeframe")
        self.htf_ema_len = i.int(50, "Runner HTF EMA Length", minval=1)
        self.runner_mode = False

    def _norm(self, src):
        m = ta.sma(src, self.len_z)
        s = ta.stdev(src, self.len_z)
        z = 0.0 if s == 0.0 else div(src - m, s)
        return _clamp(z, -3.0, 3.0) / 3.0

    def on_bar(self):
        st = self.strategy
        close, high = self.close, self.high
        h_hema = self.H("hema")
        hema_1 = h_hema[1]
        close_1 = self.close[1]
        ema_fast = ta.ema(close, self.len_fast)
        ema_slow = ta.ema(close, self.len_slow)
        atr = ta.atr(self.atr_len)
        trend = 0.0 if atr == 0.0 else _clamp(div(ema_fast - ema_slow, atr), -3.0, 3.0) / 3.0
        mom_raw = ta.roc(close, self.len_mom)
        mom = self._norm(mom_raw)
        basis = ta.vwma(close, self.len_fast)
        stretch = 0.0 if atr == 0.0 else div(close - basis, atr)
        mr = _clamp(-stretch, -3.0, 3.0) / 3.0
        vol_raw = ta.stdev(pmath.log(div(close, close_1)), self.len_vol)
        vol_reg = self._norm(vol_raw)
        vol_conf = self._norm(self.volume)
        slope = ta.linreg(close, self.len_fast, 0) - ta.linreg(close, self.len_fast, 1)
        slope_n = self._norm(slope)
        score = 0.20 * trend + 0.20 * mom + 0.10 * mr + 0.0 * vol_reg * pmath.sign(trend) + 0.10 * vol_conf * pmath.sign(mom) + 0.10 * slope_n
        score_scaled = score * 7.0
        regime_long = ema_fast > ema_slow and close > ema_slow
        long_signal = score_scaled > self.long_th and regime_long
        base_exit_signal = score_scaled < self.exit_th or close < ema_fast
        safe_equity = pmath.max(st.equity, 0)
        pos_qty_raw = div(safe_equity * self.leverage, close) if close > 0 else 0
        pos_qty = pmath.max(pos_qty_raw, 0)
        if long_signal and st.position_size == 0 and pos_qty > 0:
            st.entry("Long", st.long, qty=pos_qty)
        avg = st.position_avg_price
        atr_stop = avg - self.atr_sl * atr
        hard_stop = avg * (1.0 - self.hard_sl_pct / 100.0)
        normal_stop = pmath.max(atr_stop, hard_stop)
        runner_stop = hard_stop
        long_take = avg + self.atr_tp * atr
        htf_close = self.security(None, self.htf_tf, lambda v: float(v.close))
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_ema_len))
        htf_bearish = htf_close < htf_ema and htf_ema < hema_1
        pos = st.position_size
        if pos <= 0:
            self.runner_mode = False
        runner_trigger_price = avg * (1.0 + self.big_trade_pct / 100.0)
        if pos > 0 and not self.runner_mode and high >= runner_trigger_price:
            self.runner_mode = True
        if pos > 0:
            if self.runner_mode:
                st.exit("Long Exit", from_entry="Long", stop=runner_stop)
                if htf_bearish:
                    st.close("Long", comment="Runner HTF Bearish Exit")
            else:
                st.exit("Long Exit", from_entry="Long", stop=normal_stop, limit=long_take)
                if base_exit_signal:
                    st.close("Long", comment="Base Exit")
        h_hema.set(htf_ema)
