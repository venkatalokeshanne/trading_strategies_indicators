"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TASC 2026.03 One Percent A Week
Author       : PineCoders (article by Dion Kurczek, TASC March 2026)
Source URL   : https://www.tradingview.com/script/nVECqIQx
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, limit orders on the path). Each Monday's first regular-session bar records the weekly open and (re)issues a long limit order 1 % below it (the same id replaces an unfilled one). The first regular-session bar after a fill sends a limit exit 1 % above the average price; if the low falls under -0.5 % from the average price before that, the exit is moved to break-even; a position still open on Friday's last regular-session bar is closed immediately.
`session.isfirstbar_regular` / `session.islastbar_regular` are provided by pinelib as Script.session_isfirstbar_regular() / session_islastbar_regular() (every bar on daily and higher charts).
Deviations from the original: none.
Not carried over: the four plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na


class OnePercentAWeek(Script):
    TITLE = "TASC 2026.03 One Percent A Week"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "nVECqIQx", "author": "PineCoders", "licence": "not stated", "url": "https://www.tradingview.com/script/nVECqIQx"}

    def init(self):
        self.w_open = NA
        self.pt = NA
        self.send_pt = False
        self.be_sent = False

    def on_bar(self):
        st = self.strategy
        h_pos = self.H("pos")
        pos_prev = h_pos[1]
        first_regular = self.session_isfirstbar_regular()
        new_session = self.dayofweek() == 2 and first_regular                  # Monday (Sunday = 1)
        if new_session:
            self.w_open = float(self.open)
        down1 = self.w_open * 0.99
        if new_session:
            st.entry("Buy", st.long, limit=down1)
            self.pt = NA
        pos = st.position_size
        new_fill = (not na(pos_prev)) and pos != pos_prev
        if pos > 0 and new_fill:
            self.send_pt = True
            self.be_sent = False
        if self.send_pt and first_regular and not self.be_sent:
            self.pt = st.position_avg_price * 1.01
            st.exit("profit", "Buy", limit=self.pt, oca_name="Order", comment="Profit")
            self.send_pt = False
        bet = st.position_avg_price * 0.995
        if self.low < bet and not self.be_sent:
            self.pt = st.position_avg_price
            st.exit("profit", "Buy", limit=self.pt, oca_name="Order", comment="Break-even")
            self.be_sent = True
        if self.dayofweek() == 6 and pos > 0 and self.session_islastbar_regular():
            st.close_all("End of week", immediately=True)
        h_pos.set(pos)
