/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Professional Session CVD [Order Flow]
 * Author       : GuruJames22
 * Source URL   : https://www.tradingview.com/script/avDDJB8e-Professional-Session-CVD-Order-Flow-by-Gurujames
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Session CVD Order Flow_TV
 *
 * Deviations from the original: CVD candles drawn as close line plus high/low dotted lines; value labels replaced by
 *   markers; weekly reset by weekday wrap; intrabar history depth limited by data vendor
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Session CVD Order Flow_TV', 'lower');
const myLtfRes = input.select('Intrabar Timeframe', '1', ['1', '2', '3', '5']);
const myResetMode = input.select('Session Reset', 'Daily', ['Daily', 'Weekly', 'Continuous']);
const myShowLabels = input.boolean('Show Extreme Marks', true);
const myLtf = await request.history(current.ticker, myLtfRes);
assert(!myLtf.error, 'Error fetching intrabar data: ' + myLtf.error);
// buy volume minus sell volume per intrabar candle, as in the Pine
const myDelta = myLtf.close.map((_c, _i) => {
	const myO = myLtf.open[_i], myV = myLtf.volume[_i], myP = _i > 0 ? myLtf.close[_i - 1] : _c;
	const myBuy = _c > myO ? myV : ((_c === myO && _c >= myP) ? myV : 0);
	const mySell = _c < myO ? myV : ((_c === myO && _c < myP) ? myV : 0);
	return myBuy - mySell;
});
const myN = close.length;
const myKey = time.map(_t => { const myX = time_of(_t); return myResetMode === 'Daily' ? myX.year * 10000 + myX.month * 100 + myX.dayOfMonth : (myResetMode === 'Weekly' ? myX.dayOfWeek : 0); });
const myCvdOpen = [], myCvdHigh = [], myCvdLow = [], myCvdClose = [];
let myCur = 0, myPtr = 0;
for (let myI = 0; myI < myN; myI += 1) {
	let myNew = false;
	if (myI > 0) myNew = myResetMode === 'Daily' ? myKey[myI] !== myKey[myI - 1] : (myResetMode === 'Weekly' ? myKey[myI] < myKey[myI - 1] : false);
	if (myNew) myCur = 0;
	const myEnd = myI + 1 < myN ? time[myI + 1] : Infinity;
	while (myPtr < myLtf.time.length && myLtf.time[myPtr] < time[myI]) myPtr += 1;
	let myTemp = myCur, myHi = myCur, myLo = myCur;
	while (myPtr < myLtf.time.length && myLtf.time[myPtr] < myEnd) { myTemp += myDelta[myPtr]; myHi = Math.max(myHi, myTemp); myLo = Math.min(myLo, myTemp); myPtr += 1; }
	myCvdOpen.push(myCur); myCvdHigh.push(myHi); myCvdLow.push(myLo); myCvdClose.push(myTemp);
	myCur = myTemp;
}
const myIsHigh = myCvdClose.map((_c, _i) => { if (_i < 9) return false; for (let myK = _i - 9; myK <= _i; myK += 1) if (myCvdClose[myK] > _c) return false; return true; });
const myIsLow = myCvdClose.map((_c, _i) => { if (_i < 9) return false; for (let myK = _i - 9; myK <= _i; myK += 1) if (myCvdClose[myK] < _c) return false; return true; });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });
paint(myCvdHigh, { name: 'CVD High', color: 'silver', style: 'dotted' });
paint(myCvdLow, { name: 'CVD Low', color: 'silver', style: 'dotted' });
paint(myCvdClose, { name: 'CVD Close', color: myCvdClose.map((_c, _i) => _c >= myCvdOpen[_i] ? '#009688' : '#f44336'), thickness: 2 });
paint(myCvdHigh.map((_v, _i) => (myShowLabels && myIsHigh[_i]) ? _v : null), { name: 'High Mark', color: '#009688', style: 'dotted', marker: 'triangle-down' });
paint(myCvdLow.map((_v, _i) => (myShowLabels && myIsLow[_i]) ? _v : null), { name: 'Low Mark', color: '#f44336', style: 'dotted', marker: 'triangle' });
register_signal(myCvdClose.map((_c, _i) => _c >= myCvdOpen[_i]), 'Bullish Delta Bar');
register_signal(myCvdClose.map((_c, _i) => _c < myCvdOpen[_i]), 'Bearish Delta Bar');
register_signal(myIsHigh, 'Delta Swing High');
register_signal(myIsLow, 'Delta Swing Low');
