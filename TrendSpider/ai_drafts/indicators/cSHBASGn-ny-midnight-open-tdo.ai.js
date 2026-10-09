describe_indicator('True Daily Open - NY 0000', 'price');

// NOTE: Pine's hour()/minute() with a timezone argument has no direct
// equivalent in time_of(), so we use the moment-timezone library to
// replicate "NY midnight" detection and "23:00 Kyiv" line-end logic.
const myMoment = library('moment-timezone');
const MY_NY_TZ = 'America/New_York';
const MY_KYIV_TZ = 'Europe/Kyiv';

const myTdoColor = input.color('TDO Color', '#7C4DFF');
const myLineWidth = input.number('Line Width', 2, { min: 1, max: 5 });

// Fetch 1-minute data to find the exact NY midnight open (same approach
// as request.security(..., "1", ...) in the Pine script).
const myData1m = await request.history(current.ticker, '1', { ext_session: true });
assert(!myData1m.error, `Error fetching 1min data: "${myData1m.error}"`);

// Flag every 1-minute candle that lands exactly on NY 00:00
const myIsNYMidnight = myData1m.time.map(_t => {
	const myMoment1 = myMoment.tz(_t * 1000, MY_NY_TZ);
	return myMoment1.hours() === 0 && myMoment1.minutes() === 0;
});

// Sparse series: TDO price/time only at NY midnight candles
const mySparsePrice = myData1m.open.map((_o, _i) => myIsNYMidnight[_i] ? _o : null);
const mySparseTime = myData1m.time.map((_t, _i) => myIsNYMidnight[_i] ? _t : null);

// Land those sparse points onto the current chart's time axis,
// carrying each value forward ("valuewhen" equivalent)
const myLandedPrice = land_points_onto_series(myData1m.time, mySparsePrice, time, 'le');
const myLandedTime = land_points_onto_series(myData1m.time, mySparseTime, time, 'le');

const myTdoPriceSeries = interpolate_sparse_series(myLandedPrice, 'constant');
const myTdoTimeSeries = interpolate_sparse_series(myLandedTime, 'constant');

// For every bar, compute "23:00 Kyiv" of the Kyiv calendar date
// corresponding to the TDO's NY-midnight timestamp
const myLineEndSeries = myTdoTimeSeries.map(_t => {
	if (_t === null) {
		return null;
	}

	const myKyivMoment = myMoment.tz(_t * 1000, MY_KYIV_TZ);
	const myEndMoment = myMoment.tz(
		[myKyivMoment.year(), myKyivMoment.month(), myKyivMoment.date(), 23, 0, 0],
		MY_KYIV_TZ
	);

	return myEndMoment.unix();
});

// Mask: only show the TDO line from its own NY-midnight bar
// through 23:00 Kyiv of that calendar day (mimics the per-day
// line.new()/line.delete() lifecycle from the Pine script)
const myTdoLineMasked = time.map((_t, _i) => {
	const myTdoAtIndex = myTdoTimeSeries[_i];

	if (myTdoAtIndex === null) {
		return null;
	}

	return (_t >= myTdoAtIndex && _t <= myLineEndSeries[_i]) ? myTdoPriceSeries[_i] : null;
});

const myTdoLinePainted = paint(myTdoLineMasked, {
	name: 'TDO',
	style: 'ladder',
	color: myTdoColor,
	thickness: myLineWidth
});

// Place a single "TDO" label on the most recent visible segment
// (TrendSpider does not support dynamically created/deleted per-day
// label objects like Pine's label.new()/label.delete())
const myLastIndex = myTdoLineMasked.length - 1;

if (myTdoLineMasked[myLastIndex] !== null) {
	paint_label_at_line(myTdoLinePainted, myLastIndex, 'TDO', { color: myTdoColor });
}

// Scanning / strategy signals
const myNewTdoSignal = myTdoTimeSeries.map((_t, _i) =>
	_i > 0 && _t !== null && _t !== myTdoTimeSeries[_i - 1]
);
register_signal(myNewTdoSignal, 'New TDO');

const myPriceAboveTdo = close.map((_c, _i) =>
	myTdoPriceSeries[_i] !== null && _c > myTdoPriceSeries[_i]
);
register_signal(myPriceAboveTdo, 'Price Above TDO');

const myPriceBelowTdo = close.map((_c, _i) =>
	myTdoPriceSeries[_i] !== null && _c < myTdoPriceSeries[_i]
);
register_signal(myPriceBelowTdo, 'Price Below TDO');