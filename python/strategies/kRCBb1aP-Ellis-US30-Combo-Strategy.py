"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ellis US30 Combo Strategy
Author       : alexmateo1991
Source URL   : https://www.tradingview.com/script/kRCBb1aP-Ellis-US30-Combo-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Two signal families, both inside the New York session and until the daily profit target / loss limit (closed P&L since the day's first bar) is reached: (1) a stochastic-RSI %K / %D cross at an extreme in the direction of the SMA21/50 stack;
(2) a MACD cross below / above zero with the full SMA 21/50/200 stack, RSI above / below its floating level and a recent RSI-versus-price divergence of pivots. A signal enters at the close (reversing an opposite position) with a fixed point stop and target around the close, placed with the entry.

Deviations from the original: none.
Not carried over: the buy / sell labels, status panel label and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class EllisUs30Combo(Script):
    TITLE = "Ellis US30 Combo Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "kRCBb1aP", "author": "alexmateo1991", "licence": "not stated",
              "url": "https://www.tradingview.com/script/kRCBb1aP-Ellis-US30-Combo-Strategy"}

    def init(self):
        i = self.input
        self.use_ny_session = i.bool(True, "Trade Only New York Session")
        self.ny_session = i.session("0930-1600", "New York Session")
        self.use_daily_profit = i.bool(True, "Use Daily Profit Target ($)")
        self.daily_profit_target = i.float(100.0, "Daily Profit Target ($)", minval=1)
        self.use_daily_loss = i.bool(True, "Use Daily Loss Limit ($)")
        self.daily_loss_limit = i.float(100.0, "Daily Loss Limit ($)", minval=1)
        self.stop_loss_points = i.float(300.0, "Stop Loss (Points)", minval=1)
        self.take_profit_points = i.float(600.0, "Take Profit (Points)", minval=1)
        self.sma_fast_len = i.int(21, "SMA Fast", minval=1)
        self.sma_mid_len = i.int(50, "SMA Mid", minval=1)
        self.sma_slow_len = i.int(200, "SMA Slow", minval=1)
        self.macd_fast_len = i.int(12, "MACD Fast Length", minval=1)
        self.macd_slow_len = i.int(26, "MACD Slow Length", minval=1)
        self.macd_signal_len = i.int(9, "MACD Signal Length", minval=1)
        self.stoch_k_len = i.int(3, "Stoch RSI K", minval=1)
        self.stoch_d_len = i.int(3, "Stoch RSI D", minval=1)
        self.stoch_rsi_len = i.int(14, "Stoch RSI RSI Length", minval=1)
        self.stoch_len = i.int(12, "Stoch RSI Length", minval=1)
        self.stoch_oversold = i.float(25.0, "Stoch RSI Oversold")
        self.stoch_overbought = i.float(75.0, "Stoch RSI Overbought")
        self.rsi_div_period = i.int(14, "RSI Div Period", minval=1)
        self.div_pivot_left = i.int(5, "RSI Div Pivot Left", minval=1)
        self.div_pivot_right = i.int(5, "RSI Div Pivot Right", minval=1)
        self.div_floating = i.float(50.0, "RSI Div Floating")
        self.div_scan_length = i.int(50, "RSI Div Length", minval=5)
        self.prev_bull_price = NA
        self.last_bull_price = NA
        self.prev_bull_rsi = NA
        self.last_bull_rsi = NA
        self.last_bull_bar = NA
        self.prev_bear_price = NA
        self.last_bear_price = NA
        self.prev_bear_rsi = NA
        self.last_bear_rsi = NA
        self.last_bear_bar = NA
        self.day_start_net_profit = 0.0

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_ny_session = not na(self.time_fn(None, self.ny_session))
        session_ok = in_ny_session if self.use_ny_session else True
        sma21 = ta.sma(close, self.sma_fast_len)
        sma50 = ta.sma(close, self.sma_mid_len)
        sma200 = ta.sma(close, self.sma_slow_len)
        rsi_stoch_source = ta.rsi(close, self.stoch_rsi_len)
        rsi_div = ta.rsi(close, self.rsi_div_period)
        lowest_rsi = ta.lowest(rsi_stoch_source, self.stoch_len)
        highest_rsi = ta.highest(rsi_stoch_source, self.stoch_len)
        raw_stoch_rsi = 50.0 if highest_rsi - lowest_rsi == 0 else div(rsi_stoch_source - lowest_rsi, highest_rsi - lowest_rsi) * 100.0
        k = ta.sma(raw_stoch_rsi, self.stoch_k_len)
        d = ta.sma(k, self.stoch_d_len)
        macd_line, signal_line, _hist_line = ta.macd(close, self.macd_fast_len, self.macd_slow_len, self.macd_signal_len)
        pivot_low_price = ta.pivotlow(self.low, self.div_pivot_left, self.div_pivot_right)
        pivot_high_price = ta.pivothigh(self.high, self.div_pivot_left, self.div_pivot_right)
        pivot_low_rsi = ta.pivotlow(rsi_div, self.div_pivot_left, self.div_pivot_right)
        pivot_high_rsi = ta.pivothigh(rsi_div, self.div_pivot_left, self.div_pivot_right)
        if (not na(pivot_low_price)) and (not na(pivot_low_rsi)):
            self.prev_bull_price = self.last_bull_price
            self.prev_bull_rsi = self.last_bull_rsi
            self.last_bull_price = pivot_low_price
            self.last_bull_rsi = pivot_low_rsi
            self.last_bull_bar = self.bar_index - self.div_pivot_right
        if (not na(pivot_high_price)) and (not na(pivot_high_rsi)):
            self.prev_bear_price = self.last_bear_price
            self.prev_bear_rsi = self.last_bear_rsi
            self.last_bear_price = pivot_high_price
            self.last_bear_rsi = pivot_high_rsi
            self.last_bear_bar = self.bar_index - self.div_pivot_right
        bullish_divergence = ((not na(self.prev_bull_price)) and (not na(self.last_bull_price)) and (not na(self.prev_bull_rsi)) and (not na(self.last_bull_rsi))
                              and self.last_bull_price < self.prev_bull_price and self.last_bull_rsi > self.prev_bull_rsi and (not na(self.last_bull_bar))
                              and (self.bar_index - self.last_bull_bar <= self.div_scan_length))
        bearish_divergence = ((not na(self.prev_bear_price)) and (not na(self.last_bear_price)) and (not na(self.prev_bear_rsi)) and (not na(self.last_bear_rsi))
                              and self.last_bear_price > self.prev_bear_price and self.last_bear_rsi < self.prev_bear_rsi and (not na(self.last_bear_bar))
                              and (self.bar_index - self.last_bear_bar <= self.div_scan_length))
        kd_up = ta.crossover(k, d)
        kd_dn = ta.crossunder(k, d)
        macd_up = ta.crossover(macd_line, signal_line)
        macd_dn = ta.crossunder(macd_line, signal_line)
        stock_buy = sma21 > sma50 and kd_up and pmath.min(k, d) <= self.stoch_oversold
        stock_sell = sma21 < sma50 and kd_dn and pmath.max(k, d) >= self.stoch_overbought
        macd_buy = (sma21 > sma50 and sma21 > sma200 and sma50 > sma200 and macd_up and macd_line < 0 and signal_line < 0
                    and rsi_div > self.div_floating and bullish_divergence)
        macd_sell = (sma21 < sma50 and sma21 < sma200 and sma50 < sma200 and macd_dn and macd_line > 0 and signal_line > 0
                     and rsi_div < self.div_floating and bearish_divergence)
        buy_signal = stock_buy or macd_buy
        sell_signal = stock_sell or macd_sell
        new_day = ta.change(self.time_fn("D"))
        if (not na(new_day)) and new_day != 0:
            self.day_start_net_profit = st.netprofit
        daily_closed_pnl = st.netprofit - self.day_start_net_profit
        daily_profit_hit = self.use_daily_profit and daily_closed_pnl >= self.daily_profit_target
        daily_loss_hit = self.use_daily_loss and daily_closed_pnl <= -self.daily_loss_limit
        daily_blocked = daily_profit_hit or daily_loss_hit
        point_value = self.syminfo.mintick
        long_stop = close - self.stop_loss_points * point_value
        long_tp = close + self.take_profit_points * point_value
        short_stop = close + self.stop_loss_points * point_value
        short_tp = close - self.take_profit_points * point_value
        allow_trade = session_ok and (not daily_blocked) and self.barstate.isconfirmed
        enter_long = allow_trade and buy_signal and st.position_size <= 0 and not sell_signal
        enter_short = allow_trade and sell_signal and st.position_size >= 0 and not buy_signal
        long_comment = "Stock+MACD" if (stock_buy and macd_buy) else ("Stock" if stock_buy else "MACD")
        short_comment = "Stock+MACD" if (stock_sell and macd_sell) else ("Stock" if stock_sell else "MACD")
        if enter_long:
            st.entry("Buy", st.long, comment=long_comment)
            st.exit("Buy Exit", "Buy", stop=long_stop, limit=long_tp)
        if enter_short:
            st.entry("Sell", st.short, comment=short_comment)
            st.exit("Sell Exit", "Sell", stop=short_stop, limit=short_tp)
