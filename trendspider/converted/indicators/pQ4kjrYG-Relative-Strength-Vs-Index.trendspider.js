/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Relative Strength
 * Author       : bhavaniprasadk
 * Source URL   : https://www.tradingview.com/script/pQ4kjrYG-Relative-Strength-Vs-Index
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Relative Strength vs Index_TV
 *
 * Deviations from the original: Pine presets (NIFTY/SENSEX indices) are not available in TrendSpider: US index ETFs
 *   SPY/QQQ/IWM/DIA offered instead; dotted zero line not available.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Relative Strength vs Index_TV', 'lower');
// The Pine presets (NIFTY 50, NIFTY 500, NIFTY BANK, NIFTY MIDCAP 100, SENSEX) are not available in TrendSpider
// (request.history fails for every NSE/BSE index symbol), so US index ETFs are offered instead.
const myIndexChoice = input.select('Comparative Index', 'SPY', ['SPY', 'QQQ', 'IWM', 'DIA']);
const myLength = input.number('Period', 50, { min: 1, max: 1000 });
const myShowMa = input.boolean('Show Moving Average', true);
const myLengthMa = input.number('MA Period', 10, { min: 1, max: 1000 });
const myComp = await request.history(myIndexChoice, current.resolution);
assert(!myComp.error && myComp.close && myComp.close.length > 0, 'Could not fetch comparative symbol ' + myIndexChoice);
const myCompClose = interpolate_sparse_series(land_points_onto_series(myComp.time, myComp.close, time, 'le'), 'constant');
const myRes = close.map((_c, _i) => {
	if (_i < myLength) return null;
	const myB0 = close[_i - myLength], myC0 = myCompClose[_i - myLength], myC1 = myCompClose[_i];
	if (myC0 === null || myC1 === null || myC0 === 0 || myC1 === 0 || myB0 === 0) return null;
	return (_c / myB0) / (myC1 / myC0) - 1;
});
const myMa = myRes.map((_v, _i) => {
	if (_i < myLengthMa - 1) return null;
	let mySum = 0;
	for (let myK = _i - myLengthMa + 1; myK <= _i; myK += 1) { if (myRes[myK] === null) return null; mySum += myRes[myK]; }
	return mySum / myLengthMa;
});
paint(horizontal_line(0), { name: 'Zero', color: 'gray' });
paint(myRes, { name: 'RS', color: 'green', thickness: 2 });
paint(myMa.map(_v => myShowMa ? _v : null), { name: 'RS MA', color: 'red', thickness: 1 });
const myPrev = shift(myRes, 1);
const myPrevMa = shift(myMa, 1);
register_signal(myRes.map(_r => _r !== null && _r > 0), 'RS Above Zero');
register_signal(for_every(myRes, myPrev, (_r, _p) => _r !== null && _p !== null && _r > 0 && _p <= 0), 'RS Crosses Above Zero');
register_signal(for_every(myRes, myPrev, (_r, _p) => _r !== null && _p !== null && _r < 0 && _p >= 0), 'RS Crosses Below Zero');
register_signal(myRes.map((_r, _i) => _r !== null && myMa[_i] !== null && _r > myMa[_i]), 'RS Above MA');
register_signal(for_every(myRes, myMa, myPrev, myPrevMa, (_r, _m, _pr, _pm) => _r !== null && _m !== null && _pr !== null && _pm !== null && _r > _m && _pr <= _pm), 'RS Crosses Above MA');
register_signal(for_every(myRes, myMa, myPrev, myPrevMa, (_r, _m, _pr, _pm) => _r !== null && _m !== null && _pr !== null && _pm !== null && _r < _m && _pr >= _pm), 'RS Crosses Below MA');
