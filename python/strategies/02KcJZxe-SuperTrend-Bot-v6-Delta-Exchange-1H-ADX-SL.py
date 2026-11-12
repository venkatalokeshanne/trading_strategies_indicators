"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SuperTrend Bot v6 — Delta Exchange [1H + ADX + SL]
Author       : kapsystem
Source URL   : https://www.tradingview.com/script/02KcJZxe-SuperTrend-Bot-v6-Delta-Exchange-1H-ADX-SL
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Reproduces the original exactly, including two bugs in it:
  1. `[_, adxLine, _] = ta.dmi(...)` takes the SECOND element, which is -DI, not ADX — the
     "ADX filter" is really a minus-DI filter.
  2. The stop-loss / take-profit are computed from strategy.position_avg_price on the signal
     bar, BEFORE the new entry fills: from flat that is na (no SL/TP at all), and on a
     reversal it is the previous, opposite position's price. The exit is never re-placed.

Deviations from the original: none.
Not carried over: bgcolor; the status table (display only, last bar).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, pmath, pstr, ta


class SuperTrendBotV6Delta(Script):
    TITLE = "SuperTrend Bot v6 — Delta Exchange [1H + ADX + SL]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=100000, currency="USD",
                    commission_type="percent", commission_value=0.05, pyramiding=0)
    SOURCE = {"id": "02KcJZxe", "author": "kapsystem", "licence": "not stated",
              "url": "https://www.tradingview.com/script/02KcJZxe-SuperTrend-Bot-v6-Delta-Exchange-1H-ADX-SL"}

    def init(self):
        i = self.input
        self.atr_len = i.int(10, "ATR Length", minval=1, group="SuperTrend Settings")
        self.factor = i.float(3.0, "Factor (Multiplier)", minval=0.1, step=0.1, group="SuperTrend Settings")
        self.use_adx = i.bool(True, "Enable ADX Trend Filter", group="ADX Filter")
        self.adx_len = i.int(14, "ADX Length", group="ADX Filter", minval=1)
        self.adx_min = i.float(20.0, "Min ADX to trade (≥20 = trend)", group="ADX Filter", minval=5, step=1.0)
        self.use_htf = i.bool(True, "Enable 4H SuperTrend Filter", group="HTF Filter")
        self.htf_atr = i.int(10, "4H ATR Length", group="HTF Filter", minval=1)
        self.htf_fact = i.float(3.0, "4H Factor", group="HTF Filter", minval=0.1, step=0.1)
        self.use_sl = i.bool(True, "Enable Stop-Loss", group="Stop-Loss")
        self.sl_pct = i.float(1.5, "Stop-Loss % from entry", group="Stop-Loss", minval=0.1, maxval=10.0, step=0.1)
        self.use_tp = i.bool(True, "Enable Take-Profit", group="Stop-Loss")
        self.tp_pct = i.float(3.0, "Take-Profit % from entry", group="Stop-Loss", minval=0.1, maxval=20.0, step=0.1)
        self.qty = i.int(1, "Order Quantity (contracts)", group="Order & Display", minval=1)
        self.show_lbls = i.bool(True, "Show BUY / SELL labels", group="Order & Display")
        self.show_info = i.bool(True, "Show filter status table", group="Order & Display")

    def on_bar(self):
        supertrend, direction = ta.supertrend(self.factor, self.atr_len)
        dir_prev = self.H("dir")[1]
        self.H("dir").set(direction)
        is_bullish = direction == -1
        is_bearish = direction == 1
        buy_flip = is_bullish and dir_prev == 1
        sell_flip = is_bearish and dir_prev == -1

        _, adx_line, _ = ta.dmi(self.adx_len, self.adx_len)      # [+DI, -DI, ADX]: this is -DI
        adx_ok = not self.use_adx or adx_line >= self.adx_min

        htf_st, htf_dir = self.security(self.syminfo.tickerid, "240",
                                        lambda v: ta.supertrend(self.htf_fact, self.htf_atr), lookahead=False)
        htf_bullish = htf_dir == -1
        htf_bearish = htf_dir == 1
        htf_ok_long = not self.use_htf or htf_bullish
        htf_ok_short = not self.use_htf or htf_bearish

        go_long = buy_flip and adx_ok and htf_ok_long
        go_short = sell_flip and adx_ok and htf_ok_short

        st = self.strategy
        if go_long:
            st.entry("Long", st.long, qty=self.qty)
            if self.use_sl or self.use_tp:
                sl_long = st.position_avg_price * (1 - self.sl_pct / 100) if self.use_sl else NA
                tp_long = st.position_avg_price * (1 + self.tp_pct / 100) if self.use_tp else NA
                st.exit("Long Exit", "Long", stop=sl_long, limit=tp_long)
        if go_short:
            st.entry("Short", st.short, qty=self.qty)
            if self.use_sl or self.use_tp:
                sl_short = st.position_avg_price * (1 + self.sl_pct / 100) if self.use_sl else NA
                tp_short = st.position_avg_price * (1 - self.tp_pct / 100) if self.use_tp else NA
                st.exit("Short Exit", "Short", stop=sl_short, limit=tp_short)

        self.plot(supertrend if is_bullish else NA, title="Uptrend Line", color=color.green, linewidth=2)
        self.plot(supertrend if is_bearish else NA, title="Downtrend Line", color=color.red, linewidth=2)

        if self.show_lbls:
            if go_long:
                self.draw.label_new(self.bar_index, self.low.cur, "BUY\nADX:" + pstr.tostring(pmath.round(adx_line, 1)),
                                    style="label_up", color=color.green)
            if go_short:
                self.draw.label_new(self.bar_index, self.high.cur, "SELL\nADX:" + pstr.tostring(pmath.round(adx_line, 1)),
                                    style="label_down", color=color.red)
            if buy_flip and not go_long:
                self.draw.label_new(self.bar_index, self.low.cur, "filtered", style="label_up", color=color.gray)
            if sell_flip and not go_short:
                self.draw.label_new(self.bar_index, self.high.cur, "filtered", style="label_down", color=color.gray)

        self.alertcondition(go_long or go_short, title="SuperTrend Signal [Filtered]",
                            message='{"symbol":"{{ticker}}", "side":"{{strategy.order.action}}", '
                                    '"qty":{{strategy.order.contracts}}, "trigger_time":"{{timenow}}"}')
