"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Flowrise BOT 2.0
Author       : karlervenscorioland
Source URL   : https://www.tradingview.com/script/OyYdqgiv
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A Supertrend (ATR from the RMA built-in or the SMA of the true range) flip to the MA-200 side opens a position sized from the risk percentage (or a fixed amount) of the equity over the stop distance; the optional session, weekday and month filters gate the flip. `strategy.close_all` runs on every Supertrend change and, with the fixed take-profit option, when the close reaches the stored target; there is no stop order (the "stop" levels and the trailing stop are only drawn).
Deviations from the original: none.
Not carried over: the buy / sell labels, the trend fill, the TP / SL / entry boxes and lines, the cumulative-RR counters and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class FlowriseBot(Script):
    TITLE = "Flowrise BOT 2.0"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "OyYdqgiv", "author": "karlervenscorioland", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OyYdqgiv"}

    def init(self):
        i = self.input
        g = "Supertrend"
        self.periods = i.int(10, "ATR Period", group=g, minval=1)
        self.src = i.source(self.hl2, "Source", group=g)
        self.mult = i.float(3.0, "ATR Multiplier", group=g, step=0.1)
        self.change_atr = i.bool(True, "Change ATR Calculation Method?", group=g)
        g = "MA 200"
        self.ma_period = i.int(200, "MA 200 Period", group=g, minval=1)
        self.ma_source = i.source(self.hl2, "MA 200 Source", group=g)
        g = "Signaux"
        i.bool(True, "Show Buy/Sell Signals?", group=g)
        i.bool(True, "Highlighter On/Off?", group=g)
        self.trade_type = i.string("Both", "Type de Trade", group=g, options=["Buy Only", "Sell Only", "Both"])
        g = "Risk & Trailing SL"
        self.risk_mode = i.string("Composé %", "Mode risque", group=g, options=["Composé %", "Fixe $"])
        self.risk_pct = i.float(2.0, "Risque %", group=g, minval=0.0, maxval=100, step=0.1)
        self.risk_fixed = i.float(100.0, "Montant fixe ($)", group=g, minval=1.0, step=10.0)
        i.float(1.5, "Stop Loss Multiplier", group=g, minval=0.0, step=0.1)
        i.bool(False, "Trailing SL actif", group=g)
        i.float(1.5, "Trailing SL (%)", group=g, minval=0.01, step=0.1)
        g = "Take Profit"
        self.use_tp = i.bool(False, "TP fixe (R:R) actif", group=g)
        self.tp_rr = i.float(2.0, "TP R:R", group=g, minval=0.1, step=0.1)
        g = "Sessions"
        self.sess_start_h = i.int(9, "Début", group=g, minval=1, maxval=12, inline="sess")
        self.sess_start_ap = i.string("AM", "", group=g, options=["AM", "PM"], inline="sess")
        self.sess_end_h = i.int(5, "→ Fin", group=g, minval=1, maxval=12, inline="sess")
        self.sess_end_ap = i.string("PM", "", group=g, options=["AM", "PM"], inline="sess")
        self.use_sess = i.bool(False, "Filtre session actif", group=g)
        g = "Jours de Trading"
        self.t_lun = i.bool(True, "Lundi", group=g, inline="days1")
        self.t_mar = i.bool(True, "Mardi", group=g, inline="days1")
        self.t_mer = i.bool(True, "Mercredi", group=g, inline="days1")
        self.t_jeu = i.bool(True, "Jeudi", group=g, inline="days2")
        self.t_ven = i.bool(True, "Vendredi", group=g, inline="days2")
        self.t_sam = i.bool(False, "Samedi", group=g, inline="days2")
        g = "Mois de Trading"
        self.t_months = [
            i.bool(True, "Jan", group=g, inline="m1"), i.bool(True, "Fév", group=g, inline="m1"),
            i.bool(True, "Mar", group=g, inline="m1"), i.bool(True, "Avr", group=g, inline="m1"),
            i.bool(True, "Mai", group=g, inline="m2"), i.bool(True, "Jun", group=g, inline="m2"),
            i.bool(True, "Jul", group=g, inline="m2"), i.bool(True, "Aoû", group=g, inline="m2"),
            i.bool(True, "Sep", group=g, inline="m3"), i.bool(True, "Oct", group=g, inline="m3"),
            i.bool(True, "Nov", group=g, inline="m3"), i.bool(True, "Déc", group=g, inline="m3"),
        ]
        i.string("Bas Droite", "Position tableau", group="Dashboard", options=["Haut Gauche", "Haut Droite", "Bas Gauche", "Bas Droite"])
        i.string("Moyen", "Taille tableau", group="Dashboard", options=["Petit", "Moyen", "Grand"])
        self.up_prev = NA
        self.dn_prev = NA
        self.trend = 1
        self.trend_prev = NA
        self.active_tp = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        mintick = self.syminfo.mintick
        atr2 = ta.sma(ta.tr(True), self.periods)
        atrv = ta.atr(self.periods) if self.change_atr else atr2
        up = self.src - (self.mult * atrv)
        up1 = nz(self.up_prev, up)
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        up = pmath.max(up, up1) if close_1 > up1 else up
        dn = self.src + (self.mult * atrv)
        dn1 = nz(self.dn_prev, dn)
        dn = pmath.min(dn, dn1) if close_1 < dn1 else dn
        self.up_prev = float(up)
        self.dn_prev = float(dn)
        ma200 = ta.sma(self.ma_source, self.ma_period)
        ma200_trend = 1 if close > ma200 else -1
        trend_before = self.trend
        trend = 1 if (trend_before == -1 and close > dn1) else (-1 if (trend_before == 1 and close < up1) else trend_before)
        trend_1 = self.trend_prev
        trend_change = (not na(trend_1)) and trend != trend_1
        self.trend = trend
        self.trend_prev = trend
        s24 = (0 if self.sess_start_h == 12 else self.sess_start_h) if self.sess_start_ap == "AM" else (12 if self.sess_start_h == 12 else self.sess_start_h + 12)
        e24 = (0 if self.sess_end_h == 12 else self.sess_end_h) if self.sess_end_ap == "AM" else (12 if self.sess_end_h == 12 else self.sess_end_h + 12)
        hr = self.hour()
        in_sess = (hr >= s24 and hr < e24) if s24 <= e24 else (hr >= s24 or hr < e24)
        dow = self.dayofweek()
        trading_day = ((dow == 2 and self.t_lun) or (dow == 3 and self.t_mar) or (dow == 4 and self.t_mer) or (dow == 5 and self.t_jeu)
                       or (dow == 6 and self.t_ven) or (dow == 7 and self.t_sam))
        trading_month = self.t_months[self.month() - 1]
        sess_ok = (not self.use_sess) or in_sess
        buy_cond = bool(ma200_trend == 1 and trend == 1 and trend_1 == -1 and sess_ok and trading_day and trading_month)
        sell_cond = bool(ma200_trend == -1 and trend == -1 and trend_1 == 1 and sess_ok and trading_day and trading_month)
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        if buy_cond and st.position_size == 0:
            sl_dist = pmath.max(close - up, mintick)
            self.active_tp = float(close + sl_dist * self.tp_rr) if self.use_tp else NA
        if sell_cond and st.position_size == 0:
            sl_dist = pmath.max(dn - close, mintick)
            self.active_tp = float(close - sl_dist * self.tp_rr) if self.use_tp else NA
        risk_per_trade = self.risk_fixed if self.risk_mode == "Fixe $" else st.equity * (self.risk_pct / 100.0)
        sl_dist_l = pmath.max(close - up, mintick)
        sl_dist_s = pmath.max(dn - close, mintick)
        if st.position_size > 0:
            position_size = div(risk_per_trade, sl_dist_l)
        elif st.position_size < 0:
            position_size = div(risk_per_trade, sl_dist_s)
        elif buy_cond:
            position_size = div(risk_per_trade, sl_dist_l)
        elif sell_cond:
            position_size = div(risk_per_trade, sl_dist_s)
        else:
            position_size = 0.0
        if st.position_size == 0 and (not na(pos_1)) and pos_1 != 0:
            self.active_tp = NA
        tp_long = self.use_tp and st.position_size > 0 and not na(self.active_tp) and close >= self.active_tp
        tp_short = self.use_tp and st.position_size < 0 and not na(self.active_tp) and close <= self.active_tp
        exit_condition = trend_change or tp_long or tp_short
        if (self.trade_type == "Buy Only" or self.trade_type == "Both") and buy_cond:
            st.entry("Buy", st.long, qty=position_size, alert_message="SuperTrend Buy!")
        if (self.trade_type == "Sell Only" or self.trade_type == "Both") and sell_cond:
            st.entry("Sell", st.short, qty=position_size, alert_message="SuperTrend Sell!")
        if exit_condition:
            st.close_all(comment="", alert_message="Exit: Trend change or Stop hit")
