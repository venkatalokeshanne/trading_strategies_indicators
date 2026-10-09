describe_indicator('Kloom Session Levels', 'price');

// ── Inputs ───────────────────────────────────────────────────────────────────
const nyTab = input.tab('New York session');
const myShowNY = nyTab.boolean('Show NY session', true);
const myNYSession = nyTab.text('NY hours (exchange tz)', '0930-1600');

const ldnTab = input.tab('London session');
const myShowLDN = ldnTab.boolean('Show London session', true);
const myLDNSession = ldnTab.text('London hours (exchange tz)', '0300-1130');

const lvlTab = input.tab('Levels');
const myShowPDHL = lvlTab.boolean('Show previous day high/low (PDH/PDL)', true);
const myShowOpen = lvlTab.boolean('Show session open line', true);

// Parses a session string like "0930-1600" into minute-of-day boundaries.
function myParseSession(_sessionText) {
	const myParts = _sessionText.split('-');
	assert(myParts.length === 2, `Invalid session format: "${_sessionText}"`);
	const myStartH = parseInt(myParts[0].slice(0, 2), 10);
	const myStartM = parseInt(myParts[0].slice(2, 4), 10);
	const myEndH = parseInt(myParts[1].slice(0, 2), 10);
	const myEndM = parseInt(myParts[1].slice(2, 4), 10);
	return { from: myStartH * 60 + myStartM, to: myEndH * 60 + myEndM };
}

const myNYBounds = myParseSession(myNYSession);
const myLDNBounds = myParseSession(myLDNSession);

// Builds a boolean series: true for every candle whose time-of-day
// (in the exchange's local time zone) falls within the given bounds.
function myBuildInSession(_bounds) {
	return time.map(_t => {
		const myTimeInfo = time_of(_t);
		const myMinuteOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
		return myMinuteOfDay >= _bounds.from && myMinuteOfDay < _bounds.to;
	});
}

const myInNY = myBuildInSession(myNYBounds);
const myInLDN = myBuildInSession(myLDNBounds);

const myNYHigh = series_of(null);
const myNYLow = series_of(null);
const myNYOpen = series_of(null);
const myLDNHigh = series_of(null);
const myLDNLow = series_of(null);
const myNYStart = series_of(false);
const myLDNStart = series_of(false);

// Tracks running session high/low/open, resetting at the start of each session.
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevInNY = myIndex > 0 ? myInNY[myIndex - 1] : false;
	const myPrevInLDN = myIndex > 0 ? myInLDN[myIndex - 1] : false;

	const myIsNYStart = myInNY[myIndex] && !myPrevInNY;
	const myIsLDNStart = myInLDN[myIndex] && !myPrevInLDN;
	myNYStart[myIndex] = myIsNYStart;
	myLDNStart[myIndex] = myIsLDNStart;

	if (myIsNYStart) {
		myNYHigh[myIndex] = high[myIndex];
		myNYLow[myIndex] = low[myIndex];
		myNYOpen[myIndex] = open[myIndex];
	}
	else if (myInNY[myIndex]) {
		myNYHigh[myIndex] = Math.max(myNYHigh[myIndex - 1], high[myIndex]);
		myNYLow[myIndex] = Math.min(myNYLow[myIndex - 1], low[myIndex]);
		myNYOpen[myIndex] = myNYOpen[myIndex - 1];
	}

	if (myIsLDNStart) {
		myLDNHigh[myIndex] = high[myIndex];
		myLDNLow[myIndex] = low[myIndex];
	}
	else if (myInLDN[myIndex]) {
		myLDNHigh[myIndex] = Math.max(myLDNHigh[myIndex - 1], high[myIndex]);
		myLDNLow[myIndex] = Math.min(myLDNLow[myIndex - 1], low[myIndex]);
	}
}

// ── Previous day high/low ──────────────────────────────────────────────────
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const myPDHValues = myDailyData.high.map((_v, _i) => (_i > 0 ? myDailyData.high[_i - 1] : null));
const myPDLValues = myDailyData.low.map((_v, _i) => (_i > 0 ? myDailyData.low[_i - 1] : null));

const myPDHLanded = land_points_onto_series(myDailyData.time, myPDHValues, time, 'le');
const myPDLLanded = land_points_onto_series(myDailyData.time, myPDLValues, time, 'le');

const myPDH = interpolate_sparse_series(myPDHLanded, 'constant');
const myPDL = interpolate_sparse_series(myPDLLanded, 'constant');

// ── Masked series for plotting (null breaks the line, like plot.style_linebr) ─
const myNYHighPlot = for_every(myNYHigh, (_v, _i, _idx) => myInNY[_idx] && myShowNY ? _v : null);
const myNYLowPlot = for_every(myNYLow, (_v, _i, _idx) => myInNY[_idx] && myShowNY ? _v : null);
const myNYOpenPlot = for_every(myNYOpen, (_v, _i, _idx) => (myInNY[_idx] && myShowNY && myShowOpen) ? _v : null);
const myLDNHighPlot = for_every(myLDNHigh, (_v, _i, _idx) => myInLDN[_idx] && myShowLDN ? _v : null);
const myLDNLowPlot = for_every(myLDNLow, (_v, _i, _idx) => myInLDN[_idx] && myShowLDN ? _v : null);
const myPDHPlot = myShowPDHL ? myPDH : constants.empty_series;
const myPDLPlot = myShowPDHL ? myPDL : constants.empty_series;

paint(myNYHighPlot, { name: 'NYHigh', color: '#2962FF', thickness: 1, style: 'line' });
paint(myNYLowPlot, { name: 'NYLow', color: '#2962FF', thickness: 1, style: 'line' });
paint(myNYOpenPlot, { name: 'NYOpen', color: '#5B8DEF', thickness: 1, style: 'dotted' });

paint(myLDNHighPlot, { name: 'LondonHigh', color: '#9C27B0', thickness: 1, style: 'line' });
paint(myLDNLowPlot, { name: 'LondonLow', color: '#9C27B0', thickness: 1, style: 'line' });

const myPDHPainted = paint(myPDHPlot, { name: 'PDH', color: '#FF9800', thickness: 1, style: 'dotted' });
const myPDLPainted = paint(myPDLPlot, { name: 'PDL', color: '#FF9800', thickness: 1, style: 'dotted' });

paint_label_at_line(myPDHPainted, close.length - 1, 'PDH', { color: 'white', background_color: '#FF9800' });
paint_label_at_line(myPDLPainted, close.length - 1, 'PDL', { color: 'white', background_color: '#FF9800' });

// ── Signals for scanners / alerts / strategy tester ─────────────────────────
register_signal(myNYStart, 'NY Session Start');
register_signal(myLDNStart, 'London Session Start');
register_signal(myInNY, 'In NY Session');
register_signal(myInLDN, 'In London Session');