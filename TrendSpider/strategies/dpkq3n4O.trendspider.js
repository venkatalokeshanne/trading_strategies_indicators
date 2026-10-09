/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : LinReg Scale-In Strategy
 * Author       : p_zerbst
 * Source URL   : https://www.tradingview.com/script/dpkq3n4O
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : LinReg Scale-In Strategy_TV
 *
 * The Pine original, in words: correlation of close with the bar index over 20 bars; scale in with one unit each
 *   time it crosses up through 0.25, 0.50 and 0.75 (pyramiding 3); close everything when
 *   it crosses back below 0.25
 *
 * Deviations from the original: Pyramiding is a Tester setting: the three entry signals are separate and the exit is
 *   Long Exit. Correlation is hand-rolled (Pearson).
 * Not carried over: Strategy Tester settings (set by hand): Entry any of Long Entry 25 / 50 / 75 signal
 *   emerged; exit Long Exit signal emerged; pyramiding 3; fixed quantity 1; initial
 *   capital 100000.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('LinReg Scale-In Strategy_TV', 'lower');
const myLen = input.number('Lookback Period', 20, { min: 5, max: 500 });
const myN = close.length;
// ta.correlation(close, bar_index, length): Pearson correlation of price with the bar number
const myCoeff = close.map((_c, _i) => {
	if (_i < myLen - 1) return null;
	let mySx = 0, mySy = 0, mySxx = 0, mySyy = 0, mySxy = 0;
	for (let myK = _i - myLen + 1; myK <= _i; myK += 1) { mySx += myK; mySy += close[myK]; mySxx += myK * myK; mySyy += close[myK] * close[myK]; mySxy += myK * close[myK]; }
	const myNum = myLen * mySxy - mySx * mySy, myDen = Math.sqrt((myLen * mySxx - mySx * mySx) * (myLen * mySyy - mySy * mySy));
	return myDen === 0 ? null : myNum / myDen;
});
const myXUp = (_lvl) => close.map((_c, _i) => _i > 0 && myCoeff[_i] !== null && myCoeff[_i - 1] !== null && myCoeff[_i - 1] <= _lvl && myCoeff[_i] > _lvl);
const myXDn = (_lvl) => close.map((_c, _i) => _i > 0 && myCoeff[_i] !== null && myCoeff[_i - 1] !== null && myCoeff[_i - 1] >= _lvl && myCoeff[_i] < _lvl);
paint(myCoeff, { name: 'LinReg Coefficient', color: 'blue', thickness: 2 });
paint(horizontal_line(0.75), { name: 'Level 0.75', color: 'green', style: 'dotted' });
paint(horizontal_line(0.5), { name: 'Level 0.50', color: 'yellow', style: 'dotted' });
paint(horizontal_line(0.25), { name: 'Level 0.25', color: 'orange', style: 'dotted' });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray' });
register_signal(myXUp(0.25), 'Long Entry 25');
register_signal(myXUp(0.5), 'Long Entry 50');
register_signal(myXUp(0.75), 'Long Entry 75');
register_signal(myXDn(0.25), 'Long Exit');
