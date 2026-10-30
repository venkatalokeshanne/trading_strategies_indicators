"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Night Breakout 21:30 WIB v12
Author       : rsaktio
Source URL   : https://www.tradingview.com/script/dW9UeMTL-RamigoniStrategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Only on the bar that starts at 21:15 Jakarta time: in an EMA50 > EMA200 uptrend with the close above
EMA50, two green candles in a row and a low above EMA200 on both, a long is taken when flat (the mirror image for a short). The
stop is the lowest low (highest high) of the last 20 bars, capped at max_sl_pips * pip_value (500 x 0.1 = 50 points) from the
close, and the target is 1:1; the quantity (risk / stop distance in 0.01 lots x multiplier) never moves prices. Entry and
strategy.exit are issued together on the signal bar, so the bracket also works on the fill bar. A position older than 5 days is
closed at the next open.

Deviations from the original: none.
Not carried over: the EMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath, ta

TZ = "Asia/Jakarta"


class NightBreakout(Script):
    TITLE = "Night Breakout 21:30 WIB v12"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "dW9UeMTL", "author": "rsaktio", "licence": "not stated",
              "url": "https://www.tradingview.com/script/dW9UeMTL-RamigoniStrategy"}

    def init(self):
        self.target_risk_usd = self.input.float(100.0, title="Target Risiko Terdekat (USD)")
        self.lot_step = self.input.float(0.01, title="Step Lot Broker (Contoh: 0.01)", step=0.01)
        self.max_sl_pips = self.input.int(500, title="Maksimal SL (Pips)")
        self.pip_value = self.input.float(0.1, title="Nilai 1 Pip (XAUUSD = 0.1)")
        self.lookback_sr = self.input.int(20, title="Jumlah Candle Cek Support/Resistance")
        self.tv_multiplier = self.input.float(100.0, title="Pengali Unit Broker (Forex = 100)")
        self.sl_price = NA
        self.tp_price = NA

    def on_bar(self):
        ema50 = ta.ema(self.close, 50)
        ema200 = ta.ema(self.close, 200)
        ema200_h = self.H("e200")
        e200_prev = ema200_h[1]
        ema200_h.set(ema200)
        is_entry_time = self.hour(self.time, TZ) == 21 and self.minute(self.time, TZ) == 15
        uptrend_valid = (ema50 > ema200) and (self.close > ema50)
        bullish_candles = (self.close > self.open) and (self.close[1] > self.open[1])
        no_touch_ema200_buy = (self.low > ema200) and (self.low[1] > e200_prev)
        long_cond = is_entry_time and uptrend_valid and bullish_candles and no_touch_ema200_buy
        downtrend_valid = (ema50 < ema200) and (self.close < ema50)
        bearish_candles = (self.close < self.open) and (self.close[1] < self.open[1])
        no_touch_ema200_sell = (self.high < ema200) and (self.high[1] < e200_prev)
        short_cond = is_entry_time and downtrend_valid and bearish_candles and no_touch_ema200_sell
        recent_low = ta.lowest(self.low, self.lookback_sr)
        recent_high = ta.highest(self.high, self.lookback_sr)
        max_sl_dist = self.max_sl_pips * self.pip_value
        st = self.strategy
        if long_cond and st.position_size == 0:
            jarak_sl = self.close - recent_low
            self.sl_price = self.close - max_sl_dist if jarak_sl > max_sl_dist else recent_low
            self.tp_price = self.close + (self.close - self.sl_price)
            sl_distance_point = self.close - self.sl_price
            sl_distance_pips = div(sl_distance_point, self.pip_value)
            loss_per_01_lot = sl_distance_pips * 0.1
            if loss_per_01_lot > 0:
                multiplier = div(self.target_risk_usd, loss_per_01_lot)
                pos_qty = pmath.ceil(multiplier - 0.00001) * self.lot_step
                st.entry("Buy", st.long, qty=pos_qty * self.tv_multiplier)
                st.exit("Exit Buy", "Buy", stop=self.sl_price, limit=self.tp_price)
        if short_cond and st.position_size == 0:
            jarak_sl = recent_high - self.close
            self.sl_price = self.close + max_sl_dist if jarak_sl > max_sl_dist else recent_high
            self.tp_price = self.close - (self.sl_price - self.close)
            sl_distance_point = self.sl_price - self.close
            sl_distance_pips = div(sl_distance_point, self.pip_value)
            loss_per_01_lot = sl_distance_pips * 0.1
            if loss_per_01_lot > 0:
                multiplier = div(self.target_risk_usd, loss_per_01_lot)
                pos_qty = pmath.ceil(multiplier - 0.00001) * self.lot_step
                st.entry("Sell", st.short, qty=pos_qty * self.tv_multiplier)
                st.exit("Exit Sell", "Sell", stop=self.sl_price, limit=self.tp_price)
        if st.position_size != 0:
            trade_open_time = st.opentrades_entry_time(0)
            waktu_berjalan = self.time - trade_open_time
            if waktu_berjalan >= 432000000:
                st.close_all(comment="Batal (Lewat 5 Hari)")
        self.plot(ema50, color=color.blue, title="EMA 50", linewidth=2)
        self.plot(ema200, color=color.red, title="EMA 200", linewidth=2)
