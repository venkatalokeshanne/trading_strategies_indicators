/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA Distance MACD (50W / 200W)
 * Author       : utkarshikha
 * Source URL   : https://www.tradingview.com/script/C5ObHRwf-Hot-Cold-50W-200W-EMA
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EMA Distance MACD 50W 200W_TV
 *
 * Deviations from the original: Reviewed AI draft; weekly data lagged one completed bar (Avoid Repaint always on);
 *   EMA hand-rolled; table via paint_overlay; colour inputs fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EMA Distance MACD 50W 200W_TV', 'lower');
const mySlowLen = input.number('Slow EMA weekly', 200, { min: 10, max: 500 });
const myFastLen = input.number('Fast EMA weekly', 50, { min: 5, max: 500 });
const myWeekly = await request.history(current.ticker, 'W');
assert(!myWeekly.error, 'Error fetching weekly data: ' + myWeekly.error);
// SMA-seeded EMA over the weekly closes
const myEmaOf = (_n) => {
	let myAcc = null, mySum = 0;
	const myAlpha = 2 / (_n + 1);
	return myWeekly.close.map((_c, _i) => {
		if (myAcc === null) { mySum += _c; if (_i === _n - 1) myAcc = mySum / _n; return myAcc; }
		myAcc = myAlpha * _c + (1 - myAlpha) * myAcc; return myAcc;
	});
};
const myPctOf = (_n) => { const myE = myEmaOf(_n); return myWeekly.close.map((_c, _i) => myE[_i] === null ? null : (_c - myE[_i]) / myE[_i] * 100); };
// lag one completed weekly bar (Pine "avoid repaint")
const myLand = (_vals) => interpolate_sparse_series(land_points_onto_series(myWeekly.time, _vals.map((_v, _k) => _k ? _vals[_k - 1] : null), time, 'le'), 'constant');
const myLine1 = myLand(myPctOf(mySlowLen));
const myLine2 = myLand(myPctOf(myFastLen));
const myHist = myLine1.map((_v, _i) => (_v === null || myLine2[_i] === null) ? null : _v - myLine2[_i]);
const myHistColor = myHist.map((_h, _i) => {
	const myP = _i > 0 ? myHist[_i - 1] : null;
	if (_h === null || myP === null) return 'gray';
	if (_h >= 0) return _h >= myP ? '#26A69A' : 'rgba(38,166,154,0.4)';
	return _h <= myP ? '#EF5350' : 'rgba(239,83,80,0.4)';
});
paint(myHist, { name: 'Histogram', style: 'histogram', color: myHistColor });
paint(myLine1, { name: 'Line1 200W Distance', color: '#FF6D00', thickness: 2 });
paint(myLine2, { name: 'Line2 50W Distance', color: '#2962FF', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero', color: 'rgba(128,128,128,0.5)' });
register_signal(myHist.map((_h, _i) => _h !== null && _i > 0 && myHist[_i - 1] !== null && _h >= 0 && myHist[_i - 1] < 0), 'Bullish Regime Shift');
register_signal(myHist.map((_h, _i) => _h !== null && _i > 0 && myHist[_i - 1] !== null && _h <= 0 && myHist[_i - 1] > 0), 'Bearish Regime Shift');
const myLast = close.length - 1;
const myF = (_v) => _v === null ? 'n/a' : _v.toFixed(2);
const myHot = myHist[myLast] !== null && myHist[myLast] >= 0;
paint_overlay('EMA Distance Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: current.ticker, color: 'white', background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: '200W: ' + myF(myLine1[myLast]) + '%', color: '#FF6D00', background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: '50W: ' + myF(myLine2[myLast]) + '%', color: '#2962FF', background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: myHot ? 'Short-term running HOT vs long-term' : 'Short-term running COLD vs long-term', color: myHot ? '#26A69A' : '#EF5350', background_color: 'rgba(0,0,0,0.7)' }] }
	]
});
