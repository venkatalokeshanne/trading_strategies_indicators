describe_indicator('10AM Reference Level', 'price');

// NOTE: TrendSpider does not expose timezone conversion to an
// arbitrary timezone like "America/New_York" directly. We use
// time_of(), which returns hour/minute in the exchange's own
// timezone. For US equities this is normally America/New_York,
// so results should match the Pine script on US stock charts,
// but may differ on other asset types/timezones.

const myKeyHour = input.number('Reference hour (ET)', 10, { min: 0, max: 23 });
const myKeyMinute = input.number('Reference minute (ET)', 0, { min: 0, max: 59 });
const myShowLabel = input.boolean('Show price label', true);

const myKeyOpen = series_of(null);
const myKeyCaptured = series_of(false);

let myPrevDay = null;
let myCurrentOpen = null;
let myCurrentCaptured = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = myTimeInfo.year * 10000 + (myTimeInfo.month + 1) * 100 + myTimeInfo.dayOfMonth;

	const myNewDay = myPrevDay === null || myDayKey !== myPrevDay;
	if (myNewDay) {
		myCurrentOpen = null;
		myCurrentCaptured = false;
	}

	const myIsKeyBar = !isNaN(current.resolution) && myTimeInfo.hours === myKeyHour && myTimeInfo.minutes === myKeyMinute;

	if (!myCurrentCaptured && myIsKeyBar) {
		myCurrentOpen = open[myIndex];
		myCurrentCaptured = true;
	}

	myKeyOpen[myIndex] = myCurrentCaptured ? myCurrentOpen : null;
	myKeyCaptured[myIndex] = myCurrentCaptured;

	myPrevDay = myDayKey;
}

// style "ladder" is the closest built-in equivalent to Pine's
// plot.style_linebr: it holds the value flat without interpolating
// over the null gaps.
const myLinePainted = paint(myKeyOpen, { name: 'Key Open', color: '#1E90FF', thickness: 2, style: 'ladder' });

// Find last captured index to place the label, mirroring the
// barstate.islast label placement in the Pine script.
let myLastCapturedIndex = -1;
for (let myIndex = close.length - 1; myIndex >= 0; myIndex -= 1) {
	if (myKeyCaptured[myIndex]) {
		myLastCapturedIndex = myIndex;
		break;
	}
}

if (myShowLabel && myLastCapturedIndex >= 0) {
	paint_label_at_line(myLinePainted, myLastCapturedIndex, 'Reference Level', {
		color: 'white',
		background_color: '#1E90FF',
		vertical_align: 'middle'
	});
}

// Scanning/strategy signals
const myKeyBarSignal = for_every(myKeyCaptured, (_c, _p, _i) => {
	return _i > 0 ? (myKeyCaptured[_i] && !myKeyCaptured[_i - 1]) : myKeyCaptured[_i];
});
register_signal(myKeyBarSignal, 'Key Bar Captured');

const myCrossAbove = for_every(close, myKeyOpen, (_close, _level, _prev, _i) => {
	if (_i === 0 || _level === null || myKeyOpen[_i - 1] === null) return false;
	return close[_i - 1] <= myKeyOpen[_i - 1] && _close > _level;
});
register_signal(myCrossAbove, 'Cross Above Level');

const myCrossBelow = for_every(close, myKeyOpen, (_close, _level, _prev, _i) => {
	if (_i === 0 || _level === null || myKeyOpen[_i - 1] === null) return false;
	return close[_i - 1] >= myKeyOpen[_i - 1] && _close < _level;
});
register_signal(myCrossBelow, 'Cross Below Level');