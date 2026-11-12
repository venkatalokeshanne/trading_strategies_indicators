"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 凱因斯順勢策略 — 多週期版(重建)
Author       : desperate731
Source URL   : https://www.tradingview.com/script/W6w1R6uB
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The "Keynes" oscillator is 1.12 * EMA5(deviation of the source from its 240-bar SMA, in %)
- 0.48. A zero-line cross-up with a rising HMA(217) and the daily close above the daily SMA(60) (lookahead off) goes long
at the bar close (process_orders_on_close); a cross-down closes the long. Fixed 1 contract, 120 cash commission per
contract, pyramiding 0.

Deviations from the original: none.
Not carried over: webhook messages (alert_message only), cosmetic plots.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, ta


class KeynesMtf(Script):
    TITLE = "凱因斯順勢策略 — 多週期版(重建)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="fixed", default_qty_value=1, pyramiding=0,
                    process_orders_on_close=True, commission_type="cash_per_contract", commission_value=120)
    SOURCE = {"id": "W6w1R6uB", "author": "desperate731", "licence": "not stated",
              "url": "https://www.tradingview.com/script/W6w1R6uB"}

    def init(self):
        self.ema_len = self.input.int(20, "EMA 長度", group="訊號")
        self.sma_mid_len = self.input.int(60, "短期 SMA 長度", group="訊號")
        self.sma_lng_len = self.input.int(240, "長期 SMA 長度", group="訊號")
        self.hma_len = self.input.int(217, "HMA 長度", group="訊號")
        self.src = self.input.source(self.close, "來源價格", group="訊號")
        self.long_thr = self.input.float(0, "多單觸發門檻", group="訊號")
        self.use_htf = self.input.bool(True, "啟用大週期順勢濾網", group="濾網")
        self.htf_res = self.input.timeframe("1D", "大週期濾網時框", group="濾網")
        self.use_webhook = self.input.bool(False, "啟用 Webhook 訊息（接你的下單系統）", group="Webhook")
        self.webhook_secret = self.input.string("tv_mxf_abc123xyz", "Webhook Secret", group="Webhook")

    def on_bar(self):
        ema_v = ta.ema(self.src, self.ema_len)
        sma_mid = ta.sma(self.src, self.sma_mid_len)
        sma_lng = ta.sma(self.src, self.sma_lng_len)
        dev_pct = div(self.src - sma_lng, sma_lng) * 100
        keynes = 1.12 * ta.ema(dev_pct, 5) - 0.48
        hma = S(ta.hma(self.src, self.hma_len))
        hma_up = hma[0] > hma[1]
        htf_close = self.security(None, self.htf_res, lambda v: v.close)
        htf_sma = self.security(None, self.htf_res, lambda v: ta.sma(v.close, self.sma_mid_len))
        htf_up = (not self.use_htf) or htf_close > htf_sma
        long_signal = ta.crossover(keynes, self.long_thr) and hma_up and htf_up
        exit_signal = ta.crossunder(keynes, self.long_thr)
        st = self.strategy
        if long_signal:
            st.entry("買", st.long, alert_message="凱因斯多單進場")
        if st.position_size > 0 and exit_signal:
            st.close("買", comment="多單平倉", alert_message="凱因斯多單平倉")
        self.plot(keynes, "凱因斯群眾心理變化", color=color.red if keynes >= 0 else color.green)
        self.plot(ema_v, "EMA", color=color.orange)
        self.plot(sma_mid, "SMA中", color=color.blue)
        self.plot(sma_lng, "SMA長", color=color.gray)
