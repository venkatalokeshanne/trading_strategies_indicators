/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Daily ATR Bands
 * Author       : getrich03
 * Source URL   : https://www.tradingview.com/script/cCH7ieax
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Daily ATR Bands_TV
 *
 * The Pine original, in words: daily EMA(20) +/- 1, 2 and 3 x daily ATR(14), drawn on any chart.
 *
 * Deviations from the original: fixed from the AI draft, which landed each day's values at the day's OPEN
 *   (look-ahead intraday): intraday bars use the previous completed day; the Pine shows
 *   the new value on the day's last bar. Band-cross signals added.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Daily ATR Bands_TV', 'price');

const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 100 });
const myMaLength = input.number('Base EMA Length', 20, { min: 1, max: 300 });

// Fetch Daily OHLC data to replicate request.security() behavior
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching daily data: ' + myDailyData.error);

// Compute Daily EMA (base) and Daily ATR, exactly as Pine's ta.ema/ta.atr
const myDailyBase = ema(myDailyData.close, myMaLength);
const myDailyAtr = atr(myDailyData.high, myDailyData.low, myDailyData.close, myAtrLength);

// Land daily values onto the current chart's time series.
// Using 'le' (less-or-equal) + 'constant' interpolation reproduces
// gaps_off/lookahead_off: each intraday candle gets the most recent
// COMPLETED daily value available at or before its own time, with no
// forward-looking / repainting.
// No look-ahead: intraday bars use the previous completed day (Pine lookahead_off).
const myIntraday = /^\d+$/.test(String(current.resolution));
const myLag = _s => myIntraday ? _s.map((_v, _k) => (_k === 0 ? null : _s[_k - 1])) : _s;
const myBaseLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myLag(myDailyBase), time, 'le'),
	'constant'
);
const myAtrLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myLag(myDailyAtr), time, 'le'),
	'constant'
);

// ATR Bands
const myUpper1 = add(myBaseLanded, myAtrLanded);
const myLower1 = sub(myBaseLanded, myAtrLanded);

const myUpper2 = add(myBaseLanded, mult(myAtrLanded, 2));
const myLower2 = sub(myBaseLanded, mult(myAtrLanded, 2));

const myUpper3 = add(myBaseLanded, mult(myAtrLanded, 3));
const myLower3 = sub(myBaseLanded, mult(myAtrLanded, 3));

paint(myUpper1, { name: 'Upper 1 ATR', color: 'gray', thickness: 1 });
paint(myLower1, { name: 'Lower 1 ATR', color: 'gray', thickness: 1 });

paint(myUpper2, { name: 'Upper 2 ATR', color: 'gray', thickness: 1 });
paint(myLower2, { name: 'Lower 2 ATR', color: 'gray', thickness: 1 });

paint(myUpper3, { name: 'Upper 3 ATR', color: 'gray', thickness: 1 });
paint(myLower3, { name: 'Lower 3 ATR', color: 'gray', thickness: 1 });

// Signals for scanners/alerts/strategy tester: price crossing the bands
const myCrossAboveUpper1 = for_every(close, myUpper1, shift(close, 1), shift(myUpper1, 1),
	(_c, _u, _pc, _pu) => _pu !== null && _u !== null && _pc <= _pu && _c > _u);
const myCrossBelowLower1 = for_every(close, myLower1, shift(close, 1), shift(myLower1, 1),
	(_c, _l, _pc, _pl) => _pl !== null && _l !== null && _pc >= _pl && _c < _l);

const myCrossAboveUpper2 = for_every(close, myUpper2, shift(close, 1), shift(myUpper2, 1),
	(_c, _u, _pc, _pu) => _pu !== null && _u !== null && _pc <= _pu && _c > _u);
const myCrossBelowLower2 = for_every(close, myLower2, shift(close, 1), shift(myLower2, 1),
	(_c, _l, _pc, _pl) => _pl !== null && _l !== null && _pc >= _pl && _c < _l);

const myCrossAboveUpper3 = for_every(close, myUpper3, shift(close, 1), shift(myUpper3, 1),
	(_c, _u, _pc, _pu) => _pu !== null && _u !== null && _pc <= _pu && _c > _u);
const myCrossBelowLower3 = for_every(close, myLower3, shift(close, 1), shift(myLower3, 1),
	(_c, _l, _pc, _pl) => _pl !== null && _l !== null && _pc >= _pl && _c < _l);

register_signal(myCrossAboveUpper1, 'Cross Above Upper 1 ATR');
register_signal(myCrossBelowLower1, 'Cross Below Lower 1 ATR');
register_signal(myCrossAboveUpper2, 'Cross Above Upper 2 ATR');
register_signal(myCrossBelowLower2, 'Cross Below Lower 2 ATR');
register_signal(myCrossAboveUpper3, 'Cross Above Upper 3 ATR');
register_signal(myCrossBelowLower3, 'Cross Below Lower 3 ATR');
