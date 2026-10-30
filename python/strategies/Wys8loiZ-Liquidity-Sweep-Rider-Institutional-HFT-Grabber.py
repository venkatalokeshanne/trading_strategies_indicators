"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Liquidity Sweep Rider - Institutional HFT Grabber v6
Author       : uzair2join
Source URL   : https://www.tradingview.com/script/Wys8loiZ-Liquidity-Sweep-Rider-Institutional-HFT-Grabber
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The latest confirmed swing low / high are the buy-side / sell-side liquidity. A bar that wicks through the level and closes back across it on volume of at least
a multiple of its average is a sweep; with a cooldown of twice the pivot span since the last sweep of that side it enters (a long after a bullish sweep, a short after a bearish one; an opposite
position is reversed). While in a position an ATR stop and an R:R target are placed around the average price.

Deviations from the original: none.
Not carried over: the liquidity plots, entry labels, trigger background, the info table and alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class LiquiditySweepRider(Script):
    TITLE = "Liquidity Sweep Rider - Institutional HFT Grabber v6"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, initial_capital=100000, commission_type="percent", commission_value=0.04,
                    pyramiding=0)
    SOURCE = {"id": "Wys8loiZ", "author": "uzair2join", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Wys8loiZ-Liquidity-Sweep-Rider-Institutional-HFT-Grabber"}

    def init(self):
        self.left_bars = self.input.int(5, "Swing Pivot Left Bars (for liquidity clusters)", minval=1, maxval=20)
        self.right_bars = self.input.int(5, "Swing Pivot Right Bars (confirmed swings)", minval=1, maxval=20)
        self.vol_len = self.input.int(20, "Volume SMA Length (for HFT detection)")
        self.vol_mult = self.input.float(2.0, "HFT Huge Volume Multiplier (Institutional Grabber Filter)", minval=1.0, step=0.1)
        self.eat_sell_stops_long = self.input.bool(True, "Eat Sell Stops + Long SL (Bullish Sweep → Long Rider)")
        self.eat_buy_stops_short = self.input.bool(True, "Eat Buy Stops + Short SL (Bearish Sweep → Short Rider)")
        self.eat_stop_loss_only = self.input.bool(True, "Also Eat Pure Stop-Loss Clusters (included in above sweeps)")
        self.use_atr = self.input.bool(True, "Use ATR SL/TP")
        self.atr_len = self.input.int(14, "ATR Length")
        self.sl_atr_mult = self.input.float(1.2, "SL ATR Multiplier (tight after sweep)", minval=0.5, step=0.1)
        self.tp_rr = self.input.float(2.5, "Take-Profit Risk-Reward Ratio (ride the reversal)", minval=1.0, step=0.1)
        self.sell_side_liquidity = NA
        self.buy_side_liquidity = NA
        self.last_bull_sweep_bar = -999
        self.last_bear_sweep_bar = -999

    def on_bar(self):
        ph = ta.pivothigh(self.high, self.left_bars, self.right_bars)
        pl = ta.pivotlow(self.low, self.left_bars, self.right_bars)
        if not na(ph):
            self.sell_side_liquidity = ph
        if not na(pl):
            self.buy_side_liquidity = pl
        avg_vol = ta.sma(self.volume, self.vol_len)
        bull_sweep = (not na(self.buy_side_liquidity)) and self.low < self.buy_side_liquidity and self.close > self.buy_side_liquidity and self.volume >= avg_vol * self.vol_mult
        bear_sweep = (not na(self.sell_side_liquidity)) and self.high > self.sell_side_liquidity and self.close < self.sell_side_liquidity and self.volume >= avg_vol * self.vol_mult
        cooldown = pmath.max(self.left_bars + self.right_bars, 5) * 2
        bull_entry = bull_sweep and self.eat_sell_stops_long and (self.bar_index - self.last_bull_sweep_bar > cooldown)
        bear_entry = bear_sweep and self.eat_buy_stops_short and (self.bar_index - self.last_bear_sweep_bar > cooldown)
        st = self.strategy
        if bull_entry:
            st.entry("Sweep Rider LONG", st.long)
            self.last_bull_sweep_bar = self.bar_index
        if bear_entry:
            st.entry("Sweep Rider SHORT", st.short)
            self.last_bear_sweep_bar = self.bar_index
        atr_val = ta.atr(self.atr_len)
        if self.use_atr and st.position_size != 0:
            avg = st.position_avg_price
            if st.position_size > 0:
                st.exit("Exit LONG", from_entry="Sweep Rider LONG", stop=avg - atr_val * self.sl_atr_mult, limit=avg + atr_val * self.sl_atr_mult * self.tp_rr)
            if st.position_size < 0:
                st.exit("Exit SHORT", from_entry="Sweep Rider SHORT", stop=avg + atr_val * self.sl_atr_mult, limit=avg - atr_val * self.sl_atr_mult * self.tp_rr)
        self.plot(self.sell_side_liquidity, "Sell-Side Liquidity (Buy Stops / Short SL)", color=color.red, linewidth=2)
        self.plot(self.buy_side_liquidity, "Buy-Side Liquidity (Sell Stops / Long SL)", color=color.green, linewidth=2)
