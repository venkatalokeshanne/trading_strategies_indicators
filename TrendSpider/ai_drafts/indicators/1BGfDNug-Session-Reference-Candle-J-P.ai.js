// EXPERIMENTAL CONVERSION FROM PINE SCRIPT.
// Due to Custom JS API limitations (no dynamic line
// arrays like Pine's line.new/line.delete), this
// version keeps only the MOST RECENT reference
// session's High/Low extended to the right (acts as
// "Previous Sessions To Keep = 1"). Multiple
// historical session lines are not supported.
describe_indicator('Session Reference Candle', 'price');

const myMoment = library('moment-timezone');

const mySessionTab = input.tab('Session Settings');
const myRefTimeframe = mySessionTab.select('Reference Timeframe', '60', constants.time_frames);
const myTimezone = mySessionTab.select('Time Zone', 'America/New_York', [
	'America/New_York',
	'America/Chicago',
	'Europe/London',
	'UTC'
]);
const mySessionRow = mySessionTab.row();
const mySessionHour = mySessionRow.number('Reference Hour', 20, { min: 0, max: 23 });
const mySessionMinute = mySessionRow.number('Reference Minute', 0, { min: 0, max: 59 });

// color_candles() has no automatic color control, so a
// custom color input is appropriate here.
const myDisplayTab = input.tab('Display Settings');
const myCandleColor = myDisplayTab.color('Reference Candle Color', 'orange');

const myHtfData = await request.history(current.ticker, myRefTimeframe);
assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);

// Determine which HTF candles are the "reference candle"
// (their close time matches the configured hour/minute
// in the chosen time zone).
const myIsRefCandleHtf = myHtfData.time.map(_t => {
	const myMomentObj = myMoment.tz(_t * 1000, myTimezone);
	return myMomentObj.hours() === mySessionHour && myMomentObj.minutes() === mySessionMinute;
});

const mySparseHigh = myHtfData.high.map((_h, _i) => myIsRefCandleHtf[_i] ? _h : null);
const mySparseLow = myHtfData.low.map((_l, _i) => myIsRefCandleHtf[_i] ? _l : null);
const mySparseFlag = myHtfData.time.map((_t, _i) => myIsRefCandleHtf[_i] ? 1 : null);

// Land HTF values onto the current chart's time series.
// 'le' picks the most recent HTF point at or before each
// current candle's time, replicating request.security()
// repeat-until-next-bar behavior.
const myLandedHigh = land_points_onto_series(myHtfData.time, mySparseHigh, time, 'le');
const myLandedLow = land_points_onto_series(myHtfData.time, mySparseLow, time, 'le');

const mySessionHighSeries = interpolate_sparse_series(myLandedHigh, 'constant');
const mySessionLowSeries = interpolate_sparse_series(myLandedLow, 'constant');

// Exact match flag for candle coloring / scanner signal:
// true only on the current-chart candle whose timestamp
// equals the HTF reference candle's own timestamp.
const myLandedFlag = land_points_onto_series(myHtfData.time, mySparseFlag, time, 'eq');
const myReferenceCandleFlag = myLandedFlag.map(_v => _v === 1);

color_candles(myReferenceCandleFlag.map(_f => _f ? myCandleColor : null));

// Crossover / crossunder detection against the session
// High/Low levels.
const myHighBreak = series_of(false);
const myLowBreak = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevHigh = mySessionHighSeries[myIndex - 1];
	const myCurHigh = mySessionHighSeries[myIndex];
	const myPrevLow = mySessionLowSeries[myIndex - 1];
	const myCurLow = mySessionLowSeries[myIndex];

	if (myCurHigh != null && myPrevHigh != null) {
		myHighBreak[myIndex] = close[myIndex] > myCurHigh && close[myIndex - 1] <= myPrevHigh;
	}
	if (myCurLow != null && myPrevLow != null) {
		myLowBreak[myIndex] = close[myIndex] < myCurLow && close[myIndex - 1] >= myPrevLow;
	}
}

paint(mySessionHighSeries, { name: 'SessionHigh', color: 'lime', thickness: 2, style: 'ladder' });
paint(mySessionLowSeries, { name: 'SessionLow', color: 'red', thickness: 2, style: 'ladder' });

register_signal(myReferenceCandleFlag, 'Reference Candle');
register_signal(myHighBreak, 'Session High Broken');
register_signal(myLowBreak, 'Session Low Broken');