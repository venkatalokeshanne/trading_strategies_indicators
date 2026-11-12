"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : QQE Channel Strategy
Author       : Shiroi-
Source URL   : https://www.tradingview.com/script/c7V3XVUC
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A trend channel (EMAs of the high and low, 60 bars): the direction becomes +1 above the upper edge, -1 below the lower edge and otherwise keeps its last value; the channel exit line is the lower edge in an up-trend and the upper edge otherwise. A QQE momentum filter (smoothed RSI with a Wilder-smoothed ATR-of-RSI
band, factor 4.238) turns its own direction on band crossings. A long entry needs a channel flip to up with QQE bullish, or a QQE flip to bull inside a bullish channel (mirrored for shorts); the stop is the swing low / high over N bars and the target the risk multiple (optional fixed exit order); an exit signal (price crossing back through the channel line after a channel trend, or QQE turning against the position) closes at the next open.
Deviations from the original: none.
Not carried over: the channel fill, signal shapes and alert conditions (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, nz, pmath, ta


class QqeChannelStrategy(Script):
    TITLE = "QQE Channel Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05, slippage=2)
    SOURCE = {"id": "c7V3XVUC", "author": "Shiroi-", "licence": "not stated", "url": "https://www.tradingview.com/script/c7V3XVUC"}

    def init(self):
        i = self.input
        g = "📊 Trend Channel"
        self.ch_len = i.int(60, "Channel EMA Length", minval=1, group=g)
        g = "📈 Momentum Filter"
        self.rsi_len = i.int(14, "RSI Length", minval=1, group=g)
        self.rsi_smth = i.int(5, "RSI Smoothing (EMA)", minval=1, group=g)
        self.q_factor = i.float(4.238, "QQ Factor", minval=0.1, step=0.001, group=g)
        g = "🛡️  SL / TP"
        self.use_sltp = i.bool(True, "Use Fixed SL / TP", group=g)
        self.swing_len = i.int(10, "SL Swing Length (bars)", minval=1, group=g)
        self.rr_ratio = i.float(1.0, "Risk / Reward Ratio", minval=0.1, step=0.1, group=g)
        g = "⚙️  Strategy"
        self.use_long = i.bool(True, "Enable Long", group=g)
        self.use_short = i.bool(True, "Enable Short", group=g)
        self.lot_size = i.float(1.0, "Lot Size", minval=0.01, step=0.01, group=g)
        self.ch_dir = 0
        self.q_dir = 0
        self.l_band = NA
        self.s_band = NA
        self.l_band_2 = NA
        self.s_band_2 = NA
        self.rsi_sm_1 = NA
        self.prev_ch_bull = False
        self.prev_ch_bear = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        ch_high = ta.ema(high, self.ch_len)
        ch_low = ta.ema(low, self.ch_len)
        prev_ch_dir = self.ch_dir
        if close > ch_high:
            self.ch_dir = 1
        elif close < ch_low:
            self.ch_dir = -1
        ch_exit = ch_low if self.ch_dir >= 0 else ch_high
        ch_bull = self.ch_dir == 1
        ch_bear = self.ch_dir == -1
        ch_changed = ta.change(float(self.ch_dir)) != 0
        ch_flip_l = ch_changed and ch_bull
        ch_flip_s = ch_changed and ch_bear
        x_under = ta.crossunder(close, ch_exit)
        x_over = ta.crossover(close, ch_exit)
        exit_long = self.prev_ch_bull and x_under
        exit_short = self.prev_ch_bear and x_over
        self.prev_ch_bull, self.prev_ch_bear = bool(ch_bull), bool(ch_bear)
        rsi_val = ta.rsi(close, self.rsi_len)
        rsi_sm = ta.ema(rsi_val, self.rsi_smth)
        wilder_len = self.rsi_len * 2 - 1
        rsi_delta = abs(rsi_sm - nz(self.rsi_sm_1))
        rsi_atr1 = ta.ema(rsi_delta, wilder_len)
        dar = ta.ema(rsi_atr1, wilder_len) * self.q_factor
        l_band = rsi_sm - dar
        s_band = rsi_sm + dar
        l_prev = nz(self.l_band)
        s_prev = nz(self.s_band)
        l_band = pmath.max(l_band, l_prev) if rsi_sm > l_prev else l_band
        s_band = pmath.min(s_band, s_prev) if rsi_sm < s_prev else s_band
        prev_q = self.q_dir
        # crossover(rsiSm, sBand[1]) / crossunder(rsiSm, lBand[1]) compare with the bands one bar further back too
        x_up = rsi_sm > self.s_band and self.rsi_sm_1 <= self.s_band_2
        x_dn = rsi_sm < self.l_band and self.rsi_sm_1 >= self.l_band_2
        if x_up:
            self.q_dir = 1
        elif x_dn:
            self.q_dir = -1
        q_bull = self.q_dir == 1
        q_bear = self.q_dir == -1
        q_changed = self.q_dir != prev_q
        self.l_band_2, self.s_band_2 = self.l_band, self.s_band
        self.l_band, self.s_band = l_band, s_band
        self.rsi_sm_1 = float(rsi_sm)
        entry_long = (ch_flip_l and q_bull) or (q_changed and q_bull and ch_bull)
        entry_short = (ch_flip_s and q_bear) or (q_changed and q_bear and ch_bear)
        swing_low = ta.lowest(low, self.swing_len)
        swing_high = ta.highest(high, self.swing_len)
        exit_l = exit_long or (q_bear and st.position_size > 0)
        exit_s = exit_short or (q_bull and st.position_size < 0)
        if self.use_long:
            if entry_long:
                sl_price = swing_low
                risk = pmath.max(close - sl_price, self.syminfo.mintick)
                tp_price = close + risk * self.rr_ratio
                st.entry("Long", st.long, qty=self.lot_size)
                if self.use_sltp:
                    st.exit("Long SLTP", "Long", stop=sl_price, limit=tp_price, comment_loss="SL", comment_profit="TP")
            if exit_l:
                st.close("Long", comment="Signal Exit")
        if self.use_short:
            if entry_short:
                sl_price = swing_high
                risk = pmath.max(sl_price - close, self.syminfo.mintick)
                tp_price = close - risk * self.rr_ratio
                st.entry("Short", st.short, qty=self.lot_size)
                if self.use_sltp:
                    st.exit("Short SLTP", "Short", stop=sl_price, limit=tp_price, comment_loss="SL", comment_profit="TP")
            if exit_s:
                st.close("Short", comment="Signal Exit")
