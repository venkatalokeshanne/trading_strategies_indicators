"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NQ Scalping Strategy (EMA + RSI + ATR) [Entries/Exits]
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/h6h2mneH-NQ-Scalping-Strategy-EMA-RSI-ATR-Entries-Exits
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In session, a close hugging EMA100 (within 0.10%) on the trend side with RSI14 momentum (>= 55 / <= 45) enters at the
bar close (process_orders_on_close), reversing an open opposite trade. Both exit orders are rebuilt every bar from position_avg_price
(ATR stop 1.0, ATR target 1.2) and are na while flat; a trade is closed after 20 bars in the market.

Deviations from the original: none.
Not carried over: EMA plot and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class NqScalping(Script):
    TITLE = "NQ Scalping Strategy (EMA + RSI + ATR) [Entries/Exits]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="cash_per_contract", commission_value=0.0, slippage=0,
                    process_orders_on_close=True, pyramiding=0)
    SOURCE = {"id": "h6h2mneH", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/h6h2mneH-NQ-Scalping-Strategy-EMA-RSI-ATR-Entries-Exits"}

    def init(self):
        self.ema_len = self.input.int(100, "EMA Length", minval=1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.rsi_bull = self.input.float(55, "RSI Bull Threshold", step=0.5)
        self.rsi_bear = self.input.float(45, "RSI Bear Threshold", step=0.5)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.stop_atr = self.input.float(1.0, "Stop = ATR x", step=0.1)
        self.target_atr = self.input.float(1.2, "Target = ATR x", step=0.1)
        self.pullback_pct = self.input.float(0.10, "Pullback Band (%) around EMA", step=0.01)
        self.use_session = self.input.bool(True, "Use Session Filter")
        self.session_str = self.input.session("0930-1600", "Session (Exchange Time)")
        self.use_time_exit = self.input.bool(True, "Time Exit")
        self.max_bars_in_trade = self.input.int(20, "Max Bars in Trade (time exit)", minval=1)
        self.bars_in_trade = 0

    def on_bar(self):
        ema = ta.ema(self.close, self.ema_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        in_session = (not self.use_session) or (not na(self.time_fn(None, self.session_str)))
        band = ema * (self.pullback_pct / 100.0)
        near_ema = pmath.abs(self.close - ema) <= band
        bull_trend = self.close > ema
        bear_trend = self.close < ema
        bull_mom = rsi >= self.rsi_bull
        bear_mom = rsi <= self.rsi_bear
        long_signal = in_session and bull_trend and near_ema and bull_mom
        short_signal = in_session and bear_trend and near_ema and bear_mom
        st = self.strategy
        if long_signal and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_signal and st.position_size >= 0:
            st.entry("Short", st.short)
        avg = st.position_avg_price
        st.exit("Long Exit", from_entry="Long", stop=avg - (atr * self.stop_atr), limit=avg + (atr * self.target_atr))
        st.exit("Short Exit", from_entry="Short", stop=avg + (atr * self.stop_atr), limit=avg - (atr * self.target_atr))
        in_trade = st.position_size != 0
        if in_trade:
            self.bars_in_trade += 1
        else:
            self.bars_in_trade = 0
        if self.use_time_exit and in_trade and self.bars_in_trade >= self.max_bars_in_trade:
            st.close("Long" if st.position_size > 0 else "Short", comment="Time Exit")
        self.plot(ema, "EMA", linewidth=2)
