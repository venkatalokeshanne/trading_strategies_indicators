/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 1H BB 2.0 & 3.0 Levels
 * Author       : ag0206
 * Source URL   : https://www.tradingview.com/script/zVUEQ3tM-1H-BB-2-0-3-0-Levels
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 1H BB 2.0 & 3.0 Levels_TV
 *
 * The Pine original, in words: the 1-hour Bollinger levels (SMA 20 +/- 2 and 3 standard deviations) on any chart.
 *
 * Deviations from the original: fixed from the AI draft, which landed each hour's bands at the hour's OPEN
 *   (look-ahead on lower timeframes): below 1H the previous completed hour is used. Band
 *   width uses TrendSpider's stdev() [VERIFY vs Pine's population stdev].
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('1H BB 2.0 & 3.0 Levels_TV', 'price');

// Length for the 1 hour Bollinger Bands
const myLength = input.number('BB Length', 20, { min: 1, max: 500 });

// Fetch 1 hour data (used as the source for the Bollinger Bands,
// just like request.security(syminfo.tickerid, "60", ...) in Pine)
const my1HData = await request.history(current.ticker, '60');
assert(!my1HData.error, 'Error fetching 1H data: ' + my1HData.error);

const myBasis1H = sma(my1HData.close, myLength);
const myStdev1H = stdev(my1HData.close, myLength);

const myUpper2_1H = add(myBasis1H, mult(myStdev1H, 2.0));
const myLower2_1H = sub(myBasis1H, mult(myStdev1H, 2.0));
const myUpper3_1H = add(myBasis1H, mult(myStdev1H, 3.0));
const myLower3_1H = sub(myBasis1H, mult(myStdev1H, 3.0));

// Land the 1H values onto the current chart's time axis.
// Pine's request.security repaints the current forming 1H bar value onto
// every lower timeframe bar within it, which is equivalent to landing with
// 'ge' (first target timestamp >= source timestamp) and constant
// (stepline-like) interpolation - this avoids look-ahead / repainting.
// No look-ahead: an hour's bands are known at its close; charts below 1H use the previous hour.
const myRes = Number(current.resolution);
const myLag = (_s) => (Number.isFinite(myRes) && myRes < 60) ? _s.map((_v, _k) => (_k === 0 ? null : _s[_k - 1])) : _s;
const myUpper2Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myLag(myUpper2_1H), time, 'le'),
	'constant'
);
const myLower2Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myLag(myLower2_1H), time, 'le'),
	'constant'
);
const myUpper3Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myLag(myUpper3_1H), time, 'le'),
	'constant'
);
const myLower3Landed = interpolate_sparse_series(
	land_points_onto_series(my1HData.time, myLag(myLower3_1H), time, 'le'),
	'constant'
);

paint(myUpper2Landed, { name: '1H Upper 2 sigma', color: '#4DA3FF', thickness: 2 });
paint(myLower2Landed, { name: '1H Lower 2 sigma', color: '#4DA3FF', thickness: 2 });
paint(myUpper3Landed, { name: '1H Upper 3 sigma', color: '#EF5350', thickness: 2 });
paint(myLower3Landed, { name: '1H Lower 3 sigma', color: '#EF5350', thickness: 2 });

// Scanning / strategy signals: cross events of close vs the bands
const myCrossAboveUpper2 = for_every(close, myUpper2Landed, shift(close, 1), shift(myUpper2Landed, 1),
	(_c, _u2, _pc, _pu2) => _pc !== null && _pu2 !== null && _pc <= _pu2 && _c > _u2
);
const myCrossBelowLower2 = for_every(close, myLower2Landed, shift(close, 1), shift(myLower2Landed, 1),
	(_c, _l2, _pc, _pl2) => _pc !== null && _pl2 !== null && _pc >= _pl2 && _c < _l2
);
const myCrossAboveUpper3 = for_every(close, myUpper3Landed, shift(close, 1), shift(myUpper3Landed, 1),
	(_c, _u3, _pc, _pu3) => _pc !== null && _pu3 !== null && _pc <= _pu3 && _c > _u3
);
const myCrossBelowLower3 = for_every(close, myLower3Landed, shift(close, 1), shift(myLower3Landed, 1),
	(_c, _l3, _pc, _pl3) => _pc !== null && _pl3 !== null && _pc >= _pl3 && _c < _l3
);

register_signal(myCrossAboveUpper2, 'Cross Above Upper 2 Sigma');
register_signal(myCrossBelowLower2, 'Cross Below Lower 2 Sigma');
register_signal(myCrossAboveUpper3, 'Cross Above Upper 3 Sigma');
register_signal(myCrossBelowLower3, 'Cross Below Lower 3 Sigma');
