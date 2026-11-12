/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : P/E Ratio Quarter Vs Median [swingtradingedge.com]
 * Author       : ManasAhuja
 * Source URL   : https://www.tradingview.com/script/2cxYvQwT-P-E-Ratio-Quarter-Vs-Median-swingtradingedge
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : PE Ratio Quarter Vs Median_TV
 *
 * Deviations from the original: Newer version of SpkcCfwQ; converted with the same logic (market cap / TTM net
 *   income; shares from market cap / close at report date) and shares its saved
 *   TrendSpider script; the EPS TTM source, quarter lines, shading and panel/credit
 *   tables are not carried over.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('PE Ratio Quarter Vs Median_TV', 'lower');
const myLength = input.number('Median Lookback', 250, { min: 30, max: 2000 });
const myShowMedian = input.boolean('Show Median Line', true);
const myQuarters = 40;
const myFund = await request.fundamental(current.ticker, ['market_cap', 'net_income'], myQuarters);
assert(!myFund.error, 'Error fetching fundamentals: ' + myFund.error);
// records come newest first; reportdate is in seconds
const myCap = [...myFund.market_cap].reverse();
const myNi = [...myFund.net_income].reverse();
// shares outstanding is not available as a metric: approximate it as market cap / close at the report date
const myCloseAt = (_t) => { let myK = -1; for (let myI = 0; myI < time.length; myI += 1) { if (time[myI] <= _t) myK = myI; else break; } return myK >= 0 ? close[myK] : null; };
const myShares = myCap.map(_r => { const myC = myCloseAt(_r.reportdate); return myC ? _r.value / myC : null; });
const myNiTtm = myNi.map((_r, _i) => _i < 3 ? null : myNi[_i].value + myNi[_i - 1].value + myNi[_i - 2].value + myNi[_i - 3].value);
const myLandF = (_recs, _vals) => interpolate_sparse_series(land_points_onto_series(_recs.map(_r => _r.reportdate), _vals, time, 'le'), 'constant');
const mySharesLanded = myLandF(myCap, myShares);
const myNiLanded = myLandF(myNi, myNiTtm);
const myPe = close.map((_c, _i) => (mySharesLanded[_i] === null || myNiLanded[_i] === null || myNiLanded[_i] === 0) ? null : _c * mySharesLanded[_i] / myNiLanded[_i]);
const myMedian = myPe.map((_v, _i) => {
	if (_i < myLength - 1) return null;
	const myWin = [];
	for (let myK = _i - myLength + 1; myK <= _i; myK += 1) { if (myPe[myK] === null) return null; myWin.push(myPe[myK]); }
	myWin.sort((_a, _b) => _a - _b);
	const myMid = Math.floor(myWin.length / 2);
	return myWin.length % 2 === 0 ? (myWin[myMid - 1] + myWin[myMid]) / 2 : myWin[myMid];
});
paint(myPe, { name: 'Price to Earnings Ratio', color: myPe.map((_v, _i) => (_v === null || myMedian[_i] === null) ? 'gray' : (_v > myMedian[_i] ? '#ef5350' : '#26a69a')), thickness: 1 });
paint(myMedian.map(_v => myShowMedian ? _v : null), { name: 'Median PE', color: 'white', thickness: 2 });
register_signal(myPe.map((_v, _i) => _v !== null && myMedian[_i] !== null && _v < myMedian[_i]), 'PE Below Median');
register_signal(myPe.map((_v, _i) => _v !== null && myMedian[_i] !== null && _v > myMedian[_i]), 'PE Above Median');
