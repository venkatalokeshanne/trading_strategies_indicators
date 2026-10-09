// NOTE: TrendSpider Custom JS has no box.new()/label.new() dynamic object
// API. This is approximated using paint() with "ladder" style for session
// high/low lines (which behave like boxes outlines) and
// paint_label_at_line() for the session name labels. Session windows are
// evaluated using time_of(), which uses the exchange's own timezone, not
// a hardcoded "America/New_York" like the original Pine script does -
// if the chart's exchange timezone is not America/New_York the session
// windows will not line up exactly with the original script.
describe_indicator('QD Session Boxes', 'price');

const myShowHistory = input.boolean('Show Historical Boxes', false);
const myLookback = input.number('Days to Show', 2, { min: 1, max: 30 });
const myLabelOffsetPct = input.number('Label Offset Percent', 5.0, { min: 0, max: 100, step: 0.5 });

const mySessionsTab = input.tab('Sessions');
const myShowAsia = mySessionsTab.boolean('Show Asia Session', true);
const myShowLondon = mySessionsTab.boolean('Show London Session', true);
const myShowNY = mySessionsTab.boolean('Show New York Session', true);

const myBabyPurple = '#BF94E4';
const myBabyBlue = '#89CFF0';
const myBabyGreen = '#98D6AA';

// returns true if the hour:minute of a candle falls within [startH:startM, endH:endM)
function myWithinWindow(_hours, _minutes, _startH, _startM, _endH, _endM) {
	const myCurrentMinutes = _hours * 60 + _minutes;
	const myStartMinutes = _startH * 60 + _startM;
	let myEndMinutes = _endH * 60 + _endM;
	if (myEndMinutes <= myStartMinutes) {
		myEndMinutes += 24 * 60;
	}
	let myAdjustedCurrent = myCurrentMinutes;
	if (myAdjustedCurrent < myStartMinutes) {
		myAdjustedCurrent += 24 * 60;
	}
	return myAdjustedCurrent >= myStartMinutes && myAdjustedCurrent < myEndMinutes;
}

const myTimeInfo = time.map(_t => time_of(_t));

const myInAsiaFlags = myTimeInfo.map(_info => myWithinWindow(_info.hours, _info.minutes, 20, 0, 0, 0));
const myInLondonFlags = myTimeInfo.map(_info => myWithinWindow(_info.hours, _info.minutes, 2, 0, 7, 0));
const myInNYFlags = myTimeInfo.map(_info => myWithinWindow(_info.hours, _info.minutes, 9, 30, 12, 0));

// days since last asia session start, used for the lookback window
const myNow = current.now;
const myLastCandleTime = time[time.length - 1];

function myBuildSessionLines(_inSessionFlags, _showSession) {
	const myHigh = series_of(null);
	const myLow = series_of(null);
	let mySessionHigh = null;
	let mySessionLow = null;
	let mySessionStartIndex = null;
	let myFirstSessionStartTime = null;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const myInSession = _inSessionFlags[myIndex];
		const myWasInSession = myIndex > 0 ? _inSessionFlags[myIndex - 1] : false;

		if (myInSession) {
			if (!myWasInSession) {
				mySessionHigh = high[myIndex];
				mySessionLow = low[myIndex];
				mySessionStartIndex = myIndex;
				if (myFirstSessionStartTime === null) {
					myFirstSessionStartTime = time[myIndex];
				}
			}
			else {
				mySessionHigh = Math.max(mySessionHigh, high[myIndex]);
				mySessionLow = Math.min(mySessionLow, low[myIndex]);
			}

			// days since this particular session started, vs now
			const myDaysSinceStart = Math.floor((myNow - time[mySessionStartIndex]) / 86400);
			const myWithinLookback = myDaysSinceStart < myLookback;

			if (_showSession && (myShowHistory || myWithinLookback)) {
				myHigh[myIndex] = mySessionHigh;
				myLow[myIndex] = mySessionLow;
			}
		}
	}

	return { high: myHigh, low: myLow };
}

const myAsiaLines = myBuildSessionLines(myInAsiaFlags, myShowAsia);
const myLondonLines = myBuildSessionLines(myInLondonFlags, myShowLondon);
const myNYLines = myBuildSessionLines(myInNYFlags, myShowNY);

// paint session high/low as ladder lines (closest equivalent to a box outline)
const myAsiaHighPainted = paint(myAsiaLines.high, { name: 'Asia High', color: myBabyPurple, style: 'ladder', thickness: 1 });
const myAsiaLowPainted = paint(myAsiaLines.low, { name: 'Asia Low', color: myBabyPurple, style: 'ladder', thickness: 1 });
fill(myAsiaHighPainted, myAsiaLowPainted, myBabyPurple, 0.15);

const myLondonHighPainted = paint(myLondonLines.high, { name: 'London High', color: myBabyBlue, style: 'ladder', thickness: 1 });
const myLondonLowPainted = paint(myLondonLines.low, { name: 'London Low', color: myBabyBlue, style: 'ladder', thickness: 1 });
fill(myLondonHighPainted, myLondonLowPainted, myBabyBlue, 0.15);

const myNYHighPainted = paint(myNYLines.high, { name: 'New York High', color: myBabyGreen, style: 'ladder', thickness: 1 });
const myNYLowPainted = paint(myNYLines.low, { name: 'New York Low', color: myBabyGreen, style: 'ladder', thickness: 1 });
fill(myNYHighPainted, myNYLowPainted, myBabyGreen, 0.15);

// place a label at the last point of each session block
function myLastIndexWithValue(_series) {
	for (let myIndex = _series.length - 1; myIndex >= 0; myIndex -= 1) {
		if (_series[myIndex] !== null) {
			return myIndex;
		}
	}
	return -1;
}

const myAsiaLastIndex = myLastIndexWithValue(myAsiaLines.high);
if (myAsiaLastIndex >= 0) {
	paint_label_at_line(myAsiaHighPainted, myAsiaLastIndex, 'ASIA', { color: 'black', background_color: 'white' });
}

const myLondonLastIndex = myLastIndexWithValue(myLondonLines.high);
if (myLondonLastIndex >= 0) {
	paint_label_at_line(myLondonHighPainted, myLondonLastIndex, 'LONDON', { color: 'black', background_color: 'white' });
}

const myNYLastIndex = myLastIndexWithValue(myNYLines.high);
if (myNYLastIndex >= 0) {
	paint_label_at_line(myNYHighPainted, myNYLastIndex, 'NEW YORK', { color: 'black', background_color: 'white' });
}

// register signals for scanning/alerts/strategy usage
register_signal(myInAsiaFlags, 'In Asia Session');
register_signal(myInLondonFlags, 'In London Session');
register_signal(myInNYFlags, 'In New York Session');

const mySessionStartAsia = for_every(series_of(0), (_x, _prev, _idx) => myInAsiaFlags[_idx] && (_idx === 0 || !myInAsiaFlags[_idx - 1]));
const mySessionStartLondon = for_every(series_of(0), (_x, _prev, _idx) => myInLondonFlags[_idx] && (_idx === 0 || !myInLondonFlags[_idx - 1]));
const mySessionStartNY = for_every(series_of(0), (_x, _prev, _idx) => myInNYFlags[_idx] && (_idx === 0 || !myInNYFlags[_idx - 1]));

register_signal(mySessionStartAsia, 'Asia Session Start');
register_signal(mySessionStartLondon, 'London Session Start');
register_signal(mySessionStartNY, 'New York Session Start');