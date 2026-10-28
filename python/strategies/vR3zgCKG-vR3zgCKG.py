"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RR Master - ระบบแจ้งเตือนภาษาไทย
Author       : louislapis9
Source URL   : https://www.tradingview.com/script/vR3zgCKG
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. After the start time, with an 8-bar cooldown since the last ENTRY (lastTradeBar is set only
when an order is placed), a long needs the low above EMA200, the close above the session VWAP of hlc3, ADX(14) > 30 and
rising over its SMA(7), and RSI(7) crossing over RSI(14) (short is the mirror). Entry and strategy.exit (stop = low -/+
buffer, limit = 1.7 R) are issued together on the signal bar when flat, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the alert() texts, the BUY / SELL labels and the EMA / VWAP plots (no effect on orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, pmath, ta

START_2026_0700 = 1767200400000      # timestamp("2026-01-01 00:00 +0700")


class RrMaster(Script):
    TITLE = "RR Master - ระบบแจ้งเตือนภาษาไทย"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "vR3zgCKG", "author": "louislapis9", "licence": "not stated",
              "url": "https://www.tradingview.com/script/vR3zgCKG"}

    def init(self):
        self.start_time = self.input.time(START_2026_0700, "วันที่เริ่มทดสอบ")
        self.trade_qty = self.input.float(1.0, "จำนวนสัญญา (Qty)")
        self.rr_ratio = self.input.float(1.7, "อัตรากำไรต่อขาดทุน (RR)")
        self.sl_buffer = self.input.float(2.0, "ระยะเผื่อ SL (2.0 = 200 จุดทอง)")
        self.min_bar_gap = self.input.int(8, "ระยะพักแท่งเทียน (Cooldown)")
        self.last_trade_bar = 0

    def on_bar(self):
        ema200 = ta.ema(self.close, 200)
        vwap_val = ta.vwap(self.hlc3)
        plus_di, minus_di, adx_val = ta.dmi(14, 14)
        rsi_fast = ta.rsi(self.close, 7)
        rsi_slow = ta.rsi(self.close, 14)
        adx_ma = ta.sma(adx_val, 7)
        is_adx_strong = adx_val > 30 and adx_val > adx_ma
        cross_up = ta.crossover(rsi_fast, rsi_slow)
        cross_dn = ta.crossunder(rsi_fast, rsi_slow)
        can_trade = (self.bar_index - self.last_trade_bar) >= self.min_bar_gap
        in_window = self.time >= self.start_time
        buy = in_window and can_trade and self.low > ema200 and self.close > vwap_val and is_adx_strong and cross_up
        sell = in_window and can_trade and self.high < ema200 and self.close < vwap_val and is_adx_strong and cross_dn
        st = self.strategy
        if buy and st.position_size == 0:
            sl = self.low - self.sl_buffer
            tp = self.close + (pmath.abs(self.close - sl) * self.rr_ratio)
            st.entry("Long", st.long, qty=self.trade_qty)
            st.exit("Exit", "Long", stop=sl, limit=tp)
            self.last_trade_bar = self.bar_index
        if sell and st.position_size == 0:
            sl = self.high + self.sl_buffer
            tp = self.close - (pmath.abs(sl - self.close) * self.rr_ratio)
            st.entry("Short", st.short, qty=self.trade_qty)
            st.exit("Exit", "Short", stop=sl, limit=tp)
            self.last_trade_bar = self.bar_index
        self.plot(ema200, color=color.yellow, title="เส้น EMA 200")
        self.plot(vwap_val, color=color.gray, title="เส้น VWAP")
