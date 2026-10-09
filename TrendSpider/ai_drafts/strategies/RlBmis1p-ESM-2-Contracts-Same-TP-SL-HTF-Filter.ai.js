// EXPERIMENTAL CONVERSION: this is a best-effort translation of a Pine Script
// strategy into TrendSpider Custom JS. Strategy semantics (intrabar fills,
// exact VWAP anchor, HTF non-repainting alignment) can't be reproduced 100%
// identically on this platform - see flags below for the approximations made.
describe_indicator('ES ORB Strategy (2 Contracts, HTF Filter)', 'lower');

const myHtfTab = input.tab('Higher Timeframe');
const myHtfTf = myHtfTab.select('Higher Timeframe', '15', constants.time_frames);
const myHtfEmaLength = myHtfTab.number('HTF EMA Length', 20, { min: 1, max: 500 });

const myRiskTab = input.tab('Risk');
const myStopPoints = myRiskTab.number('Stop Loss (Points)', 32, { min: 0.25, max: 1000, step: 0.25 });
const myTargetPoints = myRiskTab.number('Target (Points)', 64, { min: 0.25, max: 1000, step: 0.25 });

const myLength = close.length;

// --- Session / day tracking, opening range (9:30-9:45 NY), daily VWAP ---
const myOrHigh = series_of(null);
const myOrLow = series_of(null);
const myVwap = series_of(null);

let myCurrentOrHigh = null;
let myCurrentOrLow = null;
let myCumPV = 0;
let myCumVol = 0;
let myPrevDay = null;

const myInOrbFlag = [];
const myAfterOrbFlag = [];

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = bar_at(time[myIndex], 'D').session;

	if (myDayKey !== myPrevDay) {
		myCurrentOrHigh = null;
		myCurrentOrLow = null;
		myCumPV = 0;
		myCumVol = 0;
		myPrevDay = myDayKey;
	}

	const myIsInOrb = myTimeInfo.hours === 9 && myTimeInfo.minutes >= 30 && myTimeInfo.minutes <= 45;
	const myIsAfterOrb = (myTimeInfo.hours > 9) || (myTimeInfo.hours === 9 && myTimeInfo.minutes > 45);

	myInOrbFlag.push(myIsInOrb);
	myAfterOrbFlag.push(myIsAfterOrb);

	if (myIsInOrb) {
		myCurrentOrHigh = myCurrentOrHigh === null ? high[myIndex] : Math.max(myCurrentOrHigh, high[myIndex]);
		myCurrentOrLow = myCurrentOrLow === null ? low[myIndex] : Math.min(myCurrentOrLow, low[myIndex]);
	}

	myOrHigh[myIndex] = myCurrentOrHigh;
	myOrLow[myIndex] = myCurrentOrLow;

	const myTypicalPrice = ohlc4[myIndex];
	myCumPV += myTypicalPrice * volume[myIndex];
	myCumVol += volume[myIndex];
	myVwap[myIndex] = myCumVol > 0 ? (myCumPV / myCumVol) : close[myIndex];
}

// --- HTF trend filter (approximated as non-repainting via 'le' landing) ---
const myHtfData = await request.history(current.ticker, myHtfTf);
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);

const myHtfEma = ema(myHtfData.close, myHtfEmaLength);
const myHtfCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.close, time, 'le'),
	'constant'
);
const myHtfEmaLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfEma, time, 'le'),
	'constant'
);

// --- Breakouts, filters and daily/position state machine ---
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myTradesToday = 0;
let myLongTakenToday = false;
let myShortTakenToday = false;
let myPositionSize = 0;
let myEntryPrice = null;
let myCurrentDayForState = null;

for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	const myDayKey = bar_at(time[myIndex], 'D').session;
	if (myDayKey !== myCurrentDayForState) {
		myTradesToday = 0;
		myLongTakenToday = false;
		myShortTakenToday = false;
		myCurrentDayForState = myDayKey;
	}

	const myOrHighPrev = myOrHigh[myIndex - 1];
	const myOrLowPrev = myOrLow[myIndex - 1];

	const myLongBreakout = myAfterOrbFlag[myIndex] && myOrHigh[myIndex] !== null &&
		close[myIndex] > myOrHigh[myIndex] && close[myIndex - 1] <= myOrHighPrev;
	const myShortBreakout = myAfterOrbFlag[myIndex] && myOrLow[myIndex] !== null &&
		close[myIndex] < myOrLow[myIndex] && close[myIndex - 1] >= myOrLowPrev;

	const myHtfLongFilter = myHtfCloseLanded[myIndex] > myHtfEmaLanded[myIndex];
	const myHtfShortFilter = myHtfCloseLanded[myIndex] < myHtfEmaLanded[myIndex];

	const myLongCondition = myLongBreakout && close[myIndex] > myVwap[myIndex] && myHtfLongFilter;
	const myShortCondition = myShortBreakout && close[myIndex] < myVwap[myIndex] && myHtfShortFilter;

	const myCanTrade = myTradesToday < 2;

	// Exits checked first (intrabar stop/limit, stop priority assumed)
	if (myPositionSize > 0) {
		const myStopPrice = myEntryPrice - myStopPoints;
		const myTargetPrice = myEntryPrice + myTargetPoints;
		if (low[myIndex] <= myStopPrice || high[myIndex] >= myTargetPrice) {
			myLongExitSignal[myIndex] = true;
			myPositionSize = 0;
			myEntryPrice = null;
		}
	}
	else if (myPositionSize < 0) {
		const myStopPrice = myEntryPrice + myStopPoints;
		const myTargetPrice = myEntryPrice - myTargetPoints;
		if (high[myIndex] >= myStopPrice || low[myIndex] <= myTargetPrice) {
			myShortExitSignal[myIndex] = true;
			myPositionSize = 0;
			myEntryPrice = null;
		}
	}

	// Entries (only if flat)
	if (myLongCondition && myPositionSize === 0 && myCanTrade && !myLongTakenToday) {
		myLongEntrySignal[myIndex] = true;
		myPositionSize = 2;
		myEntryPrice = close[myIndex];
		myTradesToday += 1;
		myLongTakenToday = true;
	}
	else if (myShortCondition && myPositionSize === 0 && myCanTrade && !myShortTakenToday) {
		myShortEntrySignal[myIndex] = true;
		myPositionSize = -2;
		myEntryPrice = close[myIndex];
		myTradesToday += 1;
		myShortTakenToday = true;
	}
}

// --- Signals for scanner/alerts/strategy tester ---
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');

// --- Plots ---
paint(myOrHigh, { name: 'ORHigh', color: '#26A69A', style: 'ladder', forceUsePriceAxis: true });
paint(myOrLow, { name: 'ORLow', color: '#EF5350', style: 'ladder', forceUsePriceAxis: true });
paint(myVwap, { name: 'VWAP', color: '#4DA3FF', forceUsePriceAxis: true });
paint(myHtfEmaLanded, { name: 'HTFEMA', color: '#FFA726', forceUsePriceAxis: true });