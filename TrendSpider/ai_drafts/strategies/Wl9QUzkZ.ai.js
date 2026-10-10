describe_indicator('RKLB 5m ORB VWAP Long (approximated)', 'price');

// NOTE: This is an approximation of a TradingView strategy. The Custom JS
// API has no strategy engine (no strategy.entry/exit, no order queue,
// no intrabar fill simulation, no backtest stats table). This script
// reproduces the opening-range / VWAP breakout LOGIC as an indicator and
// exposes Long/Short entry conditions as signals, so it can be used in
// scanners/alerts. Position management (stops, targets, EOD flat,
// pyramiding, equity, commissions) is not simulated.

const mySideInput = input.select('Trade side', 'Long only', ['Both', 'Long only', 'Short only']);
const myRR = input.number('Reward/Risk', 2.0, { min: 0.25, step: 0.25 });
const myBufferTicks = input.number('Breakout buffer ticks', 1, { min: 0, step: 1 });
const myMaxRangePct = input.number('Max opening range %', 6.0, { min: 0.1, step: 0.1 });
const myMinRangePct = input.number('Min opening range %', 0.3, { min: 0, step: 0.1 });
const myUseVwapFilter = input.boolean('Use VWAP direction filter', true);
const myUseRetestEntry = input.boolean('Require pullback before breakout', false);
const myEntryWindow = input.text('Entry window (HHMM-HHMM)', '0935-1530');
const myFlatWindow = input.text('Force flat window (HHMM-HHMM)', '1555-1600');
const myRegularSession = input.text('Regular session (HHMM-HHMM)', '0930-1600');

// tick size is not exposed by the API; approximate from current.decimals.
const myTickSize = Math.pow(10, -current.decimals);

function myParseSession(_str) {
	const myParts = _str.split('-');
	const myStartStr = myParts[0];
	const myEndStr = myParts[1];
	return {
		startH: parseInt(myStartStr.slice(0, 2), 10),
		startM: parseInt(myStartStr.slice(2, 4), 10),
		endH: parseInt(myEndStr.slice(0, 2), 10),
		endM: parseInt(myEndStr.slice(2, 4), 10)
	};
}

function myInSession(_timestamp, _session) {
	const myTimeInfo = time_of(_timestamp);
	const myMinuteOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myStartMinute = _session.startH * 60 + _session.startM;
	const myEndMinute = _session.endH * 60 + _session.endM;
	return myMinuteOfDay >= myStartMinute && myMinuteOfDay < myEndMinute;
}

const myRegularSessionDef = myParseSession(myRegularSession);
const myEntryWindowDef = myParseSession(myEntryWindow);
const myFlatWindowDef = myParseSession(myFlatWindow);

const myN = close.length;

const myOrHighSeries = series_of(null);
const myOrLowSeries = series_of(null);
const myOrMidSeries = series_of(null);
const myOpeningBarSeries = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myVwapSeries = series_of(null);

let myOrHigh = null;
let myOrLow = null;
let myOrMid = null;
let myRangeReady = false;
let myTradedToday = false;
let myPulledBackLong = false;
let myPulledBackShort = false;
let myOpeningBarIndex = null;

let myVwapCumPV = 0;
let myVwapCumVol = 0;
let myPrevDaySession = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myTimestamp = time[myIndex];
	const myInRegular = myInSession(myTimestamp, myRegularSessionDef);
	const myInEntryWindow = myInSession(myTimestamp, myEntryWindowDef);
	const myInFlatWindow = myInSession(myTimestamp, myFlatWindowDef);
	const myDaySession = bar_at(myTimestamp).session;
	const myNewDay = myDaySession !== myPrevDaySession;

	// VWAP resets at the start of a new calendar day (approximation of
	// Pine's default daily session anchor for ta.vwap).
	if (myNewDay) {
		myVwapCumPV = 0;
		myVwapCumVol = 0;
	}
	const myTypicalPrice = (high[myIndex] + low[myIndex] + close[myIndex]) / 3;
	myVwapCumPV += myTypicalPrice * volume[myIndex];
	myVwapCumVol += volume[myIndex];
	const myVwapValue = myVwapCumVol !== 0 ? myVwapCumPV / myVwapCumVol : myTypicalPrice;
	myVwapSeries[myIndex] = myVwapValue;

	const myNewRegularSession = myInRegular && (myIndex === 0 || myDaySession !== myPrevDaySession);

	if (myNewRegularSession) {
		myOrHigh = high[myIndex];
		myOrLow = low[myIndex];
		myOrMid = null;
		myRangeReady = false;
		myTradedToday = false;
		myPulledBackLong = false;
		myPulledBackShort = false;
		myOpeningBarIndex = myIndex;
		myOpeningBarSeries[myIndex] = low[myIndex];
	}

	if (myInRegular && !myRangeReady && myOpeningBarIndex !== null && myIndex > myOpeningBarIndex) {
		myOrMid = (myOrHigh + myOrLow) / 2.0;
		myRangeReady = true;
	}

	if (myRangeReady && myInEntryWindow) {
		myPulledBackLong = myPulledBackLong || low[myIndex] <= myOrHigh;
		myPulledBackShort = myPulledBackShort || high[myIndex] >= myOrLow;
	}

	const myRangePct = myRangeReady ? (myOrHigh - myOrLow) / myOrMid * 100.0 : null;
	const myRangeOk = myRangeReady && myRangePct !== null && myRangePct >= myMinRangePct && myRangePct <= myMaxRangePct;

	const myLongAllowed = mySideInput === 'Both' || mySideInput === 'Long only';
	const myShortAllowed = mySideInput === 'Both' || mySideInput === 'Short only';
	const myLongFilterOk = !myUseVwapFilter || close[myIndex] > myVwapValue;
	const myShortFilterOk = !myUseVwapFilter || close[myIndex] < myVwapValue;
	const myLongRetestOk = !myUseRetestEntry || myPulledBackLong;
	const myShortRetestOk = !myUseRetestEntry || myPulledBackShort;

	const myLongStopPrice = myRangeReady ? myOrLow : null;
	const myShortStopPrice = myRangeReady ? myOrHigh : null;
	const myLongEntryStop = myRangeReady ? myOrHigh + myBufferTicks * myTickSize : null;
	const myShortEntryStop = myRangeReady ? myOrLow - myBufferTicks * myTickSize : null;
	const myLongRisk = myRangeReady ? myLongEntryStop - myLongStopPrice : null;
	const myShortRisk = myRangeReady ? myShortStopPrice - myShortEntryStop : null;

	const myCanPlaceOrders = myRangeOk && myInEntryWindow && !myTradedToday;

	// Approximation: since there is no intrabar order engine, an entry is
	// considered "triggered" on the first bar whose high/low crosses the
	// breakout stop level while all other conditions hold.
	if (myCanPlaceOrders && myLongAllowed && myLongRisk !== null && myLongRisk > myTickSize && myLongFilterOk && myLongRetestOk) {
		if (high[myIndex] >= myLongEntryStop) {
			myLongEntrySignal[myIndex] = true;
			myTradedToday = true;
		}
	}
	if (myCanPlaceOrders && myShortAllowed && myShortRisk !== null && myShortRisk > myTickSize && myShortFilterOk && myShortRetestOk) {
		if (low[myIndex] <= myShortEntryStop) {
			myShortEntrySignal[myIndex] = true;
			myTradedToday = true;
		}
	}

	if (myInFlatWindow || !myInRegular) {
		myTradedToday = true;
	}

	myOrHighSeries[myIndex] = myRangeReady ? myOrHigh : null;
	myOrLowSeries[myIndex] = myRangeReady ? myOrLow : null;
	myOrMidSeries[myIndex] = myRangeReady ? myOrMid : null;

	myPrevDaySession = myDaySession;
}

paint(myOrHighSeries, { name: 'OpeningRangeHigh', color: '#39FF14', thickness: 2, style: 'ladder' });
paint(myOrLowSeries, { name: 'OpeningRangeLow', color: '#FF4136', thickness: 2, style: 'ladder' });
paint(myOrMidSeries, { name: 'OpeningRangeMid', color: '#9E9E9E', thickness: 1, style: 'dotted' });
paint(myVwapSeries, { name: 'SessionVwap', color: '#4DA3FF', thickness: 1, style: 'line' });
paint(myOpeningBarSeries, { name: 'OpeningBar', color: '#FFD700', thickness: 6, style: 'labels_below' });

register_signal(myLongEntrySignal, 'ORB Long Entry');
register_signal(myShortEntrySignal, 'ORB Short Entry');