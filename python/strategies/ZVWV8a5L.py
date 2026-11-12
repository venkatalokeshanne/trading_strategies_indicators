"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Adaptive Multi-Factor Swing Strategy V22 - Position Direction Guard
Author       : not stated
Source URL   : https://www.tradingview.com/script/ZVWV8a5L
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, 1 contract). The same eight-vote score as the plain version (MACD vs signal, stochastic K vs D computed as ta.stoch(high, low, close, 14) with the source arguments as written, 10-bar momentum, RSI(7) vs 50, Vortex, DMI, the custom MFI(10) and a Fisher transform) opens a long at +4 or more with RSI under its limit when not already long, a short at -6 or less with RSI over 30 when not already short; every bar the score falling back (<= 1 for longs, >= -2 for shorts) or the parabolic SAR flipping against the position closes it. Everything is closed (and nothing opened) once equity falls to 50 % of the initial capital. The chop-zone cool-down of the plain version is not applied (trading is always allowed).
Deviations from the original: none (the untitled inputs get their variable names as titles so they can be set). The sliding sums of the source's `sumN` run over the history of the passed expression, kept here in lists.
Not carried over: the plot and the background colour.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class AdaptiveMultiFactorV22(Script):
    TITLE = "Adaptive Multi-Factor Swing Strategy V22 - Position Direction Guard"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100, initial_capital=100000)
    SOURCE = {"id": "ZVWV8a5L", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/ZVWV8a5L"}

    def init(self):
        i = self.input
        self.fast = i.int(12, "fast")
        self.slow = i.int(26, "slow")
        self.sig = i.int(7, "sig")
        self.stoch_len = i.int(14, "stochLen")
        self.stoch_sig = i.int(3, "stochSig")
        self.mom_len = i.int(10, "momLen")
        self.rsi_len = i.int(7, "rsiLen")
        self.rsi_long_limit = i.int(100, "rsiLongLimit")
        self.rsi_short_limit = i.int(30, "rsiShortLimit")
        self.psar_start = i.float(0.0, "psarStart")
        self.psar_inc = i.float(0.02, "psarInc")
        self.psar_max = i.float(0.2, "psarMax")
        self.vortex_len = i.int(8, "vortexLen")
        self.dmi_len = i.int(8, "dmiLen")
        self.mfi_len = i.int(10, "mfiLen")
        self.fish_len = i.int(10, "fishLen")
        self.fish_sig = i.int(6, "fishSig")
        self.long_score_th = i.int(4, "longScoreTh")
        self.long_exit_th = i.int(1, "longExitTh")
        self.short_score_th = i.int(-6, "shortScoreTh")
        self.short_exit_th = i.int(-2, "shortExitTh")
        self.bankrupt_pct = i.float(50.0, "Bankrupt %")
        self.cooldown_bars = i.int(50, "Cooldown Bars")
        self.adx_limit = i.float(10, "ADX Danger")
        self.atr_len = i.int(14, "atrLen")
        self.is_bankrupt = False
        self.hist = {k: [] for k in ("vmp", "vmm", "trs", "pos", "neg")}

    def _sum_n(self, name, value, length):
        """sumN: sum of nz(src[i], 0) over the last `length` bars of the expression `value`."""
        h = self.hist[name]
        h.append(0.0 if na(value) else float(value))
        return sum(h[-length:])

    def on_bar(self):
        st = self.strategy
        close, high, low, volume = self.close, self.high, self.low, self.volume
        low_1, high_1 = nz(self.low[1]), nz(self.high[1])
        macd_line = ta.ema(close, self.fast) - ta.ema(close, self.slow)
        signal = ta.ema(macd_line, self.sig)
        k = ta.stoch(high, low, close, self.stoch_len)
        d = ta.sma(k, self.stoch_sig)
        mom = ta.mom(close, self.mom_len)
        rsi = ta.rsi(close, self.rsi_len)
        psar = ta.sar(self.psar_start, self.psar_inc, self.psar_max)
        atr = ta.atr(self.atr_len)
        atr_ma = ta.sma(atr, 20)
        plus_di, minus_di, adx = ta.dmi(self.dmi_len, self.dmi_len)
        vm_plus = self._sum_n("vmp", abs(high - low_1), self.vortex_len)
        vm_minus = self._sum_n("vmm", abs(low - high_1), self.vortex_len)
        tr_sum = self._sum_n("trs", ta.tr(False), self.vortex_len)
        vip = div(vm_plus, tr_sum) if tr_sum != 0 else 0
        vim = div(vm_minus, tr_sum) if tr_sum != 0 else 0
        tp = (high + low + close) / 3
        raw_mf = tp * volume
        h_tp = self.H("tp")
        tp_1 = nz(h_tp[1])
        pos_mf = raw_mf if tp > tp_1 else 0
        neg_mf = raw_mf if tp < tp_1 else 0
        pos_sum = self._sum_n("pos", pos_mf, self.mfi_len)
        neg_sum = self._sum_n("neg", neg_mf, self.mfi_len)
        mfi = 100 if neg_sum == 0 else 100 - div(100, 1 + div(pos_sum, neg_sum))
        hi = ta.highest(close, self.fish_len)
        lo = ta.lowest(close, self.fish_len)
        v = div(close - lo, hi - lo) if hi != lo else 0.5
        v = pmath.max(pmath.min(v, 0.999), 0.001)
        fish = 0.5 * pmath.log(div(v, 1 - v))
        fish_sig_line = ta.sma(fish, self.fish_sig)
        score = 0
        score += 1 if macd_line > signal else -1
        score += 1 if k > d else -1
        score += 1 if mom > 0 else -1
        score += 1 if rsi > 50 else -1
        score += 1 if vip > vim else -1
        score += 1 if plus_di > minus_di else -1
        score += 1 if mfi > 50 else -1
        score += 1 if fish > fish_sig_line else -1
        trade_allowed = True
        bankrupt_level = st.initial_capital * self.bankrupt_pct / 100
        if (not self.is_bankrupt) and st.equity <= bankrupt_level:
            self.is_bankrupt = True
            st.close_all(comment="BANKRUPT")
        long_entry = score >= self.long_score_th and rsi < self.rsi_long_limit
        long_exit = score <= self.long_exit_th or psar > close
        short_entry = score <= self.short_score_th and rsi > self.rsi_short_limit
        short_exit = score >= self.short_exit_th or psar < close
        if long_entry and not self.is_bankrupt and trade_allowed and st.position_size <= 0:
            st.entry("LONG", st.long)
        if long_exit:
            st.close("LONG")
        if short_entry and not self.is_bankrupt and trade_allowed and st.position_size >= 0:
            st.entry("SHORT", st.short)
        if short_exit:
            st.close("SHORT")
        h_tp.set(tp)
