"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TMO Dual Timeframe Strategy [Hary]
Author       : Inspire_Algos
Source URL   : https://www.tradingview.com/script/xm1plELH-TMO-Dual-Timeframe-Strategy-Hary
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The TMO oscillator (the count of the last `length`+1 opens the close is above minus those it is below, smoothed by three configurable moving averages into main and signal lines) is computed with request.security on a higher "trend" timeframe and on an "entry" timeframe (lookahead off). A long (short) is opened when the trend timeframe's main line is positive (negative) and the entry timeframe's main line crosses above (below) zero; the opposite signal also closes the trade. Percent / pip stop and target are issued from the average price while the trade is open.
Deviations from the original: none.
Not carried over: the oscillator lines, bands and TP / SL level plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta

TF_MAP = {"1m": "1", "3m": "3", "5m": "5", "8m": "8", "10m": "10", "15m": "15", "30m": "30", "1hr": "60", "2hr": "120", "4hr": "240", "6hr": "360",
          "12hr": "720", "1D": "D", "2D": "2D", "1W": "W"}


class TmoDualTimeframe(Script):
    TITLE = "TMO Dual Timeframe Strategy [Hary]"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.05, slippage=1)
    SOURCE = {"id": "xm1plELH", "author": "Inspire_Algos", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xm1plELH-TMO-Dual-Timeframe-Strategy-Hary"}

    def init(self):
        i = self.input
        labels = ["1m", "3m", "5m", "8m", "10m", "15m", "30m", "1hr", "2hr", "4hr", "6hr", "12hr", "1D", "2D", "1W"]
        g = "Timeframes"
        self.htm_tf = TF_MAP.get(i.string("1hr", "HTM - Higher Timeframe (trend)", options=labels, group=g), "60")
        self.etm_tf = TF_MAP.get(i.string("3m", "ETM - Entry Timeframe (trigger)", options=labels, group=g), "60")
        g = "TMO Settings"
        self.length = i.int(14, "Length", minval=1, group=g)
        self.calc_len = i.int(5, "Calc length", minval=1, group=g)
        self.smooth_len = i.int(3, "Smooth length", minval=1, group=g)
        self.len_type = i.string("EMA", "Length MA type", options=["EMA", "SMA", "RMA"], group=g)
        self.calc_type = i.string("EMA", "Calc length MA type", options=["EMA", "SMA", "RMA"], group=g)
        self.smooth_type = i.string("EMA", "Smooth length MA type", options=["EMA", "SMA", "RMA"], group=g)
        g = "Display"
        i.bool(True, "Show HTM line", group=g)
        i.bool(True, "Show ETM line", group=g)
        i.bool(True, "Show OB/OS + upper/lower bands", group=g)
        g = "Strategy"
        self.allow_long = i.bool(True, "Allow long trades", group=g)
        self.allow_short = i.bool(True, "Allow short trades", group=g)
        g = "TP / SL"
        i.bool(True, "Show TP/SL lines on chart", group=g)
        self.use_sl = i.bool(True, "Use stop loss", group=g)
        self.sl_unit = i.string("Percent", "Stop loss unit", options=["Percent", "Pips"], group=g)
        self.sl_amount = i.float(2.0, "Stop loss amount", minval=0.0, step=0.1, group=g)
        self.use_tp = i.bool(True, "Use take profit", group=g)
        self.tp_unit = i.string("Percent", "Take profit unit", options=["Percent", "Pips"], group=g)
        self.tp_amount = i.float(4.0, "Take profit amount", minval=0.0, step=0.1, group=g)
        self.pip_size = i.float(10, "Ticks per pip", minval=0.0001, step=1, group=g)
        g = "Backtest window"
        self.start_date = i.time(self.timestamp(2020, 1, 1, 0, 0, 0), "Start date", group=g)
        self.end_date = i.time(self.timestamp(2099, 1, 1, 0, 0, 0), "End date", group=g)

    def _ma(self, ma_type, src, length):
        if ma_type == "EMA":
            return ta.ema(src, length)
        if ma_type == "SMA":
            return ta.sma(src, length)
        return ta.rma(src, length)

    def _tmo(self, v):
        s = 0.0
        for k in range(self.length + 1):
            o_k = v.open[k]
            s = s + (1 if v.close > o_k else (-1 if v.close < o_k else 0))
        ma = self._ma(self.len_type, s, self.calc_len)
        main = self._ma(self.calc_type, ma, self.smooth_len)
        signal = self._ma(self.smooth_type, main, self.smooth_len)
        return main, signal

    def on_bar(self):
        st = self.strategy
        in_window = self.time >= self.start_date and self.time <= self.end_date
        htm_main, htm_signal = self.security(None, self.htm_tf, lambda v: self._tmo(v), lookahead=False)
        etm_main, etm_signal = self.security(None, self.etm_tf, lambda v: self._tmo(v), lookahead=False)
        htm_bull = htm_main > 0
        htm_bear = htm_main < 0
        etm_up = ta.crossover(etm_main, 0)
        etm_dn = ta.crossunder(etm_main, 0)
        buy_signal = htm_bull and etm_up
        sell_signal = htm_bear and etm_dn
        long_cond = buy_signal and self.allow_long and in_window
        short_cond = sell_signal and self.allow_short and in_window
        if long_cond:
            st.entry("Long", st.long)
        if short_cond:
            st.entry("Short", st.short)
        if sell_signal and self.allow_long:
            st.close("Long")
        if buy_signal and self.allow_short:
            st.close("Short")
        pip_value = self.syminfo.mintick * self.pip_size

        def dist(amount, unit, price):
            return price * amount / 100 if unit == "Percent" else amount * pip_value

        in_long = st.position_size > 0
        in_short = st.position_size < 0
        avg = st.position_avg_price
        sl_dist = dist(self.sl_amount, self.sl_unit, avg)
        tp_dist = dist(self.tp_amount, self.tp_unit, avg)
        long_sl = avg - sl_dist if (self.use_sl and in_long) else NA
        long_tp = avg + tp_dist if (self.use_tp and in_long) else NA
        short_sl = avg + sl_dist if (self.use_sl and in_short) else NA
        short_tp = avg - tp_dist if (self.use_tp and in_short) else NA
        if in_long and (self.use_sl or self.use_tp):
            st.exit("Long Exit", "Long", stop=long_sl, limit=long_tp)
        if in_short and (self.use_sl or self.use_tp):
            st.exit("Short Exit", "Short", stop=short_sl, limit=short_tp)
