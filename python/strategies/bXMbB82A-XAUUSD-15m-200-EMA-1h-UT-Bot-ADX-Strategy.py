"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD 15m - 200 EMA (1h) + UT Bot + ADX Strategy
Author       : r2keymoneymind
Source URL   : https://www.tradingview.com/script/bXMbB82A-XAUUSD-15m-200-EMA-1h-UT-Bot-ADX-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A UT Bot buy flip (ATR(1) x 2 trailing stop, previous state short) with the close above the 1h EMA200 (request.security,
lookahead off) and ADX above 25 goes long; the take profit (+1.5%) and stop (-1%) are fixed on the signal bar. The trailing stop and the
flip state are kept bar to bar exactly as the source reads xTrailingStop[1] and pos[1].

Deviations from the original: none.
Not carried over: the info table and signal shape (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class UtBotAdx(Script):
    TITLE = "XAUUSD 15m - 200 EMA (1h) + UT Bot + ADX Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "bXMbB82A", "author": "r2keymoneymind", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bXMbB82A-XAUUSD-15m-200-EMA-1h-UT-Bot-ADX-Strategy"}

    def init(self):
        self.key_value = self.input.float(2.0, "UT Bot Key Value")
        self.atr_period = self.input.int(1, "UT Bot ATR Period")
        self.adx_len = self.input.int(14, "ADX Smoothing")
        self.di_len = self.input.int(14, "DI Length")
        self.adx_thresh = self.input.int(25, "ADX Minimum Level")
        self.ema_period = self.input.int(200, "HTF EMA Period")
        self.htf_time = self.input.string("60", "HTF Timeframe (60 = 1 Hour)")
        self.tp_pct = self.input.float(1.5, "Take Profit (%)") / 100
        self.sl_pct = self.input.float(1.0, "Stop Loss (%)") / 100
        self.prev_xts = NA
        self.prev_close = NA
        self.pos = 0

    def on_bar(self):
        htf_ema = self.security(None, self.htf_time, lambda v: ta.ema(v.close, self.ema_period))
        di_plus, di_minus, adx_value = ta.dmi(self.di_len, self.adx_len)
        x_atr = ta.atr(self.atr_period)
        n_loss = self.key_value * x_atr
        c = float(self.close)
        xts1 = self.prev_xts
        c1 = self.prev_close
        xts = pmath.max(c - n_loss, 0.0)
        if c1 > xts1 and c > xts1:
            xts = pmath.max(xts1, c - n_loss)
        elif c1 < xts1 and c < xts1:
            xts = pmath.min(xts1, c + n_loss)
        else:
            xts = c - n_loss if c > xts1 else c + n_loss
        pos1 = self.pos
        if c > xts1 and c1 <= xts1:
            self.pos = 1
        elif c < xts1 and c1 >= xts1:
            self.pos = -1
        ut_bot_buy = self.pos == 1 and pos1 == -1
        htf_trend_bullish = self.close > htf_ema
        buy_condition = ut_bot_buy and htf_trend_bullish and (adx_value > self.adx_thresh)
        st = self.strategy
        if buy_condition:
            st.entry("Buy", st.long)
            st.exit("Exit Buy", "Buy", limit=self.close * (1 + self.tp_pct), stop=self.close * (1 - self.sl_pct))
        self.prev_xts = xts
        self.prev_close = c
        self.plot(htf_ema, "1H 200 EMA", color=color.orange, linewidth=2)
