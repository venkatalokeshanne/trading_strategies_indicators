"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MES Scalperino
Author       : public_username_twice
Source URL   : https://www.tradingview.com/script/o0DUiYSC-MES-Scalperino
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A selectable crossover / oscillator-extreme / trend-state signal (long only, short only, or both with optional reversal) inside an Eastern-time session window is acted on one bar after it fires (the source reads `signal[1]`): a market entry with a fixed point take-profit and stop-loss in ticks from the fill price. A position is also closed on a gap between bars longer than the set minutes (session gaps) or after a maximum number of bars from the order bar.

Deviations from the original: none.
Not carried over: TP / SL lines and signal markers (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, ta


class MesScalperino(Script):
    TITLE = "MES Scalperino"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2500000, default_qty_type="fixed", default_qty_value=4, pyramiding=0, commission_type="cash_per_contract",
                    commission_value=0.624, slippage=0, process_orders_on_close=False)
    SOURCE = {"id": "o0DUiYSC", "author": "public_username_twice", "licence": "not stated",
              "url": "https://www.tradingview.com/script/o0DUiYSC-MES-Scalperino"}

    def init(self):
        i = self.input
        self.trade_direction = i.string("Long Only", "Direction", group="Direction", options=["Long Only", "Short Only", "Both"])
        self.long_signal = i.string("SMA(20) x> SMA(50)", "Long Signal", group="Long Signal", options=[
            "SMA(20) x> SMA(50)", "EMA(50) x> EMA(100)", "RSI(9) <20", "RSI(14) <25", "RSI(14) <20", "SMA(50) > SMA(200)", "EMA(50) > EMA(100)",
            "All Crossovers Up", "All RSI Oversold"])
        self.short_signal = i.string("SMA(20) x< SMA(50)", "Short Signal", group="Short Signal", options=[
            "SMA(20) x< SMA(50)", "EMA(50) x< EMA(100)", "RSI(9) >80", "RSI(14) >75", "RSI(14) >80", "SMA(50) < SMA(200)", "EMA(50) < EMA(100)",
            "All Crossovers Down", "All RSI Overbought"])
        self.both_signal = i.string("SMA(20)/SMA(50) Cross", "Both Signal", group="Both Signal", options=[
            "SMA(20)/SMA(50) Cross", "EMA(50)/EMA(100) Cross", "RSI(9) Extremes", "RSI(14) 25/75", "RSI(14) 20/80", "SMA(50)/SMA(200) State",
            "EMA(50)/EMA(100) State", "All Crossovers", "All RSI"])
        self.allow_reversal = i.bool(False, "Allow Reversal", group="Both Signal")
        g = "Risk"
        self.tp_points = i.float(1.5, "Take Profit (points)", minval=0.25, step=0.25, group=g)
        self.sl_points = i.float(50.0, "Stop Loss (points)", minval=1.0, step=5.0, group=g)
        self.max_hold_bars = i.int(480, "Max Hold (bars)", minval=10, step=10, group=g)
        self.gap_exit_min = i.int(120, "Session Gap Exit (minutes)", minval=0, step=30, group=g)
        g = "Session"
        self.session_filter = i.string("Evening ETH 18-01", "Session Filter", group=g,
                                       options=["No Filter", "RTH 9:30-16:00", "Core RTH 10-15", "Evening ETH 18-01", "Full ETH (outside RTH)", "Custom"])
        self.custom_start = i.int(18, "Custom Session Start (hour ET)", minval=0, maxval=23, group=g)
        self.custom_end = i.int(1, "Custom Session End (hour ET)", minval=0, maxval=23, group=g)
        self.long_fired = False
        self.short_fired = False
        self.entry_bar = None

    @staticmethod
    def in_window(h, s, e):
        return (h >= s and h < e) if s <= e else (h >= s or h < e)

    def on_bar(self):
        st = self.strategy
        close = self.close
        mintick = self.syminfo.mintick
        h = self.hour(self.time, "America/New_York")
        sf = self.session_filter
        if sf == "No Filter":
            session_allowed = True
        elif sf == "RTH 9:30-16:00":
            session_allowed = h >= 9 and h < 16
        elif sf == "Core RTH 10-15":
            session_allowed = h >= 10 and h < 15
        elif sf == "Evening ETH 18-01":
            session_allowed = self.in_window(h, 18, 1)
        elif sf == "Full ETH (outside RTH)":
            session_allowed = h < 9 or h >= 16
        elif sf == "Custom":
            session_allowed = self.in_window(h, self.custom_start, self.custom_end)
        else:
            session_allowed = True
        sma20, sma50, sma200 = ta.sma(close, 20), ta.sma(close, 50), ta.sma(close, 200)
        ema50, ema100 = ta.ema(close, 50), ta.ema(close, 100)
        rsi9, rsi14 = ta.rsi(close, 9), ta.rsi(close, 14)
        x_up_sma, x_up_ema = ta.crossover(sma20, sma50), ta.crossover(ema50, ema100)
        x_dn_sma, x_dn_ema = ta.crossunder(sma20, sma50), ta.crossunder(ema50, ema100)
        sma_cross_over = x_up_sma and not na(sma50)
        ema_cross_over = x_up_ema
        sma_cross_under = x_dn_sma and not na(sma50)
        ema_cross_under = x_dn_ema
        rsi9_oversold = rsi9 < 20 and not na(rsi9)
        rsi14_under25 = rsi14 < 25 and not na(rsi14)
        rsi14_under20 = rsi14 < 20 and not na(rsi14)
        rsi9_overbought = rsi9 > 80 and not na(rsi9)
        rsi14_over75 = rsi14 > 75 and not na(rsi14)
        rsi14_over80 = rsi14 > 80 and not na(rsi14)
        sma_state_bull = sma50 > sma200 and not na(sma200)
        ema_state_bull = ema50 > ema100
        sma_state_bear = sma50 < sma200 and not na(sma200)
        ema_state_bear = ema50 < ema100
        long_map = {"SMA(20) x> SMA(50)": sma_cross_over, "EMA(50) x> EMA(100)": ema_cross_over, "RSI(9) <20": rsi9_oversold,
                    "RSI(14) <25": rsi14_under25, "RSI(14) <20": rsi14_under20, "SMA(50) > SMA(200)": sma_state_bull,
                    "EMA(50) > EMA(100)": ema_state_bull, "All Crossovers Up": sma_cross_over or ema_cross_over,
                    "All RSI Oversold": rsi9_oversold or rsi14_under25}
        short_map = {"SMA(20) x< SMA(50)": sma_cross_under, "EMA(50) x< EMA(100)": ema_cross_under, "RSI(9) >80": rsi9_overbought,
                     "RSI(14) >75": rsi14_over75, "RSI(14) >80": rsi14_over80, "SMA(50) < SMA(200)": sma_state_bear,
                     "EMA(50) < EMA(100)": ema_state_bear, "All Crossovers Down": sma_cross_under or ema_cross_under,
                     "All RSI Overbought": rsi9_overbought or rsi14_over75}
        both_long = {"SMA(20)/SMA(50) Cross": sma_cross_over, "EMA(50)/EMA(100) Cross": ema_cross_over, "RSI(9) Extremes": rsi9_oversold,
                     "RSI(14) 25/75": rsi14_under25, "RSI(14) 20/80": rsi14_under20, "SMA(50)/SMA(200) State": sma_state_bull,
                     "EMA(50)/EMA(100) State": ema_state_bull, "All Crossovers": sma_cross_over or ema_cross_over, "All RSI": rsi9_oversold or rsi14_under25}
        both_short = {"SMA(20)/SMA(50) Cross": sma_cross_under, "EMA(50)/EMA(100) Cross": ema_cross_under, "RSI(9) Extremes": rsi9_overbought,
                      "RSI(14) 25/75": rsi14_over75, "RSI(14) 20/80": rsi14_over80, "SMA(50)/SMA(200) State": sma_state_bear,
                      "EMA(50)/EMA(100) State": ema_state_bear, "All Crossovers": sma_cross_under or ema_cross_under, "All RSI": rsi9_overbought or rsi14_over75}
        long_prev, short_prev = self.long_fired, self.short_fired
        if self.trade_direction == "Long Only":
            self.long_fired = bool(long_map.get(self.long_signal, False))
            self.short_fired = False
        elif self.trade_direction == "Short Only":
            self.long_fired = False
            self.short_fired = bool(short_map.get(self.short_signal, False))
        else:
            self.long_fired = bool(both_long.get(self.both_signal, False))
            self.short_fired = bool(both_short.get(self.both_signal, False))
        can_reverse = self.trade_direction == "Both" and self.allow_reversal
        can_enter_long = st.position_size == 0 or (can_reverse and st.position_size < 0)
        can_enter_short = st.position_size == 0 or (can_reverse and st.position_size > 0)
        enter_long = long_prev and session_allowed and can_enter_long
        enter_short = short_prev and session_allowed and can_enter_short
        if enter_long:
            self.entry_bar = self.bar_index
            st.entry("Long", st.long)
            st.exit("TP/SL", "Long", profit=div(self.tp_points, mintick), loss=div(self.sl_points, mintick))
        if enter_short:
            self.entry_bar = self.bar_index
            st.entry("Short", st.short)
            st.exit("TP/SL", "Short", profit=div(self.tp_points, mintick), loss=div(self.sl_points, mintick))
        bar_gap_minutes = (self.time - self.time[1]) / 60000
        is_session_gap = self.gap_exit_min > 0 and bar_gap_minutes > self.gap_exit_min
        if st.position_size != 0 and self.entry_bar is not None:
            bars_held = self.bar_index - self.entry_bar
            exit_id = "Long" if st.position_size > 0 else "Short"
            if is_session_gap:
                st.close(exit_id, comment="Gap Exit")
            elif bars_held >= self.max_hold_bars:
                st.close(exit_id, comment="Time Exit")
