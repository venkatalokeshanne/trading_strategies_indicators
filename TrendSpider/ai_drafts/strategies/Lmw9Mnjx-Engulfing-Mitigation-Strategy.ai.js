// This indicator reproduces, as closely as the TrendSpider Custom JS API
// allows, the EMA/Engulfing/Pivot signal logic from the given Pine Script.
// TrendSpider Custom JS API has no strategy/broker simulation engine
// (no equity, position sizing, pyramiding or limit-order fills), so the
// DCA/scale-in money-management part of the Pine strategy cannot be
// executed literally. Instead this script simulates the SAME entry/add/exit
// RULES bar-by-bar (position state, average entry price, entry count,
// take-profit level) purely as a signal-tracking state machine, and
// exposes every rule as a register_signal() so it can be used in
// Scanners / Alerts / Strategy Tester. Position sizing (qtyPercents,
// strategy.equity) is not simulated since there is no portfolio engine.
describe_indicator('Engulfing Mitigation Signals', 'price');

const myTakeProfitPct = input.number('Take Profit %', 4.0, { min: 0.1, max: 50, step: 0.5 });
const myPivotLeft = input.number('Pivot Left Bars', 5, { min: 1, max: 50 });
const myPivotRight = input.number('Pivot Right Bars', 5, { min: 1, max: 50 });
const myEmaLength = input.number('EMA Length', 200, { min: 1, max: 500 });

const myTakeProfitFraction = myTakeProfitPct / 100.0;

// --- Indicators ---
const myEma200 = ema(close, myEmaLength);

const myOpenPrev = shift(open, 1);
const myClosePrev = shift(close, 1);

// bullishEngulfing = close > open[1] and open <= close[1] and close[1] < open[1]
const myBullishEngulfing = for_every(close, open, myOpenPrev, myClosePrev, (_c, _o, _opPrev, _clPrev) => {
	return _c > _opPrev && _o <= _clPrev && _clPrev < _opPrev;
});

// bearishEngulfing = close < open[1] and open >= close[1] and close[1] > open[1]
const myBearishEngulfing = for_every(close, open, myOpenPrev, myClosePrev, (_c, _o, _opPrev, _clPrev) => {
	return _c < _opPrev && _o >= _clPrev && _clPrev > _opPrev;
});

const myPivotHighSeries = pivot_high(high, myPivotLeft, myPivotRight);
const myPivotLowSeries = pivot_low(low, myPivotLeft, myPivotRight);

// --- Rule simulation state machine (replaces strategy.* calls) ---
const myQtyPercents = [0.005, 0.005, 0.01, 0.02, 0.04];

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongAddSignal = series_of(false);
const myShortAddSignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myPositionSize = 0; // >0 long, <0 short, 0 flat
let myAvgPrice = 0;
let myEntryCount = 0;
let myTotalUnits = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const myIsBullish = myBullishEngulfing[myIndex];
	const myIsBearish = myBearishEngulfing[myIndex];
	const myHasPivotLow = myPivotLowSeries[myIndex] !== null && myPivotLowSeries[myIndex] !== undefined;
	const myHasPivotHigh = myPivotHighSeries[myIndex] !== null && myPivotHighSeries[myIndex] !== undefined;
	const myEmaValue = myEma200[myIndex];

	// Reset counter when flat
	if (myPositionSize === 0) {
		myEntryCount = 0;
		myTotalUnits = 0;
	}

	let myLongEntry = false;
	let myShortEntry = false;
	let myLongAdd = false;
	let myShortAdd = false;
	let myLongExit = false;
	let myShortExit = false;

	// Initial entries
	if (myPositionSize === 0) {
		if (myIsBullish && myClose > myEmaValue) {
			const myUnits = myQtyPercents[0];
			myPositionSize = 1;
			myAvgPrice = myClose;
			myTotalUnits = myUnits;
			myEntryCount = 1;
			myLongEntry = true;
		}
		else if (myIsBearish && myClose < myEmaValue) {
			const myUnits = myQtyPercents[0];
			myPositionSize = -1;
			myAvgPrice = myClose;
			myTotalUnits = myUnits;
			myEntryCount = 1;
			myShortEntry = true;
		}
	}
	else if (myPositionSize > 0) {
		// Long scale-in
		if (myEntryCount < 5 && myClose < myAvgPrice && (myIsBullish || myHasPivotLow)) {
			const myUnits = myQtyPercents[myEntryCount];
			const myNewTotalUnits = myTotalUnits + myUnits;
			myAvgPrice = (myAvgPrice * myTotalUnits + myClose * myUnits) / myNewTotalUnits;
			myTotalUnits = myNewTotalUnits;
			myEntryCount += 1;
			myLongAdd = true;
		}

		// Take profit exit
		const myTpLevel = myAvgPrice * (1 + myTakeProfitFraction);
		if (myClose >= myTpLevel) {
			myLongExit = true;
			myPositionSize = 0;
			myAvgPrice = 0;
			myEntryCount = 0;
			myTotalUnits = 0;
		}
	}
	else if (myPositionSize < 0) {
		// Short scale-in
		if (myEntryCount < 5 && myClose > myAvgPrice && (myIsBearish || myHasPivotHigh)) {
			const myUnits = myQtyPercents[myEntryCount];
			const myNewTotalUnits = myTotalUnits + myUnits;
			myAvgPrice = (myAvgPrice * myTotalUnits + myClose * myUnits) / myNewTotalUnits;
			myTotalUnits = myNewTotalUnits;
			myEntryCount += 1;
			myShortAdd = true;
		}

		// Take profit exit
		const myTpLevel = myAvgPrice * (1 - myTakeProfitFraction);
		if (myClose <= myTpLevel) {
			myShortExit = true;
			myPositionSize = 0;
			myAvgPrice = 0;
			myEntryCount = 0;
			myTotalUnits = 0;
		}
	}

	myLongEntrySignal[myIndex] = myLongEntry;
	myShortEntrySignal[myIndex] = myShortEntry;
	myLongAddSignal[myIndex] = myLongAdd;
	myShortAddSignal[myIndex] = myShortAdd;
	myLongExitSignal[myIndex] = myLongExit;
	myShortExitSignal[myIndex] = myShortExit;
}

// --- Visuals ---
paint(myEma200, { name: 'EMA200', color: '#2962ff', thickness: 2 });

const myBullishMarks = for_every(myBullishEngulfing, _b => _b ? constants.icons.triangle_up : null);
const myBearishMarks = for_every(myBearishEngulfing, _b => _b ? constants.icons.triangle_down : null);

paint(myBullishMarks, { style: 'labels_below', color: 'green', name: 'BullishEngulfing' });
paint(myBearishMarks, { style: 'labels_above', color: 'red', name: 'BearishEngulfing' });

// --- Signals for Scanners / Alerts / Strategy Tester ---
register_signal(myBullishEngulfing, 'Bullish Engulfing');
register_signal(myBearishEngulfing, 'Bearish Engulfing');
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongAddSignal, 'Long Add');
register_signal(myShortAddSignal, 'Short Add');
register_signal(myLongExitSignal, 'Long Take Profit Exit');
register_signal(myShortExitSignal, 'Short Take Profit Exit');