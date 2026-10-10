describe_indicator('NQ Kebo Sessions', 'price');
// ============================================================================
// LIMITATION: TrendSpider Custom JS has no equivalent of Pine's time(tf, session, tz)
// or box.new()/line.new() dynamic drawing objects. This version approximates
// Pine's logic using candle-time hour/minute checks (time_of()) in the EXCHANGE
// timezone of the current chart (there's no way to convert to an arbitrary
// timezone like "America/Sao_Paulo" in this API). Session boxes are approximated
// with ladder-style high/low lines, and Asia liquidity lines are approximated
// with lines that persist until broken, exactly like Pine, but built via arrays
// instead of box/line draw objects.
// ============================================================================

const myGeneral = input.tab('General');
// shortened title (was too long and triggered a platform error)
const myTzNote = myGeneral.text('Chart Timezone', 'America/New_York');

const mySessionsTab = input.tab('Sessions / Killzones');
const myAsiaGroup = mySessionsTab.group('Asia');
const myShowAsia = myAsiaGroup.boolean('Show Asia range', true);
const mySesAsia = myAsiaGroup.text('Asia session', '2000-0000');

const myLonGroup = mySessionsTab.group('London');
const myShowLon = myLonGroup.boolean('Show London range', true);
const mySesLon = myLonGroup.text('London session', '0200-0500');

const myNYGroup = mySessionsTab.group('NY AM');
const myShowNY = myNYGroup.boolean('Show NY AM range', true);
const mySesNY = myNYGroup.text('NY AM session', '0930-1100');

const myLiqTab = input.tab('Liquidity and Opens');
const myLiqGroup = myLiqTab.group('Asia liquidity');
const myShowAsiaLiq = myLiqGroup.boolean('Show Asia liquidity lines', true);

const myOpenGroup = myLiqTab.group('NY Open');
const myShowNYOpen = myOpenGroup.boolean('Mark NY open', true);
const mySesNYOpen = myOpenGroup.text('NY open window', '0930-0931');
const myColorOpenBar = myOpenGroup.boolean('Color NY opening candle', true);

const myMOGroup = myLiqTab.group('Midnight Open');
const myShowMO = myMOGroup.boolean('Show Midnight Open', true);

// parses "HHMM-HHMM" into { startH, startM, endH, endM }
function myParseSession(_mySessionText) {
	const myParts = _mySessionText.split('-');
	assert(myParts.length === 2, `Invalid session format: "${_mySessionText}"`);
	const myStart = myParts[0];
	const myEnd = myParts[1];
	return {
		startH: parseInt(myStart.slice(0, 2), 10),
		startM: parseInt(myStart.slice(2, 4), 10),
		endH: parseInt(myEnd.slice(0, 2), 10),
		endM: parseInt(myEnd.slice(2, 4), 10)
	};
}

// checks if a given timestamp's time-of-day falls within a session window.
// handles overnight windows (e.g. 2000-0000) where end < start.
function myInSession(_myTimestamp, _mySession) {
	const myTimeInfo = time_of(_myTimestamp);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myStartMin = _mySession.startH * 60 + _mySession.startM;
	let myEndMin = _mySession.endH * 60 + _mySession.endM;
	if (myEndMin <= myStartMin) {
		// overnight session wraps past midnight
		return myMinutesOfDay >= myStartMin || myMinutesOfDay < myEndMin;
	}
	return myMinutesOfDay >= myStartMin && myMinutesOfDay < myEndMin;
}

const myAsiaSession = myParseSession(mySesAsia);
const myLonSession = myParseSession(mySesLon);
const myNYSession = myParseSession(mySesNY);
const myNYOpenSession = myParseSession(mySesNYOpen);

const myCandleCount = close.length;

// --- flags per candle: is this candle inside each session window ---
const myIsAsiaFlags = time.map(_t => myInSession(_t, myAsiaSession));
const myIsLonFlags = time.map(_t => myInSession(_t, myLonSession));
const myIsNYFlags = time.map(_t => myInSession(_t, myNYSession));
const myIsNYOpenFlags = time.map(_t => myInSession(_t, myNYOpenSession));
const myIsMidnightFlags = time.map(_t => myInSession(_t, { startH: 0, startM: 0, endH: 1, endM: 0 }));

// --- generic session range builder: outputs high/low ladder lines while active ---
function myBuildSessionRange(_myFlags) {
	const myHigh = series_of(null);
	const myLow = series_of(null);
	let myOn = false;
	let myH = null;
	let myL = null;
	for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
		const myInS = _myFlags[myIndex];
		const myNewS = myInS && !myOn;
		if (myNewS) {
			myH = high[myIndex];
			myL = low[myIndex];
		}
		else if (myInS) {
			myH = Math.max(myH, high[myIndex]);
			myL = Math.min(myL, low[myIndex]);
		}
		if (myInS) {
			myHigh[myIndex] = myH;
			myLow[myIndex] = myL;
		}
		myOn = myInS;
	}
	return { high: myHigh, low: myLow };
}

const myAsiaRange = myBuildSessionRange(myIsAsiaFlags);
const myLonRange = myBuildSessionRange(myIsLonFlags);
const myNYRange = myBuildSessionRange(myIsNYFlags);

// --- Asia liquidity: lines that persist after session ends, until broken ---
function myBuildLiquidityLines(_myFlags) {
	const myLiqHigh = series_of(null);
	const myLiqLow = series_of(null);
	let myOn = false;
	let myH = null;
	let myL = null;
	let myHighActive = false;
	let myLowActive = false;
	for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
		const myInS = _myFlags[myIndex];
		const myNewS = myInS && !myOn;
		if (myNewS) {
			myH = high[myIndex];
			myL = low[myIndex];
			myHighActive = true;
			myLowActive = true;
		}
		else if (myInS) {
			myH = Math.max(myH, high[myIndex]);
			myL = Math.min(myL, low[myIndex]);
		}
		if (!myInS && myH !== null) {
			if (myHighActive && high[myIndex] >= myH) {
				myHighActive = false;
			}
			if (myLowActive && low[myIndex] <= myL) {
				myLowActive = false;
			}
			if (myHighActive) {
				myLiqHigh[myIndex] = myH;
			}
			if (myLowActive) {
				myLiqLow[myIndex] = myL;
			}
		}
		myOn = myInS;
	}
	return { high: myLiqHigh, low: myLiqLow };
}

const myAsiaLiquidity = myBuildLiquidityLines(myIsAsiaFlags);

// --- NY open marker: true on first candle entering the NY open window ---
const myNYOpenBarFlags = series_of(false);
for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	myNYOpenBarFlags[myIndex] = myIsNYOpenFlags[myIndex] && !myIsNYOpenFlags[myIndex - 1];
}
if (myCandleCount > 0) {
	myNYOpenBarFlags[0] = myIsNYOpenFlags[0];
}

const myNYOpenMarkers = for_every(close, (_c, _prev, _i) => (myShowNYOpen && myNYOpenBarFlags[_i]) ? low[_i] : null);

// --- Midnight open: carries today's 00:00 open price forward as a dotted line ---
const myMidnightOpenLine = series_of(null);
{
	let myMOPrice = null;
	for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
		const myIsMid = myIsMidnightFlags[myIndex] && (myIndex === 0 || !myIsMidnightFlags[myIndex - 1]);
		if (myIsMid) {
			myMOPrice = open[myIndex];
		}
		if (myShowMO && myMOPrice !== null) {
			myMidnightOpenLine[myIndex] = myMOPrice;
		}
	}
}

// --- color opening candle ---
const myOpenBarColors = for_every(close, (_c, _prev, _i) => (myColorOpenBar && myNYOpenBarFlags[_i]) ? 'yellow' : null);
color_candles(myOpenBarColors);

// ============================================================================
// Painting
// ============================================================================
paint(myShowAsia ? myAsiaRange.high : constants.empty_series, { name: 'AsiaHigh', style: 'ladder', color: '#9e9e9e' });
paint(myShowAsia ? myAsiaRange.low : constants.empty_series, { name: 'AsiaLow', style: 'ladder', color: '#9e9e9e' });

paint(myShowLon ? myLonRange.high : constants.empty_series, { name: 'LondonHigh', style: 'ladder', color: '#4da3ff' });
paint(myShowLon ? myLonRange.low : constants.empty_series, { name: 'LondonLow', style: 'ladder', color: '#4da3ff' });

paint(myShowNY ? myNYRange.high : constants.empty_series, { name: 'NYHigh', style: 'ladder', color: '#26A69A' });
paint(myShowNY ? myNYRange.low : constants.empty_series, { name: 'NYLow', style: 'ladder', color: '#26A69A' });

paint(myShowAsiaLiq ? myAsiaLiquidity.high : constants.empty_series, { name: 'AsiaLiquidityHigh', style: 'ladder', color: 'orange' });
paint(myShowAsiaLiq ? myAsiaLiquidity.low : constants.empty_series, { name: 'AsiaLiquidityLow', style: 'ladder', color: 'orange' });

paint(myNYOpenMarkers, { name: 'NYOpenMarker', style: 'labels_below', color: 'green' });
paint(myMidnightOpenLine, { name: 'MidnightOpen', style: 'dotted', color: 'gray' });

// ============================================================================
// Signals for scanners / alerts / strategies
// ============================================================================
register_signal(myIsAsiaFlags, 'In Asia Session');
register_signal(myIsLonFlags, 'In London Session');
register_signal(myIsNYFlags, 'In NY AM Session');
register_signal(myNYOpenBarFlags, 'NY Open Bar');