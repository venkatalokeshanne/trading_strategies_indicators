"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : GOLD EDGE FUND v3 (MTF + SMC + Risk Engine)
Author       : not stated
Source URL   : https://www.tradingview.com/script/3xb1MBvG
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Inside the London (07-10) or New York (13-16) exchange hours, a long needs the 15-minute close over its EMA(50) over its EMA(200), the chart close over EMA(20) over EMA(50), RSI over 55 and one of: a liquidity sweep of the 10-bar low (low under the previous bar's 10-bar low, close back above the current one), a bullish fair-value gap (low over the high two bars back) or a bullish order block; shorts mirror these with RSI under 45. Entries are placed on every signal (1 % of equity, pyramiding 0), each carrying a 1.3 ATR stop / 1.6 R:R target exit order; once the close is 0.8 ATR in profit a break-even stop is added and a trailing stop one ATR under (over) the close is re-issued every bar. All positions close when the day's equity drawdown reaches -3 %, and all orders are cancelled after 7 entries in a day.
Assumption: `dayofmonth != dayofmonth[1]` is true on the first bar (a na previous value compares as different).
Deviations from the original: none.
Not carried over: plots.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, ta


class GoldEdgeFund(Script):
    TITLE = "GOLD EDGE FUND v3 (MTF + SMC + Risk Engine)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=1)
    SOURCE = {"id": "3xb1MBvG", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/3xb1MBvG"}

    def init(self):
        i = self.input
        self.lookback = i.int(10, "Liquidity Lookback")
        self.risk_atr = i.float(1.3, "ATR Risk Mult")
        self.rr = i.float(1.6, "Risk Reward")
        self.max_daily_loss = i.float(3.0, "Max Daily Loss %")
        self.max_trades = i.int(7, "Max Trades Per Day")
        self.day_start_equity = NA
        self.trades_today = 0

    def on_bar(self):
        st = self.strategy
        close, high, low, open_ = self.close, self.high, self.low, self.open
        h_liq_h, h_liq_l, h_dom, h_ot = self.H("lh"), self.H("ll"), self.H("dom"), self.H("ot")
        liq_h_1, liq_l_1, dom_1, ot_1 = h_liq_h[1], h_liq_l[1], h_dom[1], h_ot[1]
        high_1, high_2, low_1, low_2, open_1 = self.high[1], self.high[2], self.low[1], self.low[2], self.open[1]
        hour = self.hour()
        london = hour >= 7 and hour <= 10
        newyork = hour >= 13 and hour <= 16
        session_ok = london or newyork
        htf_close = self.security(None, "15", lambda v: float(v.close))
        htf_ema50 = self.security(None, "15", lambda v: ta.ema(v.close, 50))
        htf_ema200 = self.security(None, "15", lambda v: ta.ema(v.close, 200))
        htf_bull = htf_close > htf_ema50 and htf_ema50 > htf_ema200
        htf_bear = htf_close < htf_ema50 and htf_ema50 < htf_ema200
        ema20 = ta.ema(close, 20)
        ema50 = ta.ema(close, 50)
        trend_up = close > ema20 and ema20 > ema50
        trend_down = close < ema20 and ema20 < ema50
        bull_fvg = low > high_2
        bear_fvg = high < low_2
        bull_ob = close > high_1 and open_1 > self.close[1]
        bear_ob = close < low_1 and open_1 < self.close[1]
        liq_high = ta.highest(high, self.lookback)
        liq_low = ta.lowest(low, self.lookback)
        sweep_high = high > liq_h_1 and close < liq_high
        sweep_low = low < liq_l_1 and close > liq_low
        rsi = ta.rsi(close, 14)
        momentum_buy = rsi > 55
        momentum_sell = rsi < 45
        long_cond = session_ok and htf_bull and trend_up and (sweep_low or bull_fvg or bull_ob) and momentum_buy
        short_cond = session_ok and htf_bear and trend_down and (sweep_high or bear_fvg or bear_ob) and momentum_sell
        atr = ta.atr(14)
        long_sl = close - atr * self.risk_atr
        short_sl = close + atr * self.risk_atr
        long_tp = close + atr * self.risk_atr * self.rr
        short_tp = close - atr * self.risk_atr * self.rr
        if long_cond:
            st.entry("BUY", st.long)
        if short_cond:
            st.entry("SELL", st.short)
        st.exit("EXIT BUY", from_entry="BUY", stop=long_sl, limit=long_tp)
        st.exit("EXIT SELL", from_entry="SELL", stop=short_sl, limit=short_tp)
        be_atr = atr * 0.8
        pos = st.position_size
        avg = st.position_avg_price
        if pos > 0 and close > avg + be_atr:
            st.exit("BE BUY", from_entry="BUY", stop=avg)
        if pos < 0 and close < avg - be_atr:
            st.exit("BE SELL", from_entry="SELL", stop=avg)
        trail_atr = atr * 1.0
        if pos > 0:
            st.exit("TRAIL BUY", from_entry="BUY", stop=close - trail_atr)
        if pos < 0:
            st.exit("TRAIL SELL", from_entry="SELL", stop=close + trail_atr)
        dom = self.dayofmonth()
        day_changed = dom != dom_1
        if day_changed:
            self.day_start_equity = float(st.equity)
        drawdown = 100 * div(st.equity - self.day_start_equity, self.day_start_equity)
        if drawdown <= -self.max_daily_loss:
            st.close_all()
        if day_changed:
            self.trades_today = 0
        ots = st.opentrades
        if (not (ot_1 != ot_1)) and ots > ot_1:
            self.trades_today += 1
        allow_trade = self.trades_today < self.max_trades
        if not allow_trade:
            st.cancel_all()
        h_liq_h.set(liq_high)
        h_liq_l.set(liq_low)
        h_dom.set(dom)
        h_ot.set(ots)
