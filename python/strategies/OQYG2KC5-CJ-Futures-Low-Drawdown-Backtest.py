"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CJ Futures Low-Drawdown Backtest
Author       : euealbule30
Source URL   : https://www.tradingview.com/script/OQYG2KC5-CJ-Futures-Low-Drawdown-Backtest
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Trend filter: the 240-minute and 60-minute closes both on the same side of their own EMA50
(four request.security calls, lookahead off). In the 08:30-11:30 exchange-time session, with above-average volume, a
pullback to the chart EMA50 followed by a confirming candle (close beyond the open and the previous high / low) enters
when not already on that side; the stop is the 5-bar lowest low / highest high and the target is 2 R. Entry and exit are
issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the EMA plot and the BUY / SELL shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class CjFuturesLowDrawdown(Script):
    TITLE = "CJ Futures Low-Drawdown Backtest"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=0.5)
    SOURCE = {"id": "OQYG2KC5", "author": "euealbule30", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OQYG2KC5-CJ-Futures-Low-Drawdown-Backtest"}

    def init(self):
        self.ema_length = self.input.int(50, "EMA Length")
        self.trend_tf = self.input.timeframe("240", "Trend Timeframe")
        self.setup_tf = self.input.timeframe("60", "Setup Timeframe")
        self.rr = self.input.float(2.0, "Risk Reward", step=0.1)
        self.swing_lookback = self.input.int(5, "Swing Lookback", minval=1)
        self.use_volume_filter = self.input.bool(True, "Use Volume Filter")
        self.volume_length = self.input.int(20, "Volume SMA Length")
        self.session_input = self.input.session("0830-1130", "Main Session")

    def on_bar(self):
        ema = ta.ema(self.close, self.ema_length)
        trend_close = self.security(self.syminfo.tickerid, self.trend_tf, lambda v: v.close)
        trend_ema = self.security(self.syminfo.tickerid, self.trend_tf, lambda v: ta.ema(v.close, self.ema_length))
        setup_close = self.security(self.syminfo.tickerid, self.setup_tf, lambda v: v.close)
        setup_ema = self.security(self.syminfo.tickerid, self.setup_tf, lambda v: ta.ema(v.close, self.ema_length))
        bull_trend = trend_close > trend_ema and setup_close > setup_ema
        bear_trend = trend_close < trend_ema and setup_close < setup_ema
        in_session = not na(self.time_fn(None, self.session_input))
        vol_sma = ta.sma(self.volume, self.volume_length)
        good_volume = (not self.use_volume_filter) or self.volume > vol_sma
        pullback_buy = self.low <= ema and bull_trend
        pullback_sell = self.high >= ema and bear_trend
        bull_confirm = self.close > self.open and self.close > self.high[1]
        bear_confirm = self.close < self.open and self.close < self.low[1]
        buy_signal = in_session and good_volume and pullback_buy and bull_confirm
        sell_signal = in_session and good_volume and pullback_sell and bear_confirm
        buy_sl = ta.lowest(self.low, self.swing_lookback)
        sell_sl = ta.highest(self.high, self.swing_lookback)
        buy_risk = self.close - buy_sl
        sell_risk = sell_sl - self.close
        buy_tp = self.close + (buy_risk * self.rr)
        sell_tp = self.close - (sell_risk * self.rr)
        st = self.strategy
        if buy_signal and buy_risk > 0 and st.position_size <= 0:
            st.entry("Buy", st.long)
            st.exit("Buy Exit", from_entry="Buy", stop=buy_sl, limit=buy_tp)
        if sell_signal and sell_risk > 0 and st.position_size >= 0:
            st.entry("Sell", st.short)
            st.exit("Sell Exit", from_entry="Sell", stop=sell_sl, limit=sell_tp)
        self.plot(ema, color=color.orange, title="EMA 50")
