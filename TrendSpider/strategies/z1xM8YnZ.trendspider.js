/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : BB Mean Reversion Long + SL
 * Author       : a4nti
 * Source URL   : https://www.tradingview.com/script/z1xM8YnZ
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : BB Mean Reversion Long_TV
 *
 * The Pine original, in words: buy when close crosses below the lower Bollinger band (20, 2); exit at the middle
 *   band or a 1.5 percent stop; fixed 100 units, pyramiding 3
 *
 * Deviations from the original: The Pine's limit is the middle band at the signal bar; the Long Exit signal fires on
 *   the first bar whose high reaches the current middle band. The stop is a Tester
 *   setting.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry signal emerged; exit Long
 *   Exit signal emerged; stop loss 1.5 percent; fixed quantity 100; pyramiding 3.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('BB Mean Reversion Long_TV', 'overlay');
const myN2 = input.number('SMA Period', 20, { min: 1, max: 500 });
const myK = input.number('Std Dev Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myLen = close.length;
// Bollinger bands: SMA basis, population standard deviation (Pine ta.bb / ta.stdev)
const myMid = [], myUpper = [], myLower = [];
for (let myI = 0; myI < myLen; myI += 1) {
	if (myI < myN2 - 1) { myMid.push(null); myUpper.push(null); myLower.push(null); continue; }
	let myS = 0; for (let myJ = myI - myN2 + 1; myJ <= myI; myJ += 1) myS += close[myJ];
	const myAvg = myS / myN2; let myV = 0; for (let myJ = myI - myN2 + 1; myJ <= myI; myJ += 1) myV += (close[myJ] - myAvg) * (close[myJ] - myAvg);
	const myD = Math.sqrt(myV / myN2) * myK;
	myMid.push(myAvg); myUpper.push(myAvg + myD); myLower.push(myAvg - myD);
}
const myEntry = close.map((_c, _i) => _i > 0 && myLower[_i] !== null && myLower[_i - 1] !== null && close[_i - 1] >= myLower[_i - 1] && _c < myLower[_i]);
// the Pine exits at the middle band (limit); a bar reaching the middle band is the exit signal
const myExit = close.map((_c, _i) => myMid[_i] !== null && high[_i] >= myMid[_i]);
paint(myMid, { name: 'Middle', color: 'gray' });
paint(myUpper, { name: 'Upper Band', color: 'red' });
paint(myLower, { name: 'Lower Band', color: 'green' });
paint(myEntry.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
register_signal(myEntry, 'Long Entry');
register_signal(myExit, 'Long Exit');
