describe_indicator('Rolling Multi-Day VWAP', 'price');

// ─────────────────────────────
// INPUTS
// ─────────────────────────────
const myPeriodsTab = input.tab('Period Lengths (days)');
const myLen7 = myPeriodsTab.number('Short-Term Period', 7, { min: 1, max: 365 });
const myLen30 = myPeriodsTab.number('Medium-Term Period', 30, { min: 1, max: 365 });
const myLen90 = myPeriodsTab.number('Long-Term Period', 90, { min: 1, max: 365 });

const myVisibilityTab = input.tab('Visibility');
const myShow7 = myVisibilityTab.boolean('Show Short-Term VWAP', true);
const myShow30 = myVisibilityTab.boolean('Show Medium-Term VWAP', true);
const myShow90 = myVisibilityTab.boolean('Show Long-Term VWAP', true);

const mySourceTab = input.tab('Source');
const mySrcType = mySourceTab.select('Price Source', 'hlc3', ['hlc3', 'close', 'ohlc4']);

// ─────────────────────────────
// BAR COUNT CONVERSION (30-minute bars)
// 48 = 24 hours x 2 bars per hour (matches crypto/24-7 markets)
// ─────────────────────────────
const myBars7Raw = myLen7 * 48;
const myBars30Raw = myLen30 * 48;
const myBars90Raw = myLen90 * 48;

// Fetch fixed 30-minute data so values stay identical on every chart timeframe
const myData30 = await request.history(current.ticker, '30');
assert(!myData30.error, `Error fetching 30 min data: "${myData30.error}"`);

// NOTE: request.history() only returns ~300 candles when the requested
// resolution is lower than the current chart's resolution. That means a
// request for a 90-day window of 30 min candles (4320 bars) can easily
// exceed what's actually available, causing vwma() to throw
// "not_enough_candles". We clamp every window length to the amount of
// data actually returned, so the indicator never errors out; on charts
// where the full history isn't available, the longer windows will simply
// be computed over as much data as there is.
const myAvailableBars = myData30.close.length;
const myBars7 = Math.min(myBars7Raw, myAvailableBars);
const myBars30 = Math.min(myBars30Raw, myAvailableBars);
const myBars90 = Math.min(myBars90Raw, myAvailableBars);

// pick the price source on the 30 min data set
const myPrice30 = mySrcType === 'hlc3'
	? div(add(myData30.high, myData30.low, myData30.close), 3)
	: mySrcType === 'close'
		? myData30.close
		: div(add(myData30.open, myData30.high, myData30.low, myData30.close), 4);

// Volume Weighted MA over the 30 min series, acts as our rolling VWAP
const myVwap7_30 = vwma(myPrice30, myBars7);
const myVwap30_30 = vwma(myPrice30, myBars30);
const myVwap90_30 = vwma(myPrice30, myBars90);

// Land the 30 min computed values onto the current chart timeframe.
// 'le' picks the most recent completed 30 min value at or before the
// current candle's time, avoiding any lookahead bias.
const myVwap7Landed = interpolate_sparse_series(
	land_points_onto_series(myData30.time, myVwap7_30, time, 'le'),
	'constant'
);
const myVwap30Landed = interpolate_sparse_series(
	land_points_onto_series(myData30.time, myVwap30_30, time, 'le'),
	'constant'
);
const myVwap90Landed = interpolate_sparse_series(
	land_points_onto_series(myData30.time, myVwap90_30, time, 'le'),
	'constant'
);

// ─────────────────────────────
// PLOTS
// ─────────────────────────────
const myLine7 = paint(myShow7 ? myVwap7Landed : constants.empty_series, { name: 'ShortTermVWAP', color: 'yellow', thickness: 2 });
const myLine30 = paint(myShow30 ? myVwap30Landed : constants.empty_series, { name: 'MediumTermVWAP', color: 'orange', thickness: 2 });
const myLine90 = paint(myShow90 ? myVwap90Landed : constants.empty_series, { name: 'LongTermVWAP', color: 'red', thickness: 2 });

// ─────────────────────────────
// LABELS (always placed at the last candle, mirroring barstate.islast)
// ─────────────────────────────
const myLastIndex = close.length - 1;

if (myShow7 && myVwap7Landed[myLastIndex] !== null) {
	paint_label_at_line(myLine7, myLastIndex, `${myLen7}D VWAP`, { color: 'yellow', background_color: 'yellow' });
}
if (myShow30 && myVwap30Landed[myLastIndex] !== null) {
	paint_label_at_line(myLine30, myLastIndex, `${myLen30}D VWAP`, { color: 'orange', background_color: 'orange' });
}
if (myShow90 && myVwap90Landed[myLastIndex] !== null) {
	paint_label_at_line(myLine90, myLastIndex, `${myLen90}D VWAP`, { color: 'red', background_color: 'red' });
}

// ─────────────────────────────
// SCANNING / STRATEGY SIGNALS
// Cross of price above/below each rolling VWAP, usable in
// Scanners, Alerts and Strategy Tester
// ─────────────────────────────
const myCrossAbove7 = for_every(close, myVwap7Landed, (_c, _v, _prev, _i) => _i > 0 && close[_i - 1] <= myVwap7Landed[_i - 1] && _c > _v);
const myCrossBelow7 = for_every(close, myVwap7Landed, (_c, _v, _prev, _i) => _i > 0 && close[_i - 1] >= myVwap7Landed[_i - 1] && _c < _v);
register_signal(myCrossAbove7, 'Price Crosses Above Short Term VWAP');
register_signal(myCrossBelow7, 'Price Crosses Below Short Term VWAP');

const myCrossAbove30 = for_every(close, myVwap30Landed, (_c, _v, _prev, _i) => _i > 0 && close[_i - 1] <= myVwap30Landed[_i - 1] && _c > _v);
const myCrossBelow30 = for_every(close, myVwap30Landed, (_c, _v, _prev, _i) => _i > 0 && close[_i - 1] >= myVwap30Landed[_i - 1] && _c < _v);
register_signal(myCrossAbove30, 'Price Crosses Above Medium Term VWAP');
register_signal(myCrossBelow30, 'Price Crosses Below Medium Term VWAP');

const myCrossAbove90 = for_every(close, myVwap90Landed, (_c, _v, _prev, _i) => _i > 0 && close[_i - 1] <= myVwap90Landed[_i - 1] && _c > _v);
const myCrossBelow90 = for_every(close, myVwap90Landed, (_c, _v, _prev, _i) => _i > 0 && close[_i - 1] >= myVwap90Landed[_i - 1] && _c < _v);
register_signal(myCrossAbove90, 'Price Crosses Above Long Term VWAP');
register_signal(myCrossBelow90, 'Price Crosses Below Long Term VWAP');