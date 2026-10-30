"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD RSI Long + Short Backtest
Author       : sujonabushaid
Source URL   : https://www.tradingview.com/script/aovTOo6I-XAUUSD-RSI-Long-Short-Backtest
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The RSI of the chosen timeframe (lookahead off) below the buy level opens a long (above the short level, a short) when flat; the trade
quantity is lots x ounces per lot, and a fixed dollar take-profit / stop-loss converts to a price move per ounce around the average price while in a position.

Deviations from the original: none.
Not carried over: the signal labels, the TP / SL / entry lines, the background shading and the PnL table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class XauusdRsiLongShort(Script):
    TITLE = "XAUUSD RSI Long + Short Backtest"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="fixed", default_qty_value=2, initial_capital=10000)
    SOURCE = {"id": "aovTOo6I", "author": "sujonabushaid", "licence": "not stated",
              "url": "https://www.tradingview.com/script/aovTOo6I-XAUUSD-RSI-Long-Short-Backtest"}

    def init(self):
        self.rsi_timeframe = self.input.timeframe("5", "RSI Timeframe")
        self.rsi_length = self.input.int(14, "RSI Length", minval=1)
        self.long_rsi_level = self.input.float(29.0, "Buy When RSI Below", step=0.1)
        self.short_rsi_level = self.input.float(71.0, "Short When RSI Above", step=0.1)
        self.enable_long = self.input.bool(True, "Enable Buy Trades")
        self.enable_short = self.input.bool(True, "Enable Short Trades")
        self.lot_size = self.input.float(0.02, "Lot Size", step=0.01)
        self.ounces_per_lot = self.input.float(100.0, "Ounces Per 1 Lot", step=1)
        self.take_profit_usd = self.input.float(20.0, "Take Profit USD", step=1)
        self.stop_loss_usd = self.input.float(20.0, "Stop Loss USD", step=1)

    def on_bar(self):
        trade_qty = self.lot_size * self.ounces_per_lot
        rsi_len = self.rsi_length
        rsi_value = self.security(None, self.rsi_timeframe, lambda v: ta.rsi(v.close, rsi_len), lookahead=False)
        tp_move = div(self.take_profit_usd, trade_qty)
        sl_move = div(self.stop_loss_usd, trade_qty)
        st = self.strategy
        long_condition = self.enable_long and rsi_value < self.long_rsi_level and st.position_size == 0
        short_condition = self.enable_short and rsi_value > self.short_rsi_level and st.position_size == 0
        if long_condition:
            st.entry("Buy", st.long, qty=trade_qty)
        if short_condition:
            st.entry("Short", st.short, qty=trade_qty)
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Buy TP / SL", from_entry="Buy", limit=avg + tp_move, stop=avg - sl_move)
        if st.position_size < 0:
            st.exit("Short TP / SL", from_entry="Short", limit=avg - tp_move, stop=avg + sl_move)
        self.plot(avg + tp_move if st.position_size > 0 else (avg - tp_move if st.position_size < 0 else NA), "Take Profit", color=color.green, linewidth=2)
        self.plot(avg - sl_move if st.position_size > 0 else (avg + sl_move if st.position_size < 0 else NA), "Stop Loss", color=color.red, linewidth=2)
