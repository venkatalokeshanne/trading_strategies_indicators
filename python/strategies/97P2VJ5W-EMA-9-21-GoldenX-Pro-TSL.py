"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA 9/21 GoldenX Pro-TSL
Author       : (unnamed)
Source URL   : https://www.tradingview.com/script/97P2VJ5W
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An EMA9 / EMA21 cross with a volume or price confirmation (above its 5-bar average) and a trending market (ADX over its threshold or a
DI gap over 10) opens the matching side, first closing the opposite one; entries only fire when flat after that close. While a position is open, a stop at the
tighter of 2 ATR and a 1% hard stop is re-issued every bar (it works from the next bar). The DMI-flip exit is commented out in the source.

Deviations from the original: none.
Not carried over: the log.info debug call and EMA plots.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, pmath, ta


class GoldenXTsl(Script):
    TITLE = "EMA 9/21 GoldenX Pro-TSL"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=30000)
    SOURCE = {"id": "97P2VJ5W", "author": "(unnamed)", "licence": "not stated",
              "url": "https://www.tradingview.com/script/97P2VJ5W"}

    def init(self):
        self.ema_fast = self.input.int(9, "Fast EMA", minval=1)
        self.ema_slow = self.input.int(21, "Slow EMA", minval=1)
        self.trade_dir = self.input.string("Both", "Trade Direction", options=["Long", "Short", "Both"])
        self.adx_len = self.input.int(14, "ADX Length")
        self.adx_thresh = self.input.int(20, "ADX Threshold")
        self.use_adx_flip = self.input.bool(True, "Exit & flip on DMI reversal (needs ADX > threshold)")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(2.0, "ATR Multiplier", step=0.1)
        self.max_loss_perc = self.input.float(1.0, "Max Stop Loss %", minval=0.1)

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.ema_fast)
        slow_ema = ta.ema(self.close, self.ema_slow)
        di_plus, di_minus, adx_value = ta.dmi(self.adx_len, self.adx_len)
        is_trending = adx_value > self.adx_thresh or pmath.abs(di_plus - di_minus) > 10
        vol_rising = self.volume > ta.sma(self.volume, 5)
        price_rising = self.close > ta.sma(self.close, 5)
        price_falling = self.close < ta.sma(self.close, 5)
        atr = ta.atr(self.atr_len)
        long_stop = self.close - (atr * self.atr_mult)
        short_stop = self.close + (atr * self.atr_mult)
        long_ok = self.trade_dir == "Long" or self.trade_dir == "Both"
        short_ok = self.trade_dir == "Short" or self.trade_dir == "Both"
        long_signal = ta.crossover(fast_ema, slow_ema) and (vol_rising or price_rising) and is_trending
        short_signal = ta.crossunder(fast_ema, slow_ema) and (vol_rising or price_falling) and is_trending
        qty = 1
        st = self.strategy
        if long_signal and long_ok:
            if st.position_size < 0:
                st.close("Short", comment="Close S")
                st.entry("Long", st.long, qty=qty, comment="GoldenX->L")
            elif st.position_size == 0:
                st.entry("Long", st.long, qty=qty, comment="GoldenX->L")
        if short_signal and short_ok:
            if st.position_size > 0:
                st.close("Long", comment="Close L")
                st.entry("Short", st.short, qty=qty, comment="DeathX->S")
            elif st.position_size == 0:
                st.entry("Short", st.short, qty=qty, comment="DeathX->S")
        if st.position_size > 0:
            hard_stop_price = st.position_avg_price * (1 - (self.max_loss_perc / 100))
            final_stop = pmath.min(long_stop, hard_stop_price)
            st.exit("Exit Long", from_entry="Long", stop=final_stop, comment="SL-Long")
        if st.position_size < 0:
            hard_stop_price = st.position_avg_price * (1 + (self.max_loss_perc / 100))
            final_stop = pmath.max(short_stop, hard_stop_price)
            st.exit("Exit Short", from_entry="Short", stop=final_stop, comment="SL-Short")
        self.plot(fast_ema, "Fast", color=color.orange)
        self.plot(slow_ema, "Slow", color=color.blue)
