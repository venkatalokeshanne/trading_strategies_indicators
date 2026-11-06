"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMC ICT Backtest XAUUSD + MNQ
Author       : shary890
Source URL   : https://www.tradingview.com/script/QpR7OWpA-SMC-ICT-Backtest-XAUUSD-MNQ
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. process_orders_on_close=true: entries fill at the signal bar's close and the
bracket (stop = signal bar low/high, target = rr * risk) works from the next bar. ta.pivothigh/pivotlow
(5, 5) report a pivot five bars after its centre, so lastHigh/lastLow only ever use confirmed pivots. The
session windows are read in the symbol's exchange time zone.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class SmcIctBacktest(Script):
    TITLE = "SMC ICT Backtest XAUUSD + MNQ"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.01, pyramiding=0,
                    process_orders_on_close=True)
    SOURCE = {"id": "QpR7OWpA", "author": "shary890", "licence": "not stated",
              "url": "https://www.tradingview.com/script/QpR7OWpA-SMC-ICT-Backtest-XAUUSD-MNQ"}

    def init(self):
        self.swing_len = self.input.int(5, "Swing Length")
        self.rr = self.input.float(2.0, "Risk Reward", step=0.5)
        self.last_high = NA
        self.last_low = NA

    def on_bar(self):
        london = not na(self.time_fn(None, "0700-1000"))
        new_york = not na(self.time_fn(None, "1230-1600"))
        trade_session = london or new_york
        ph = ta.pivothigh(self.high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(self.low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_high = ph
        if not na(pl):
            self.last_low = pl
        bull_sweep = not na(self.last_low) and self.low < self.last_low and self.close > self.last_low
        bear_sweep = not na(self.last_high) and self.high > self.last_high and self.close < self.last_high
        bull_mss = bull_sweep and self.close > self.high[1]
        bear_mss = bear_sweep and self.close < self.low[1]
        bull_fvg = self.low > self.high[2]
        bear_fvg = self.high < self.low[2]
        buy = trade_session and bull_mss and bull_fvg
        sell = trade_session and bear_mss and bear_fvg
        buy_sl = self.low
        sell_sl = self.high
        buy_risk = self.close - buy_sl
        sell_risk = sell_sl - self.close
        buy_tp = self.close + (buy_risk * self.rr)
        sell_tp = self.close - (sell_risk * self.rr)
        st = self.strategy
        if buy:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", "BUY", stop=buy_sl, limit=buy_tp)
        if sell:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", "SELL", stop=sell_sl, limit=sell_tp)
        self.plotshape(buy)
        self.plotshape(sell)
