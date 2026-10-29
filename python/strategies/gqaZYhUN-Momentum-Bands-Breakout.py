"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Momentum Exhaustion Breakout (Momentum Bands | Breakout)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/gqaZYhUN-Momentum-Bands-Breakout
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A high above the previous N-bar high on expanded volume enters long in an EMA uptrend with rising RSI above a threshold,
or (outside an uptrend, with a weakening RSI) a "fade" short. Position size risks a % of equity per ATR stop distance. While in a position a stop
around the average price and an ATR trailing stop (trail points and offset = ATR x mult, read as ticks as in Pine) are issued each bar.

Deviations from the original: none.
Not carried over: the glow bands, fills and candle colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class MomentumExhaustionBreakout(Script):
    TITLE = "Momentum Exhaustion Breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "gqaZYhUN", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gqaZYhUN-Momentum-Bands-Breakout"}

    def init(self):
        self.n_len = self.input.int(20, "Breakout Lookback (N bars)")
        self.vol_len = self.input.int(20, "Volume MA Length")
        self.vol_mult = self.input.float(1.5, "Volume Expansion Multiplier", step=0.1)
        self.ema_fast_len = self.input.int(20, "EMA Fast (trend filter)")
        self.ema_slow_len = self.input.int(50, "EMA Slow (trend filter)")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.roc_len = self.input.int(5, "RSI Rate-of-Change Lookback")
        self.rsi_confirm = self.input.float(55, "Min RSI to Confirm Longs")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_sl_mult = self.input.float(1.5, "Initial Stop = ATR x")
        self.atr_trail_mult = self.input.float(1.5, "Trailing Stop = ATR x")
        self.risk_pct = self.input.float(1.0, "Risk % of Equity per Trade")
        self.allow_shorts = self.input.bool(True, "Enable Fade-the-Fakeout Shorts")
        self.band_mult = self.input.float(2.0, "Band Width = ATR x", step=0.1, group="Visuals")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        uptrend = ema_fast > ema_slow
        prior_high = ta.highest(self.high[1], self.n_len)
        vol_avg = ta.sma(self.volume, self.vol_len)
        vol_expansion = self.volume > vol_avg * self.vol_mult
        rsi_val = ta.rsi(self.close, self.rsi_len)
        rsi_hist = self.H("rsi")
        rsi_roc = rsi_val - rsi_hist[self.roc_len]
        prior_rsi_pk = ta.highest(rsi_hist[1], self.n_len)
        rsi_hist.set(rsi_val)
        breakout_up = self.high > prior_high and vol_expansion
        long_signal = breakout_up and uptrend and rsi_roc > 0 and rsi_val > self.rsi_confirm
        fade_signal = self.allow_shorts and breakout_up and not uptrend and (rsi_val < prior_rsi_pk or rsi_roc < 0)
        atr_val = ta.atr(self.atr_len)
        st = self.strategy
        risk_amount = st.equity * (self.risk_pct / 100)
        sl_distance = atr_val * self.atr_sl_mult
        qty = div(risk_amount, sl_distance) if sl_distance > 0 else 0
        if long_signal and st.position_size == 0 and qty > 0:
            st.entry("Long", st.long, qty=qty)
        if fade_signal and st.position_size == 0 and qty > 0:
            st.entry("Fade Short", st.short, qty=qty)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=st.position_avg_price - sl_distance,
                    trail_points=atr_val * self.atr_trail_mult, trail_offset=atr_val * self.atr_trail_mult)
        if st.position_size < 0:
            st.exit("Exit Short", "Fade Short", stop=st.position_avg_price + sl_distance,
                    trail_points=atr_val * self.atr_trail_mult, trail_offset=atr_val * self.atr_trail_mult)
        band_width = atr_val * self.band_mult
        self.plot(ema_fast, "Trend Basis", color=color.gray)
        self.plot(ema_fast + band_width, "Upper Band Core", color=color.teal)
        self.plot(ema_fast - band_width, "Lower Band Core", color=color.red)
