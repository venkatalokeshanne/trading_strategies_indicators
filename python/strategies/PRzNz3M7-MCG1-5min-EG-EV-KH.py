"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ECV Strategy v2 – MGC1! Futures
Author       : kaihershy
Source URL   : https://www.tradingview.com/script/PRzNz3M7-MCG1-5min-EG-EV-KH
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). An engulfing-style candle (a bar that takes both the previous high and low and closes above the previous open) with volume 1.3 x the previous bar's, on the right side of the 50 EMA, outside the cooldown after the last bar in a position, inside the Asian (20:00 - 03:00) or New York (09:30 - 16:00) window, enters 2 contracts
while the script's state is idle. The entry issues two exit orders of one contract each (take-profit 100 / 200 ticks, common 50-tick stop). Once the close reaches the entry plus the stop distance, a third order of one contract with a zero-tick stop (break-even) is added. The state returns to idle when the position is flat.
Deviations from the original: none.
Not carried over: the JSON alert, the information table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class EcvStrategyV2(Script):
    TITLE = "ECV Strategy v2 – MGC1! Futures"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=150000, default_qty_type="fixed", default_qty_value=2)
    SOURCE = {"id": "PRzNz3M7", "author": "kaihershy", "licence": "not stated", "url": "https://www.tradingview.com/script/PRzNz3M7-MCG1-5min-EG-EV-KH"}

    def init(self):
        i = self.input
        self.sl_ticks = i.int(50, "Stop Loss (Ticks)", group="Risk Management")
        self.tp1_ticks = i.int(100, "TP1 (Ticks)", group="Risk Management")
        self.tp2_ticks = i.int(200, "TP2 (Ticks)", group="Risk Management")
        self.ema_len = i.int(50, "EMA Length", group="Trend Filter")
        self.atr_len = i.int(14, "ATR Length", group="Volatility")
        self.cooldown_bars = i.int(15, "Cooldown Bars", group="Cooldown")
        self.bars_since_exit = 999
        self.entry_p = NA
        self.be_p = NA
        self.is_buy = False
        self.status = "IDLE"
        self.tp1_hit = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        tick = self.syminfo.mintick
        ema50 = ta.ema(close, self.ema_len)
        trend_bull = close > ema50
        trend_bear = close < ema50
        et_mins = self.hour(self.time, "America/New_York") * 60 + self.minute(self.time, "America/New_York")
        is_ny = et_mins >= 570 and et_mins < 960
        is_asia = et_mins >= 1200 or et_mins < 180
        session_ok = is_asia or is_ny
        self.bars_since_exit = 0 if st.position_size != 0 else self.bars_since_exit + 1
        cooldown_ok = self.bars_since_exit >= self.cooldown_bars
        bull_candle = close > open_ and high >= self.high[1] and low <= self.low[1] and close > self.open[1]
        bear_candle = close < open_ and high >= self.high[1] and low <= self.low[1] and close < self.open[1]
        vol_ok = self.volume > self.volume[1] * 1.3
        ecv_buy = bull_candle and vol_ok and trend_bull and cooldown_ok and session_ok
        ecv_sell = bear_candle and vol_ok and trend_bear and cooldown_ok and session_ok
        if (ecv_buy or ecv_sell) and self.status == "IDLE":
            self.is_buy = bool(ecv_buy)
            self.entry_p = float(close)
            self.be_p = self.entry_p + self.sl_ticks * tick if self.is_buy else self.entry_p - self.sl_ticks * tick
            self.status = "IN_TRADE"
            self.tp1_hit = False
            st.entry("ECV", st.long if self.is_buy else st.short, qty=2)
            st.exit("SL_TP1", "ECV", qty=1, profit=self.tp1_ticks, loss=self.sl_ticks)
            st.exit("SL_TP2", "ECV", qty=1, profit=self.tp2_ticks, loss=self.sl_ticks)
        if st.position_size != 0 and self.status == "IN_TRADE":
            if self.is_buy and close >= self.be_p and not self.tp1_hit:
                self.tp1_hit = True
                st.exit("BE", "ECV", qty=1, loss=0)
            if (not self.is_buy) and close <= self.be_p and not self.tp1_hit:
                self.tp1_hit = True
                st.exit("BE", "ECV", qty=1, loss=0)
        if st.position_size == 0 and self.status == "IN_TRADE":
            self.status = "IDLE"
            self.entry_p = NA
            self.be_p = NA
            self.tp1_hit = False
