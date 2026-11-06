"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 单因子指数增强
Author       : laiyanjun8015
Source URL   : https://www.tradingview.com/script/w45uet8E
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The daily SMA60 / SMA100 pair comes from request.security with lookahead ON (every chart bar of a
day sees that day's final values); the golden-cross regime must hold for 15 consecutive chart bars. Inside the regime a
24-bar z-score under -2.1 arms the long, a z-score over +1.1, a lost regime or a 3 % close-under-average-price stop disarms
it; a flat armed state enters and a disarmed open long is closed at the next open. is_long is a var that persists.

Deviations from the original: none.
Not carried over: the stop, MA plots and backgrounds (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class SingleFactorEnhance(Script):
    TITLE = "单因子指数增强"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "w45uet8E", "author": "laiyanjun8015", "licence": "not stated",
              "url": "https://www.tradingview.com/script/w45uet8E"}

    def init(self):
        self.tf_macro = self.input.timeframe("D", "宏观趋势周期")
        self.ma_s_len = self.input.int(60, "短均线周期", group="均线底座")
        self.ma_l_len = self.input.int(100, "长均线周期", group="均线底座")
        self.conf_bars = self.input.int(15, "假突破确认(K线)", group="均线底座")
        self.z_len = self.input.int(24, "Z-Score 周期", group="进攻引擎")
        self.z_entry = self.input.float(-2.1, "入场阈值", step=0.1, group="进攻引擎")
        self.z_exit = self.input.float(1.1, "止盈阈值", step=0.1, group="进攻引擎")
        self.stop_loss_pct = self.input.float(3.0, "每笔最大回撤止损 (%)", step=0.1, group="风控设置")
        self.bull_conf_cnt = 0
        self.is_long = False

    def on_bar(self):
        m_ma_s, m_ma_l = self.security(None, self.tf_macro,
                                       lambda v: (ta.sma(v.close, self.ma_s_len), ta.sma(v.close, self.ma_l_len)),
                                       lookahead=True)
        macro_bull_raw = m_ma_s > m_ma_l
        self.bull_conf_cnt = self.bull_conf_cnt + 1 if macro_bull_raw else 0
        bull_regime = self.bull_conf_cnt >= self.conf_bars
        p_mean = ta.sma(self.close, self.z_len)
        p_std = ta.stdev(self.close, self.z_len)
        z_val = div(self.close - p_mean, pmath.max(p_std, 0.0001))
        st = self.strategy
        stop_price = st.position_avg_price * (1 - self.stop_loss_pct / 100)
        is_stop_loss = st.position_size > 0 and self.close < stop_price
        if bull_regime and z_val < self.z_entry:
            self.is_long = True
        if z_val > self.z_exit or (not bull_regime) or is_stop_loss:
            self.is_long = False
        if self.is_long and st.position_size == 0:
            st.entry("All-in Long", st.long, comment="圣杯入场")
        if (not self.is_long) and st.position_size > 0:
            st.close_all(comment="3%硬止损" if is_stop_loss else ("死叉清仓" if not bull_regime else "止盈出场"))
        self.plot(m_ma_s, "宏观短均线", color=color.blue, linewidth=2)
        self.plot(m_ma_l, "宏观长均线", color=color.orange, linewidth=2)
