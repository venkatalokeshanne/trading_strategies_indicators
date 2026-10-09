/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kloom Turtle System
 * Author       : Kloom
 * Source URL   : https://www.tradingview.com/script/TnkefIeX-Kloom-Turtle-System-Donchian-Breakout-with-Trend-Filter
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kloom Turtle System_TV
 *
 * Deviations from the original: Reviewed AI draft; channels and state machine hand-rolled; markers as icons; table
 *   via paint_overlay; dotted styles not available.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kloom Turtle System_TV', 'price');
const myEntryLen = input.number('Entry length', 20, { min: 5, max: 200 });
const myExitLen = input.number('Exit length', 10, { min: 3, max: 100 });
const myUseTrend = input.boolean('Trend EMA filter', true);
const myTrendLen = input.number('Trend EMA length', 200, { min: 20, max: 500 });
const myShowCh = input.boolean('Show channels', true);
const myShowSig = input.boolean('Show markers', true);
const myChan = (_src, _n, _isHigh) => close.map((_c, _i) => {
	// highest/lowest over the n bars ending one bar earlier ([1])
	if (_i < _n) return null;
	let myV = _isHigh ? -Infinity : Infinity;
	for (let myK = _i - _n; myK < _i; myK += 1) myV = _isHigh ? Math.max(myV, _src[myK]) : Math.min(myV, _src[myK]);
	return myV;
});
const myEntryHi = myChan(high, myEntryLen, true), myEntryLo = myChan(low, myEntryLen, false);
const myExitHi = myChan(high, myExitLen, true), myExitLo = myChan(low, myExitLen, false);
const myTrendEma = ema(close, myTrendLen);
const myLongEntry = close.map(() => false), myShortEntry = close.map(() => false);
const myLongExit = close.map(() => false), myShortExit = close.map(() => false);
const myPosArr = close.map(() => 0);
let myPos = 0;
for (let myI = 0; myI < close.length; myI += 1) {
	const myLongOk = !myUseTrend || (myTrendEma[myI] !== null && close[myI] > myTrendEma[myI]);
	const myShortOk = !myUseTrend || (myTrendEma[myI] !== null && close[myI] < myTrendEma[myI]);
	const myLe = myEntryHi[myI] !== null && high[myI] > myEntryHi[myI] && myLongOk && myPos <= 0;
	const mySe = myEntryLo[myI] !== null && low[myI] < myEntryLo[myI] && myShortOk && myPos >= 0;
	const myLx = myPos === 1 && myExitLo[myI] !== null && low[myI] < myExitLo[myI];
	const mySx = myPos === -1 && myExitHi[myI] !== null && high[myI] > myExitHi[myI];
	myLongEntry[myI] = myLe; myShortEntry[myI] = mySe; myLongExit[myI] = myLx; myShortExit[myI] = mySx;
	if (myLe) myPos = 1;
	else if (mySe) myPos = -1;
	else if (myLx || mySx) myPos = 0;
	myPosArr[myI] = myPos;
}
const myGate = (_s, _show) => _s.map(_v => _show ? _v : null);
paint(myGate(myEntryHi, myShowCh), { name: 'Entry High', color: 'rgba(0,128,128,0.7)' });
paint(myGate(myEntryLo, myShowCh), { name: 'Entry Low', color: 'rgba(0,128,128,0.7)' });
color_cloud(myGate(myEntryHi, myShowCh), myGate(myEntryLo, myShowCh), 'rgba(0,128,128,0.06)', 'rgba(0,128,128,0.06)', 'Channel Up', 'Channel Dn');
paint(myGate(myExitHi, myShowCh), { name: 'Exit High', color: 'rgba(255,152,0,0.5)' });
paint(myGate(myExitLo, myShowCh), { name: 'Exit Low', color: 'rgba(255,152,0,0.5)' });
paint(myGate(myTrendEma, myUseTrend), { name: 'Trend EMA', color: 'rgba(128,128,128,0.6)', thickness: 2 });
paint(myLongEntry.map(_f => (myShowSig && _f) ? constants.icons.triangle_up : null), { name: 'Long Entry Mark', style: 'labels_below', color: 'teal' });
paint(myShortEntry.map(_f => (myShowSig && _f) ? constants.icons.triangle_down : null), { name: 'Short Entry Mark', style: 'labels_above', color: 'red' });
paint(myLongExit.map((_f, _i) => (myShowSig && (_f || myShortExit[_i])) ? constants.icons.triangle_down : null), { name: 'Exit Mark', style: 'labels_above', color: 'orange' });
const myLast = close.length - 1;
const myPosText = myPosArr[myLast] === 1 ? 'LONG' : (myPosArr[myLast] === -1 ? 'SHORT' : 'FLAT');
const myBull = myTrendEma[myLast] !== null && close[myLast] > myTrendEma[myLast];
paint_overlay('Turtle Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Turtle state', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myPosText, color: 'white', background_color: myPosArr[myLast] === 1 ? 'teal' : (myPosArr[myLast] === -1 ? 'red' : 'gray') }] },
		{ cells: [{ text: 'Regime', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myBull ? 'Bull' : 'Bear', color: 'white', background_color: myBull ? 'rgba(0,128,128,0.6)' : 'rgba(220,0,0,0.6)' }] }
	]
});
register_signal(myLongEntry, 'Long Entry Signal');
register_signal(myShortEntry, 'Short Entry Signal');
register_signal(myLongExit, 'Long Exit Signal');
register_signal(myShortExit, 'Short Exit Signal');
