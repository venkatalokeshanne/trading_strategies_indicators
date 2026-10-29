"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : QQE Trend Strategy [Long/Short]
Author       : Shiroi-
Source URL   : https://www.tradingview.com/script/KM4wOmrL
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A QQE line (EMA of RSI) with ATR-style (double EMA of its change) long / short bands for a fast and a slow factor; the trend flips up when the line crosses above the short band
and down when it crosses below the long band (the cross-under is only evaluated while the cross-over is false, as in Pine's lazy ternary). The selected band's trend turning bullish / bearish, with the 50-line
filter on the QQE line, opens a long / short at the next open (reversing). An optional percent stop is off by default. qqeCalc() keeps ta and var state, so it is written out once per band.

Deviations from the original: none.
Not carried over: histogram, bands, markers, backgrounds, bar colouring and alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, nz, pmath, ta


class QqeTrend(Script):
    TITLE = "QQE Trend Strategy [Long/Short]"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(margin_long=100, margin_short=100, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.03, slippage=1)
    SOURCE = {"id": "KM4wOmrL", "author": "Shiroi-", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KM4wOmrL"}

    def init(self):
        g = "📊 QQE Settings"
        self.rsi_len = self.input.int(14, "RSI Length", minval=2, group=g)
        self.rsi_smooth = self.input.int(5, "Smooth EMA Length", minval=1, group=g)
        self.fast_factor = self.input.float(2.618, "Fast Band Factor", minval=0.1, step=0.001, group=g)
        self.slow_factor = self.input.float(4.236, "Slow Band Factor", minval=0.1, step=0.001, group=g)
        g = "⚙️ Strategy"
        self.sig_mode = self.input.string("Slow", "Signal Band", options=["Fast", "Slow"], group=g)
        self.use50_filter = self.input.bool(True, "50-Line Direction Filter", group=g)
        self.trade_dir = self.input.string("Both", "Trade Direction", options=["Both", "Long Only", "Short Only"], group=g)
        self.qty_fixed = self.input.float(1.0, "Lot Size", minval=0.01, step=0.01, group=g)
        self.use_stop_loss = self.input.bool(False, "Enable Stop Loss", group=g)
        self.stop_loss_pct = self.input.float(1.0, "SL (%)", minval=0.1, step=0.1, group=g)
        self.f_lb = NA
        self.f_sb = NA
        self.f_tr = 1
        self.s_lb = NA
        self.s_sb = NA
        self.s_tr = 1

    def qqe_fast(self):
        rsi = ta.rsi(self.close, self.rsi_len)
        qqe_l = ta.ema(rsi, self.rsi_smooth)
        wp = self.rsi_smooth * 2 - 1
        prev = self.H("fq")[1]
        self.H("fq").set(qqe_l)
        dar = ta.ema(ta.ema(pmath.abs(qqe_l - prev), wp), wp) * self.fast_factor
        lb_prev, sb_prev = self.f_lb, self.f_sb
        self.f_lb = pmath.max(nz(lb_prev, qqe_l - dar), qqe_l - dar) if qqe_l > nz(lb_prev, qqe_l - dar) else qqe_l - dar
        self.f_sb = pmath.min(nz(sb_prev, qqe_l + dar), qqe_l + dar) if qqe_l < nz(sb_prev, qqe_l + dar) else qqe_l + dar
        tr = 1 if ta.crossover(qqe_l, sb_prev) else (-1 if ta.crossunder(qqe_l, lb_prev) else nz(self.f_tr, 1))
        self.f_tr = tr
        return qqe_l, self.f_lb if tr == 1 else self.f_sb, tr

    def qqe_slow(self):
        rsi = ta.rsi(self.close, self.rsi_len)
        qqe_l = ta.ema(rsi, self.rsi_smooth)
        wp = self.rsi_smooth * 2 - 1
        prev = self.H("sq")[1]
        self.H("sq").set(qqe_l)
        dar = ta.ema(ta.ema(pmath.abs(qqe_l - prev), wp), wp) * self.slow_factor
        lb_prev, sb_prev = self.s_lb, self.s_sb
        self.s_lb = pmath.max(nz(lb_prev, qqe_l - dar), qqe_l - dar) if qqe_l > nz(lb_prev, qqe_l - dar) else qqe_l - dar
        self.s_sb = pmath.min(nz(sb_prev, qqe_l + dar), qqe_l + dar) if qqe_l < nz(sb_prev, qqe_l + dar) else qqe_l + dar
        tr = 1 if ta.crossover(qqe_l, sb_prev) else (-1 if ta.crossunder(qqe_l, lb_prev) else nz(self.s_tr, 1))
        self.s_tr = tr
        return qqe_l, self.s_lb if tr == 1 else self.s_sb, tr

    def on_bar(self):
        f_line, f_band, f_trend = self.qqe_fast()
        s_line, s_band, s_trend = self.qqe_slow()
        active_trend = f_trend if self.sig_mode == "Fast" else s_trend
        at_prev = self.H("active")[1]
        self.H("active").set(active_trend)
        raw_buy = active_trend == 1 and at_prev == -1
        raw_sell = active_trend == -1 and at_prev == 1
        f50_buy = f_line > 50 if self.use50_filter else True
        f50_sell = f_line < 50 if self.use50_filter else True
        buy_signal = raw_buy and f50_buy and self.trade_dir != "Short Only"
        sell_signal = raw_sell and f50_sell and self.trade_dir != "Long Only"
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long, qty=self.qty_fixed)
        if sell_signal:
            st.entry("Short", st.short, qty=self.qty_fixed)
        if self.use_stop_loss:
            avg = st.position_avg_price
            if st.position_size > 0:
                st.exit("SL-Long", from_entry="Long", stop=avg * (1 - self.stop_loss_pct / 100))
            if st.position_size < 0:
                st.exit("SL-Short", from_entry="Short", stop=avg * (1 + self.stop_loss_pct / 100))
        self.plot(f_line, "QQE Line", color=color.purple, linewidth=2)
        self.plot(f_band, "Fast Band", color=color.green)
        self.plot(s_band, "Slow Band", color=color.teal)
