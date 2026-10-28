"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 波段交易执行手册 v1 - BTC/ETH/SOL
Author       : txts0370
Source URL   : https://www.tradingview.com/script/SaSpHWMm
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long only: the daily close above the daily EMA20 and EMA50 with a positive daily MACD histogram (all
through request.security, lookahead off), a pullback of the chart close to EMA20 or the Bollinger basis, RSI(14) above 45 and a
positive/bullish chart MACD buys when flat. Entry and exit (stop 1.5 ATR below the close, target `rrRatio` times that distance)
are issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the EMA / basis plots, signal shape and info table (cosmetic). volumeConfirm is computed but unused in the original.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SwingTradingManual(Script):
    TITLE = "波段交易执行手册 v1 - BTC/ETH/SOL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=100000,
                    commission_type="percent", commission_value=0.1, pyramiding=0)
    SOURCE = {"id": "SaSpHWMm", "author": "txts0370", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SaSpHWMm"}

    def init(self):
        self.len_ema20 = self.input.int(20, "20 EMA", minval=1)
        self.len_ema50 = self.input.int(50, "50 EMA", minval=1)
        self.len_rsi = self.input.int(14, "RSI 长度")
        self.len_macd_fast = self.input.int(12, "MACD 快线")
        self.len_macd_signal = self.input.int(26, "MACD 慢线")
        self.len_bb = self.input.int(20, "布林带长度")
        self.mult_bb = self.input.float(2.0, "布林带倍数")
        self.atr_len = self.input.int(14, "ATR 长度")
        self.rr_ratio = self.input.float(2.0, "盈亏比", minval=1.5, step=0.1)
        self.risk_percent = self.input.float(1.0, "单笔风险 %", minval=0.5, maxval=2.0)

    def on_bar(self):
        ema20 = ta.ema(self.close, self.len_ema20)
        ema50 = ta.ema(self.close, self.len_ema50)
        rsi = ta.rsi(self.close, self.len_rsi)
        macd_line, signal_line, hist = ta.macd(self.close, self.len_macd_fast, self.len_macd_signal, 9)
        bb_middle, bb_upper, bb_lower = ta.bb(self.close, self.len_bb, self.mult_bb)
        atr = ta.atr(self.atr_len)
        daily_close = self.security(None, "D", lambda v: v.close)
        daily_ema20 = self.security(None, "D", lambda v: ta.ema(v.close, self.len_ema20))
        daily_ema50 = self.security(None, "D", lambda v: ta.ema(v.close, self.len_ema50))
        daily_macd_line, daily_signal_line, daily_hist = self.security(
            None, "D", lambda v: ta.macd(v.close, self.len_macd_fast, self.len_macd_signal, 9))
        daily_bullish = daily_close > daily_ema20 and daily_close > daily_ema50 and daily_hist > 0
        pullback_to_support = self.close <= ema20 or self.close <= bb_middle
        rsi_condition = rsi > 45
        macd_bullish = hist > 0 or (macd_line > signal_line)
        long_condition = daily_bullish and pullback_to_support and rsi_condition and macd_bullish
        long_stop = self.close - atr * 1.5
        long_tp = self.close + (self.close - long_stop) * self.rr_ratio
        st = self.strategy
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=long_stop, limit=long_tp)
        self.plot(ema20, color=color.orange, linewidth=2, title="20 EMA")
        self.plot(ema50, color=color.blue, linewidth=2, title="50 EMA")
        self.plot(bb_middle, color=color.gray, linewidth=1, title="布林中轨")
