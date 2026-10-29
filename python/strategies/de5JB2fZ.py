"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rangos Manipulados PRO EURUSD/GBPUSD [STRATEGY]
Author       : pacorodriguez_ber
Source URL   : https://www.tradingview.com/script/de5JB2fZ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). During the operating session (08:00 - 17:00 at Europe/Madrid), a 1-hour bar that swept the previous hour's low and closed back above it (request.security, lookahead off, so the value of an hour shows on its last chart bar), together with a chart bar that took out the previous bar's low and
closes up above the previous high ("Simple" mode, or a large-body candle near its high in the "Institucional" mode), buys while flat; sell is the mirror image. The entry carries its exit order: stop a pip buffer beyond the signal bar's extreme and a take-profit at the risk-reward multiple.
Deviations from the original: none.
Not carried over: the range boxes, labels and dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class RangosManipulados(Script):
    TITLE = "Rangos Manipulados PRO EURUSD/GBPUSD [STRATEGY]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "de5JB2fZ", "author": "pacorodriguez_ber", "licence": "not stated", "url": "https://www.tradingview.com/script/de5JB2fZ"}

    def init(self):
        i = self.input
        self.modo_entrada = i.string("Simple", "Tipo de Confirmación", options=["Simple", "Institucional"])
        self.rr = i.float(2.0, "Risk Reward", step=0.1)
        self.buffer_pips = i.float(4.0, "Buffer SL en pips")
        self.session_frankfurt = i.session("0800-1700", "Horario Operativo")

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        en_horario = self.time_in_session(self.session_frankfurt, "Europe/Madrid")
        pip = self.syminfo.mintick * 10
        buffer = self.buffer_pips * pip
        h1_high = self.security(None, "60", lambda v: v.high)
        h1_low = self.security(None, "60", lambda v: v.low)
        h1_close = self.security(None, "60", lambda v: v.close)
        h1_prev_high = self.security(None, "60", lambda v: v.high[1])
        h1_prev_low = self.security(None, "60", lambda v: v.low[1])
        h1_manip_buy = h1_low < h1_prev_low and h1_close > h1_prev_low
        h1_manip_sell = h1_high > h1_prev_high and h1_close < h1_prev_high
        prev_high = self.high[1]
        prev_low = self.low[1]
        sweep_buy = low < prev_low
        sweep_sell = high > prev_high
        simple_buy = close > open_ and close > self.high[1]
        simple_sell = close < open_ and close < self.low[1]
        body_size = abs(close - open_)
        full_range = high - low
        atr = ta.atr(14)
        inst_buy = close > open_ and body_size > full_range * 0.6 and full_range > atr * 0.8 and close >= high - (full_range * 0.2)
        inst_sell = close < open_ and body_size > full_range * 0.6 and full_range > atr * 0.8 and close <= low + (full_range * 0.2)
        confirm_buy = simple_buy if self.modo_entrada == "Simple" else inst_buy
        confirm_sell = simple_sell if self.modo_entrada == "Simple" else inst_sell
        buy_signal = en_horario and h1_manip_buy and sweep_buy and confirm_buy
        sell_signal = en_horario and h1_manip_sell and sweep_sell and confirm_sell
        buy_sl = low - buffer
        buy_risk = close - buy_sl
        buy_tp = close + (buy_risk * self.rr)
        sell_sl = high + buffer
        sell_risk = sell_sl - close
        sell_tp = close - (sell_risk * self.rr)
        if buy_signal and st.position_size == 0:
            st.entry("BUY", st.long)
            st.exit("BUY TP/SL", "BUY", stop=buy_sl, limit=buy_tp)
        if sell_signal and st.position_size == 0:
            st.entry("SELL", st.short)
            st.exit("SELL TP/SL", "SELL", stop=sell_sl, limit=sell_tp)
