/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Auto S/R Levels [5 Strongest]
 * Author       : jlawless6925
 * Source URL   : https://www.tradingview.com/script/pYWgIMPE-TRADING-LAB-10AM-PMH-HOD-BREAKOUT-V1
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Auto SR Levels 5 Strongest_TV
 *
 * Deviations from the original: Reviewed AI draft; pivots hand-rolled and clustered as in Pine; levels drawn as 5
 *   fixed-slot lines from the lookback start with a projection of the extension bars.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Auto SR Levels 5 Strongest_TV', 'price');
const myPivotLen = input.number('Pivot Length', 10, { min: 2, max: 20 });
const myLookback = input.number('Lookback bars', 500, { min: 100, max: 500 });
const myClusterPct = input.number('Cluster Tolerance %', 0.5, { min: 0.1, max: 2.0, step: 0.1 });
const myExtBars = input.number('Extend Forward bars', 30, { min: 1, max: 100 });
const myNLevels = input.number('Levels to Draw', 5, { min: 1, max: 5 });
const mySupColor = input.color('Support Color', 'green');
const myResColor = input.color('Resistance Color', 'red');
const MAX_LEVELS = 5;
const myN = close.length;
const myFrom = Math.max(0, myN - 1 - myLookback);
const myPivotAt = (_src, _i, _isHigh) => {
	const myP = _i - myPivotLen;
	if (myP - myPivotLen < 0) return false;
	for (let myK = myP - myPivotLen; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? (myK < myP ? !(_src[myP] > _src[myK]) : !(_src[myP] >= _src[myK])) : (myK < myP ? !(_src[myP] < _src[myK]) : !(_src[myP] <= _src[myK]))) return false;
	}
	return true;
};
// pivots confirmed inside the lookback window, clustered by price tolerance (as in the Pine arrays)
const myRaw = [];
for (let myI = myFrom; myI < myN; myI += 1) {
	if (myPivotAt(high, myI, true)) myRaw.push(high[myI - myPivotLen]);
	if (myPivotAt(low, myI, false)) myRaw.push(low[myI - myPivotLen]);
}
const myPrices = [], myHits = [];
myRaw.forEach(_p => {
	const myTol = _p * myClusterPct / 100;
	for (let myJ = 0; myJ < myPrices.length; myJ += 1) {
		if (Math.abs(myPrices[myJ] - _p) <= myTol) { myPrices[myJ] = (myPrices[myJ] * myHits[myJ] + _p) / (myHits[myJ] + 1); myHits[myJ] += 1; return; }
	}
	myPrices.push(_p); myHits.push(1);
});
const myLevels = [];
while (myLevels.length < myNLevels && myPrices.length > 0) {
	let myMaxI = 0;
	for (let myJ = 1; myJ < myHits.length; myJ += 1) if (myHits[myJ] > myHits[myMaxI]) myMaxI = myJ;
	myLevels.push(myPrices[myMaxI]);
	myPrices.splice(myMaxI, 1); myHits.splice(myMaxI, 1);
}
const myLastClose = close[myN - 1];
for (let myS = 0; myS < MAX_LEVELS; myS += 1) {
	const myHas = myS < myLevels.length;
	const myRes = myHas && myLevels[myS] >= myLastClose;
	const myLine = paint(myHas ? close.map((_c, _i) => _i >= myFrom ? myLevels[myS] : null) : close.map(() => null), { name: 'Level ' + (myS + 1), color: myRes ? myResColor : mySupColor, thickness: 2 });
	paint_projection(myLine, myHas ? Array(myExtBars).fill(myLevels[myS]) : [], { color: myRes ? myResColor : mySupColor, thickness: 2 });
}
const myNearLevel = (_c, _res) => myLevels.some(_l => (_res ? _l >= myLastClose : _l < myLastClose) && Math.abs(_c - _l) <= _l * myClusterPct / 100);
register_signal(close.map(_c => myNearLevel(_c, false)), 'Price Near Support Level');
register_signal(close.map(_c => myNearLevel(_c, true)), 'Price Near Resistance Level');
