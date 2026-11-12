/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 🚫🚩 RUN SIGNAL 🚩🚫
 * Author       : kitkatkit2003
 * Source URL   : https://www.tradingview.com/script/yjGV03wM-EXITING-SIGNAL
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Exiting Run Signal_TV
 *
 * Deviations from the original: Reviewed TrendSpider-AI draft, live-tested. Colour/width/extend-right options not
 *   available; higher-timeframe values lag one completed HTF bar (non-repainting).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Exiting Run Signal_TV', 'price');
const mySignalColor = input.color('Signal Color', 'red');
const [myDaily, myH4, myH2, myM15] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '240'),
	request.history(current.ticker, '120'),
	request.history(current.ticker, '15')
]);
assert(!myDaily.error, 'Error fetching Daily data: ' + myDaily.error);
assert(!myH4.error, 'Error fetching 4H data: ' + myH4.error);
assert(!myH2.error, 'Error fetching 2H data: ' + myH2.error);
assert(!myM15.error, 'Error fetching 15m data: ' + myM15.error);
// Land a higher-timeframe condition on the chart seeing only COMPLETED bars (shifted one HTF bar, L23).
const myLand = (_htf, _cond) => {
	const myPrev = _cond.map((_v, _k) => _k ? _cond[_k - 1] : null);
	return interpolate_sparse_series(land_points_onto_series(_htf.time, myPrev, time, 'le'), 'constant');
};
const myDHma = hullma(myDaily.close, 200);
const myDMom = sub(myDaily.close, shift(myDaily.close, 14)); // ta.mom(close, 14)
const myCond1 = for_every(myDaily.close, myDHma, shift(myDaily.close, 1), shift(myDHma, 1),
	(_c, _h, _cp, _hp) => _h !== null && _hp !== null && _cp !== null && _cp >= _hp && _c < _h);
const myCond2 = for_every(myDMom, shift(myDMom, 1), (_m, _mp) => _m !== null && _mp !== null && _m < 0 && _m < _mp);
const myH4Hma = hullma(myH4.close, 200);
const myCond3 = for_every(myH4Hma, myH4.close, (_h, _c) => _h !== null && _h > _c);
const myH2Hma = hullma(myH2.close, 200);
const myH2Ema = ema(myH2.close, 200);
const myH2Dist = sub(myH2Hma, myH2Ema);
const myCond4 = for_every(myH2Dist, shift(myH2Dist, 1), myH2Hma, myH2Ema,
	(_d, _dp, _h, _e) => _d !== null && _dp !== null && _d < _dp && _h > _e);
const myM15Hma = hullma(myM15.close, 200);
const myM15Ema = ema(myM15.close, 200);
const myCond5 = for_every(myM15Hma, myM15Ema, (_h, _e) => _h !== null && _e !== null && _h < _e);
const myRunSignal = for_every(myLand(myDaily, myCond1), myLand(myDaily, myCond2), myLand(myH4, myCond3),
	myLand(myH2, myCond4), myLand(myM15, myCond5),
	(_a, _b, _c, _d, _e) => Boolean(_a && _b && _c && _d && _e));
paint(for_every(myRunSignal, _s => _s ? constants.icons.triangle_down : null), { name: 'Run Signal Mark', style: 'labels_above', color: mySignalColor });
register_signal(myRunSignal, 'Run Signal');
