/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 200W EMA Heat
 * Author       : utkarshikha
 * Source URL   : https://www.tradingview.com/script/R5tatqRR-200W-EMA-Hot-Cold
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 200W EMA Heat_TV
 *
 * Deviations from the original: Reviewed AI draft; weekly data lagged one completed bar (Avoid Repaint always on);
 *   Pine percentrank and gradient colours hand-rolled; table via paint_overlay; columns
 *   as histogram.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('200W EMA Heat_TV', 'lower', { decimals: 2 });
const myEmaLength = input.number('EMA Length weekly', 200, { min: 10, max: 500 });
const myPctLookback = input.number('Percentile Lookback', 260, { min: 20, max: 1000 });
const myWeekly = await request.history(current.ticker, 'W');
assert(!myWeekly.error, 'Error fetching weekly data: ' + myWeekly.error);
// SMA-seeded EMA over the weekly closes
let myAcc = null, mySum = 0;
const myAlpha = 2 / (myEmaLength + 1);
const myEma = myWeekly.close.map((_c, _i) => {
	if (myAcc === null) { mySum += _c; if (_i === myEmaLength - 1) myAcc = mySum / myEmaLength; return myAcc; }
	myAcc = myAlpha * _c + (1 - myAlpha) * myAcc; return myAcc;
});
const myPct = myWeekly.close.map((_c, _i) => myEma[_i] === null ? null : (_c - myEma[_i]) / myEma[_i] * 100);
// ta.percentrank: share of the previous len values that are <= the current value
const myRank = myPct.map((_v, _i) => {
	if (_i < myPctLookback || _v === null) return null;
	let myCount = 0;
	for (let myK = 1; myK <= myPctLookback; myK += 1) { const myV = myPct[_i - myK]; if (myV === null) return null; if (myV <= _v) myCount += 1; }
	return myCount / myPctLookback * 100;
});
// lag one completed weekly bar (Pine "avoid repaint")
const myLand = (_vals) => interpolate_sparse_series(land_points_onto_series(myWeekly.time, _vals.map((_v, _k) => _k ? _vals[_k - 1] : null), time, 'le'), 'constant');
const myPctL = myLand(myPct);
const myRankL = myLand(myRank);
const myCold = [41, 98, 255], myNeutral = [120, 123, 134], myHot = [255, 23, 68];
const myMix = (_a, _b, _t) => 'rgb(' + _a.map((_x, _k) => Math.round(_x + (_b[_k] - _x) * _t)).join(',') + ')';
const myColors = myRankL.map(_r => _r === null ? 'gray' : (_r < 50 ? myMix(myCold, myNeutral, _r / 50) : myMix(myNeutral, myHot, (_r - 50) / 50)));
paint(myPctL, { name: 'Pct Distance 200W EMA', style: 'histogram', color: myColors });
paint(horizontal_line(0), { name: 'Zero', color: 'rgba(128,128,128,0.5)' });
const myLast = close.length - 1;
const myZone = (_r) => _r === null ? 'n/a' : (_r < 10 ? 'COLD' : (_r < 30 ? 'COOL' : (_r < 70 ? 'NEUTRAL' : (_r < 90 ? 'WARM' : 'HOT'))));
paint_overlay('200W Heat Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: current.ticker, color: 'white', background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: (myPctL[myLast] === null ? 'n/a' : myPctL[myLast].toFixed(2)) + '% from 200W EMA', color: 'white', background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: myZone(myRankL[myLast]) + ' (percentile ' + (myRankL[myLast] === null ? 'n/a' : Math.round(myRankL[myLast])) + ')', color: 'white', background_color: 'rgba(0,0,0,0.7)' }] }
	]
});
register_signal(myRankL.map(_r => _r !== null && _r >= 90), 'Overheated Top 10 Percent');
register_signal(myRankL.map(_r => _r !== null && _r <= 10), 'Deeply Cold Bottom 10 Percent');
