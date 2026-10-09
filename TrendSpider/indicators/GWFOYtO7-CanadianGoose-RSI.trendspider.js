/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RSI SIGNAL
 * Author       : icenet_ml
 * Source URL   : https://www.tradingview.com/script/GWFOYtO7-CanadianGoose-RSI
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : CanadianGoose RSI_TV
 *
 * Deviations from the original: Pine-exact RSI; GOOSE ARMED status table not carried over; alertcondition mapped to
 *   signals.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('CanadianGoose RSI_TV', 'lower');
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const mySigLength = input.number('Signal EMA Length', 14, { min: 1, max: 200 });
const myUpperLevel = input.number('Upper Alert Level', 65, { min: 0, max: 100 });
const myLowerLevel = input.number('Lower Alert Level', 35, { min: 0, max: 100 });
// pine-parity: ta.rsi uses SMA-seeded RMA of gains/losses
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myGain = close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0));
const myLoss = close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0));
const myAvgGain = myRma(myGain, myRsiLength);
const myAvgLoss = myRma(myLoss, myRsiLength);
const myRsiVal = myAvgGain.map((_g, _i) => (_g === null || myAvgLoss[_i] === null) ? null : (myAvgLoss[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myAvgLoss[_i])));
const mySigLine = ema(myRsiVal, mySigLength);
const myUpperSignal = series_of(false);
const myLowerSignal = series_of(false);
let myArmed = true;
for (let myIndex = 1; myIndex < mySigLine.length; myIndex += 1) {
	const myCurr = mySigLine[myIndex];
	const myPrev = mySigLine[myIndex - 1];
	if (myCurr === null || myPrev === null) continue;
	if ((myCurr > 50 && myPrev <= 50) || (myCurr < 50 && myPrev >= 50)) myArmed = true;
	const myUp = myArmed && myCurr > myUpperLevel && myPrev <= myUpperLevel;
	const myDn = myArmed && myCurr < myLowerLevel && myPrev >= myLowerLevel;
	myUpperSignal[myIndex] = myUp;
	myLowerSignal[myIndex] = myDn;
	if (myUp || myDn) myArmed = false;
}
paint(mySigLine, { name: 'Signal', color: 'orange', thickness: 2 });
paint(horizontal_line(50), { name: 'Midline', color: 'gray' });
paint(horizontal_line(70), { name: 'Upper Level', color: 'red' });
paint(horizontal_line(30), { name: 'Lower Level', color: 'green' });
paint(horizontal_line(myUpperLevel), { name: 'Upper Alarm', color: 'green' });
paint(horizontal_line(myLowerLevel), { name: 'Lower Alarm', color: 'red' });
register_signal(myUpperSignal, 'RSI Signal Overbought');
register_signal(myLowerSignal, 'RSI Signal Oversold');
