/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kloom ATR Position Sizer
 * Author       : Kloom
 * Source URL   : https://www.tradingview.com/script/ApizScHE-Kloom-ATR-Position-Sizer-Risk-Based-Quantity-Calc
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kloom ATR Position Sizer_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ATR; table via paint_overlay; stop-level lines
 *   unchanged.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kloom ATR Position Sizer_TV', 'price');
const myAccTab = input.tab('Account');
const myEquity = myAccTab.number('Account equity', 10000, { min: 10 });
const myRiskPct = myAccTab.number('Risk per trade %', 1.0, { min: 0.1, max: 10, step: 0.1 });
const myStopTab = input.tab('Stop distance');
const myAtrLen = myStopTab.number('ATR length', 14, { min: 1, max: 100 });
const myAtrMult = myStopTab.number('ATR mult for stop', 2.0, { min: 0.5, max: 10, step: 0.5 });
const myShowLvl = input.boolean('Show stop levels', true);
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLen) myAcc = mySeed / myAtrLen; return myAcc; }
	myAcc = (myAcc * (myAtrLen - 1) + _v) / myAtrLen; return myAcc;
});
const myStopDist = myAtr.map(_a => _a === null ? null : _a * myAtrMult);
const myRiskMoney = myEquity * myRiskPct / 100;
const myQty = myStopDist.map(_d => (_d !== null && _d > 0) ? myRiskMoney / _d : null);
const myLongStop = close.map((_c, _i) => myStopDist[_i] === null ? null : _c - myStopDist[_i]);
const myShortStop = close.map((_c, _i) => myStopDist[_i] === null ? null : _c + myStopDist[_i]);
paint(myLongStop.map(_v => myShowLvl ? _v : null), { name: 'Long Stop', color: 'teal', thickness: 1 });
paint(myShortStop.map(_v => myShowLvl ? _v : null), { name: 'Short Stop', color: 'red', thickness: 1 });
const myLast = close.length - 1;
const myQ = myQty[myLast];
const myPos = myQ === null ? null : myQ * close[myLast];
const myLev = myPos === null ? null : myPos / myEquity;
const myFmt = (_v, _d) => (_v === null || _v === undefined) ? 'na' : _v.toFixed(_d);
const myRow = (_a, _b, _bg) => ({ cells: [{ text: _a, color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: _b, color: 'white', background_color: _bg }] });
paint_overlay('Kloom Sizer Table', { position: 'top_right' }, {
	rows: [
		myRow('Risk', myRiskMoney.toFixed(2) + ' (' + myRiskPct.toFixed(1) + '%)', 'rgba(0,0,0,0.6)'),
		myRow('ATR', myFmt(myAtr[myLast], 4), 'rgba(0,0,0,0.6)'),
		myRow('Stop dist', myFmt(myStopDist[myLast], 4), 'rgba(0,0,0,0.6)'),
		myRow('Qty', myFmt(myQ, 4), 'rgba(0,128,128,0.5)'),
		myRow('Pos. value', myFmt(myPos, 2), 'rgba(0,0,0,0.6)'),
		myRow('Leverage', myLev === null ? 'na' : myLev.toFixed(2) + 'x', (myLev !== null && myLev > 3) ? 'rgba(220,20,20,0.7)' : 'rgba(0,0,0,0.6)')
	]
});
register_signal(close.map((_c, _i) => myLongStop[_i] !== null && _c <= myLongStop[_i]), 'Long Stop Hit');
register_signal(close.map((_c, _i) => myShortStop[_i] !== null && _c >= myShortStop[_i]), 'Short Stop Hit');
register_signal(close.map((_c, _i) => myQty[_i] !== null && myQty[_i] * _c / myEquity > 3), 'High Leverage');
