/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Thermometer Oscillator
 * Author       : bashu9
 * Source URL   : https://www.tradingview.com/script/fUGqpzA0-Thermometer-Oscillator
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Thermometer Oscillator_TV
 *
 * Deviations from the original: Reviewed AI draft; MA types hand-rolled (SMA-seeded EMA/RMA); dashed/dotted level
 *   styles not available.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Thermometer Oscillator_TV', 'lower', { decimals: 0 });
const myMaLength = input.number('MA Length', 9, { min: 1, max: 500 });
const myMaType = input.select('MA Type', 'EMA', ['EMA', 'SMA', 'WMA', 'RMA']);
const myThermo = close.map((_c, _i) => {
	if (_i === 0) return 0;
	const myPc = close[_i - 1];
	const myC1 = _c > myPc ? 2 : (_c < myPc ? -2 : 0);
	const myC2 = _c > open[_i] ? 2 : (_c < open[_i] ? -2 : 0);
	const myC3 = low[_i] > myPc ? 1 : (high[_i] < myPc ? -1 : 0);
	return myC1 + myC2 + myC3;
});
let myMa;
if (myMaType === 'SMA' || myMaType === 'WMA') {
	myMa = myThermo.map((_v, _i) => {
		if (_i < myMaLength - 1) return null;
		let myNum = 0, myDen = 0;
		for (let myK = 0; myK < myMaLength; myK += 1) { const myW = myMaType === 'WMA' ? myK + 1 : 1; myNum += myThermo[_i - myMaLength + 1 + myK] * myW; myDen += myW; }
		return myNum / myDen;
	});
} else {
	// EMA and RMA are SMA-seeded as in Pine
	const myAlpha = myMaType === 'EMA' ? 2 / (myMaLength + 1) : 1 / myMaLength;
	let myAcc = null, mySum = 0;
	myMa = myThermo.map((_v, _i) => {
		if (myAcc === null) { mySum += _v; if (_i === myMaLength - 1) myAcc = mySum / myMaLength; return myAcc; }
		myAcc = myAlpha * _v + (1 - myAlpha) * myAcc; return myAcc;
	});
}
paint(myThermo, { name: 'Thermometer', color: '#2196f3', thickness: 2 });
paint(myMa, { name: 'MA', color: 'yellow', thickness: 1 });
paint(horizontal_line(5), { name: 'Plus 5', color: 'rgba(239,83,80,0.6)' });
paint(horizontal_line(3), { name: 'Plus 3', color: 'rgba(239,83,80,0.3)' });
paint(horizontal_line(0), { name: 'Zero', color: 'gray' });
paint(horizontal_line(-3), { name: 'Minus 3', color: 'rgba(38,166,154,0.3)' });
paint(horizontal_line(-5), { name: 'Minus 5', color: 'rgba(38,166,154,0.6)' });
const myPrevT = shift(myThermo, 1);
const myPrevM = shift(myMa, 1);
register_signal(myThermo.map(_t => _t >= 5), 'Thermo At Or Above Plus5');
register_signal(myThermo.map(_t => _t <= -5), 'Thermo At Or Below Minus5');
register_signal(for_every(myThermo, myMa, myPrevT, myPrevM, (_t, _m, _pt, _pm) => _m !== null && _pm !== null && _pt <= _pm && _t > _m), 'Thermo Crosses Above MA');
register_signal(for_every(myThermo, myMa, myPrevT, myPrevM, (_t, _m, _pt, _pm) => _m !== null && _pm !== null && _pt >= _pm && _t < _m), 'Thermo Crosses Below MA');
