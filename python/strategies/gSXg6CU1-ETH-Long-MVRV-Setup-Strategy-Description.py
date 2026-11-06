"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ETH Long | MVRV Setup
Author       : Crypto_Andy_
Source URL   : https://www.tradingview.com/script/gSXg6CU1-ETH-Long-MVRV-Setup-Strategy-Description
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: the entry fills at the signal bar's close). While flat, a close inside the entry zone (1800 - 1950, and above 1800) with the 21 EMA above the 55 EMA, the RSI between 45 and 70 and a volume above its 20-bar average
enters long and issues three exit orders from that entry: 40 % at TP1 (2245), 35 % at TP2 (2650) and 25 % at TP3 (3000), each with the same stop-loss level (1680).
Deviations from the original: none (the 200 EMA is computed but unused in the source and is dropped).
Not carried over: the information table and plots / level lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class EthLongMvrvSetup(Script):
    TITLE = "ETH Long | MVRV Setup"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, process_orders_on_close=True)
    SOURCE = {"id": "gSXg6CU1", "author": "Crypto_Andy_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gSXg6CU1-ETH-Long-MVRV-Setup-Strategy-Description"}

    def init(self):
        i = self.input
        self.entry_zone_low = i.float(1800.0, "Entry Zone - Lower Bound")
        self.entry_zone_high = i.float(1950.0, "Entry Zone - Upper Bound")
        self.sl_level = i.float(1680.0, "Stop Loss")
        self.tp1_level = i.float(2245.0, "TP1 — Realized Price")
        self.tp2_level = i.float(2650.0, "TP2 — Intermediate Target")
        self.tp3_level = i.float(3000.0, "TP3 — Final Target")

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema21 = ta.ema(close, 21)
        ema55 = ta.ema(close, 55)
        rsi = ta.rsi(close, 14)
        vol_ma = ta.sma(self.volume, 20)
        long_condition = (close >= self.entry_zone_low and close <= self.entry_zone_high and ema21 > ema55 and close > 1800.0
                          and rsi > 45 and rsi < 70 and self.volume > vol_ma and st.position_size == 0)
        if long_condition:
            st.entry("ETH Long", st.long)
            st.exit("TP1", "ETH Long", qty_percent=40, limit=self.tp1_level, stop=self.sl_level)
            st.exit("TP2", "ETH Long", qty_percent=35, limit=self.tp2_level, stop=self.sl_level)
            st.exit("TP3", "ETH Long", qty_percent=25, limit=self.tp3_level, stop=self.sl_level)
