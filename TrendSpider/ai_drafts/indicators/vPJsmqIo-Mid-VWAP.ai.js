describe_indicator('Mid VWAP', 'price');

// NOTE: This is an approximation of the original Pine Script.
// TrendSpider Custom JS API has no equivalent of Pine's
// input.session(), timeframe.change(), bar time() session
// detection with custom time zones, or bgcolor(). The anchor
// types below are reproduced using available building blocks
// (current.session, time_of(), bar_at()) which gives very
// close but not pixel-perfect behavior for session-based
// anchors (RTH, RTH Stretch, Euro) and for pure clock-based
// anchors (Minute, Half hour, Hour, Four hour, Eight hour).
// Day, Week, Month, Quarter, Year, Bar, Chart and Opt Exp
// anchors are reproduced faithfully.

const myAnchorTab = input.tab('Anchor');
const myAnchorType = myAnchorTab.select('Anchor period', 'Day', [
	'Chart', 'Minute', 'Half hour', 'Hour', 'Four hour', 'Eight hour',
	'RTH', 'RTH Stretch', 'Euro', 'Day', 'Week', 'Month', 'Quarter',
	'Opt Exp', 'Year', 'Bar'
]);

const myVwapTab = input.tab('VWAP');
const mySourceName = myVwapTab.select('Source', 'hlc3', constants.price_source_options);
const myBreakLine = myVwapTab.boolean('Break at period boundary', true);

const myStyleTab = input.tab('Style');
const myShowCloud = myStyleTab.boolean('Mid VWAP cloud', true);
const myUpColor = myStyleTab.color('Cloud VWAP above mid', 'green');
const myDnColor = myStyleTab.color('Cloud VWAP below mid', 'red');
const myCloudOpacity = myStyleTab.number('Cloud transparency', 82, { min: 0, max: 100 });

const mySource = market[mySourceName];

// ═══ Helper: detect "new period" boolean per candle ═══════
const myNewPeriod = series_of(false);

const mySessionStartHour = current.session.start.hours;
const mySessionStartMinute = current.session.start.minutes;
const mySessionEndHour = current.session.end.hours;
const mySessionEndMinute = current.session.end.minutes;

const myTimeParts = time.map(_t => time_of(_t));

const myInRth = myTimeParts.map(_p => {
	const myMinutesOfDay = _p.hours * 60 + _p.minutes;
	const myStart = mySessionStartHour * 60 + mySessionStartMinute;
	const myEnd = mySessionEndHour * 60 + mySessionEndMinute;
	return myMinutesOfDay >= myStart && myMinutesOfDay < myEnd;
});

const myInEuro = myTimeParts.map(_p => _p.hours === 3 && _p.minutes === 0);

for (let myCandleIndex = 0; myCandleIndex < time.length; myCandleIndex += 1) {
	if (myCandleIndex === 0) {
		myNewPeriod[myCandleIndex] = true;
		continue;
	}

	const myCurrentParts = myTimeParts[myCandleIndex];
	const myPreviousParts = myTimeParts[myCandleIndex - 1];

	const myRthOpen = myInRth[myCandleIndex] && !myInRth[myCandleIndex - 1];
	const myRthClose = !myInRth[myCandleIndex] && myInRth[myCandleIndex - 1];
	const myEuroOpen = myInEuro[myCandleIndex] && !myInEuro[myCandleIndex - 1];

	// Third Friday option expiration month index
	const myOpexIndexFor = _parts => {
		const myFirstOfMonth = Date.UTC(_parts.year, _parts.month, 1) / 1000;
		const myDow1 = time_of(myFirstOfMonth).dayOfWeek;
		const myFirstFriday = 1 + Math.round(((6 - myDow1 + 7) % 7));
		const myThirdFriday = myFirstFriday + 14;
		return _parts.year * 12 + _parts.month + (_parts.dayOfMonth > myThirdFriday ? 1 : 0);
	};

	let myResult = false;

	switch (myAnchorType) {
		case 'Chart':
			myResult = false;
			break;
		case 'Bar':
			myResult = true;
			break;
		case 'Minute':
			myResult = Math.floor(time[myCandleIndex] / 60) !== Math.floor(time[myCandleIndex - 1] / 60);
			break;
		case 'Half hour':
			myResult = Math.floor(time[myCandleIndex] / 1800) !== Math.floor(time[myCandleIndex - 1] / 1800);
			break;
		case 'Hour':
			myResult = Math.floor(time[myCandleIndex] / 3600) !== Math.floor(time[myCandleIndex - 1] / 3600);
			break;
		case 'Four hour':
			myResult = Math.floor(time[myCandleIndex] / 14400) !== Math.floor(time[myCandleIndex - 1] / 14400);
			break;
		case 'Eight hour':
			myResult = Math.floor(time[myCandleIndex] / 28800) !== Math.floor(time[myCandleIndex - 1] / 28800);
			break;
		case 'RTH':
			myResult = myRthOpen || myRthClose;
			break;
		case 'RTH Stretch':
			myResult = myRthOpen;
			break;
		case 'Euro':
			myResult = myRthOpen || myRthClose || myEuroOpen;
			break;
		case 'Day':
			myResult = myCurrentParts.dayOfYear !== myPreviousParts.dayOfYear || myCurrentParts.year !== myPreviousParts.year;
			break;
		case 'Week':
			myResult = myCurrentParts.weekOfYear !== myPreviousParts.weekOfYear || myCurrentParts.year !== myPreviousParts.year;
			break;
		case 'Month':
			myResult = myCurrentParts.month !== myPreviousParts.month || myCurrentParts.year !== myPreviousParts.year;
			break;
		case 'Quarter':
			myResult = myCurrentParts.quarter !== myPreviousParts.quarter || myCurrentParts.year !== myPreviousParts.year;
			break;
		case 'Opt Exp':
			myResult = myOpexIndexFor(myCurrentParts) !== myOpexIndexFor(myPreviousParts);
			break;
		case 'Year':
			myResult = myCurrentParts.year !== myPreviousParts.year;
			break;
		default:
			myResult = false;
	}

	myNewPeriod[myCandleIndex] = myResult;
}

// ═══ VWAP + Mid computation ════════════════════════════════
const myVwapValue = series_of(null);
const myMidValue = series_of(null);

let myVolumeSum = null;
let myVolumePriceSum = null;
let myPeriodHigh = null;
let myPeriodLow = null;

for (let myCandleIndex = 0; myCandleIndex < time.length; myCandleIndex += 1) {
	const myRoll = myNewPeriod[myCandleIndex] || myVolumeSum === null;

	if (myRoll) {
		myVolumeSum = volume[myCandleIndex];
		myVolumePriceSum = volume[myCandleIndex] * mySource[myCandleIndex];
		myPeriodHigh = high[myCandleIndex];
		myPeriodLow = low[myCandleIndex];
	}
	else {
		myVolumeSum += volume[myCandleIndex];
		myVolumePriceSum += volume[myCandleIndex] * mySource[myCandleIndex];
		myPeriodHigh = Math.max(myPeriodHigh, high[myCandleIndex]);
		myPeriodLow = Math.min(myPeriodLow, low[myCandleIndex]);
	}

	myVwapValue[myCandleIndex] = myVolumeSum > 0 ? myVolumePriceSum / myVolumeSum : null;
	myMidValue[myCandleIndex] = (myPeriodHigh + myPeriodLow) / 2;
}

// ═══ Apply "break at period boundary" ══════════════════════
const myVwapPlotSeries = series_of(null);
const myMidPlotSeries = series_of(null);

for (let myCandleIndex = 0; myCandleIndex < time.length; myCandleIndex += 1) {
	const myBreakHere = myBreakLine && myNewPeriod[myCandleIndex];
	myVwapPlotSeries[myCandleIndex] = myBreakHere ? null : myVwapValue[myCandleIndex];
	myMidPlotSeries[myCandleIndex] = myBreakHere ? null : myMidValue[myCandleIndex];
}

paint(myVwapPlotSeries, { name: 'VWAP', color: '#e8c84a', thickness: 2 });
paint(myMidPlotSeries, { name: 'Mid', color: 'gray', thickness: 1 });

// Cloud fill, colored by whether VWAP is above or below Mid
color_cloud(
	myVwapPlotSeries,
	myMidPlotSeries,
	myUpColor,
	myDnColor,
	'VwapAboveMid',
	'VwapBelowMid',
	myShowCloud ? (1 - myCloudOpacity / 100) : 0
);

// ═══ Signals for scanners, alerts and strategies ═══════════
const myVwapAboveMidSignal = for_every(myVwapValue, myMidValue, (_vwap, _mid) => _vwap !== null && _mid !== null && _vwap > _mid);
const myVwapBelowMidSignal = for_every(myVwapValue, myMidValue, (_vwap, _mid) => _vwap !== null && _mid !== null && _vwap < _mid);
const myNewPeriodSignal = for_every(series_of(0), (_x, _prev, _idx) => myNewPeriod[_idx]);
const myVwapCrossAboveMidSignal = for_every(myVwapValue, myMidValue, (_vwap, _mid, _prev, _idx) => {
	if (_idx === 0 || _vwap === null || _mid === null) return false;
	const myPrevVwap = myVwapValue[_idx - 1];
	const myPrevMid = myMidValue[_idx - 1];
	if (myPrevVwap === null || myPrevMid === null) return false;
	return _vwap > _mid && myPrevVwap <= myPrevMid;
});
const myVwapCrossBelowMidSignal = for_every(myVwapValue, myMidValue, (_vwap, _mid, _prev, _idx) => {
	if (_idx === 0 || _vwap === null || _mid === null) return false;
	const myPrevVwap = myVwapValue[_idx - 1];
	const myPrevMid = myMidValue[_idx - 1];
	if (myPrevVwap === null || myPrevMid === null) return false;
	return _vwap < _mid && myPrevVwap >= myPrevMid;
});

register_signal(myVwapAboveMidSignal, 'VWAP Above Mid');
register_signal(myVwapBelowMidSignal, 'VWAP Below Mid');
register_signal(myVwapCrossAboveMidSignal, 'VWAP Crosses Above Mid');
register_signal(myVwapCrossBelowMidSignal, 'VWAP Crosses Below Mid');
register_signal(myNewPeriodSignal, 'New Period Started');