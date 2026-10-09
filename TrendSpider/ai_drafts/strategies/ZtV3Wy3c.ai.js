describe_indicator('Ichimoku Chikou Touch Exit', 'price');

// --- Inputs ---
const tsTab = input.tab('Ichimoku');
const myTsBars = tsTab.number('Tenkan-Sen Bars', 9, { min: 1, max: 200 });
const myKsBars = tsTab.number('Kijun-Sen Bars', 26, { min: 1, max: 200 });
const mySsbBars = tsTab.number('Senkou-Span B Bars', 52, { min: 1, max: 300 });
const myCsOffset = tsTab.number('Chikou-Span Offset (Lookback)', 26, { min: 1, max: 300 });
const mySsOffset = tsTab.number('Senkou-Span Offset (Forward)', 26, { min: 1, max: 300 });

const entryTab = input.tab('Entries');
const myLongEntry = entryTab.boolean('Allow Long Entries', true);
const myShortEntry = entryTab.boolean('Allow Short Entries', true);

// --- Ichimoku core calculations ---
// middle(len) = avg(lowest(len), highest(len))
function myMiddle(_len) {
	return div(add(highest(high, _len), lowest(low, _len)), 2);
}

const myTenkan = myMiddle(myTsBars);
const myKijun = myMiddle(myKsBars);
const mySenkouA = div(add(myTenkan, myKijun), 2);
const mySenkouB = myMiddle(mySsbBars);

// Cloud as it is "currently" positioned (i.e., projected ss_offset-1 bars ago)
// Pine's `senkouA[ss_offset-1]` means "value from ss_offset-1 bars back",
// which, since we don't shift forward on this engine the same way Pine plots,
// we replicate using shift() to look back in time by (ss_offset - 1) bars.
const myCurrentSsA = shift(mySenkouA, -(mySsOffset - 1));
const myCurrentSsB = shift(mySenkouB, -(mySsOffset - 1));
const mySsHigh = max_of(myCurrentSsA, myCurrentSsB);
const mySsLow = min_of(myCurrentSsA, myCurrentSsB);

// --- Entry conditions ---
const myTkCrossBull = for_every(myTenkan, myKijun, (_t, _k) => _t > _k);
const myTkCrossBear = for_every(myTenkan, myKijun, (_t, _k) => _t < _k);

const myMomCs = momentum(close, myCsOffset - 1);
const myCsAbovePrice = for_every(myMomCs, _m => _m > 0);
const myCsBelowPrice = for_every(myMomCs, _m => _m < 0);

const myPriceAboveKumo = for_every(close, mySsHigh, (_c, _h) => _c > _h);
const myPriceBelowKumo = for_every(close, mySsLow, (_c, _l) => _c < _l);

const myBullishSignal = for_every(myTkCrossBull, myCsAbovePrice, myPriceAboveKumo, (_a, _b, _c) => _a && _b && _c);
const myBearishSignal = for_every(myTkCrossBear, myCsBelowPrice, myPriceBelowKumo, (_a, _b, _c) => _a && _b && _c);

// --- Exit logic: Chikou touches price ---
// price_lookback = close[cs_offset-1] (value of close, cs_offset-1 bars ago)
const myPriceLookback = shift(close, myCsOffset - 1);

// ta.cross(close, price_lookback): detect sign change of (close - price_lookback)
const myDiffSeries = sub(close, myPriceLookback);
const myChikouExit = for_every(myDiffSeries, (_d, _prev, _idx) => {
	if (_idx === 0) return false;
	const myPrevDiff = myDiffSeries[_idx - 1];
	if (myPrevDiff === null || _d === null || myPrevDiff === undefined) return false;
	return (myPrevDiff <= 0 && _d > 0) || (myPrevDiff >= 0 && _d < 0);
});

// --- Simulated position state (mirrors strategy.entry/close logic) ---
// Position: 1 = long, -1 = short, 0 = flat
const myPositionState = for_every(myBullishSignal, myBearishSignal, myChikouExit, (_bull, _bear, _exit, _prevPos, _idx) => {
	let myPos = _prevPos || 0;

	// Exit first, as per Pine ordering (checked after entries in code,
	// but since entries/exits reference position_size at that bar, we
	// approximate by processing exit based on current position before any new entry on this bar)
	if (myPos > 0 && _exit) {
		myPos = 0;
	}
	else if (myPos < 0 && _exit) {
		myPos = 0;
	}

	if (_bull && myLongEntry) {
		myPos = 1;
	}
	if (_bear && myShortEntry) {
		myPos = -1;
	}

	return myPos;
});

// Entry/exit signals derived from position state transitions
const myLongEntrySignal = for_every(myPositionState, (_pos, _prevPos, _idx) => {
	const myPrev = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return _pos === 1 && myPrev !== 1;
});

const myShortEntrySignal = for_every(myPositionState, (_pos, _prevPos, _idx) => {
	const myPrev = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return _pos === -1 && myPrev !== -1;
});

const myExitLongSignal = for_every(myPositionState, myChikouExit, (_pos, _exit, _prevPos, _idx) => {
	const myPrev = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return myPrev === 1 && _exit;
});

const myExitShortSignal = for_every(myPositionState, myChikouExit, (_pos, _exit, _prevPos, _idx) => {
	const myPrev = _idx === 0 ? 0 : myPositionState[_idx - 1];
	return myPrev === -1 && _exit;
});

// --- Register signals for scanners/alerts/strategy tester ---
register_signal(myBullishSignal, 'Bullish Signal');
register_signal(myBearishSignal, 'Bearish Signal');
register_signal(myChikouExit, 'Chikou Touch Exit');
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myExitLongSignal, 'Exit Long');
register_signal(myExitShortSignal, 'Exit Short');

// --- Visual plotting ---
paint(myTenkan, { name: 'Tenkan', color: '#2962FF', thickness: 1 });
paint(myKijun, { name: 'Kijun', color: '#EF5350', thickness: 1 });

const mySenkouAShifted = shift(mySenkouA, mySsOffset - 1);
const mySenkouBShifted = shift(mySenkouB, mySsOffset - 1);

fill(
	paint(mySenkouAShifted, { name: 'Senkou A', color: '#26A69A', thickness: 1 }),
	paint(mySenkouBShifted, { name: 'Senkou B', color: '#EF5350', thickness: 1 }),
	'green',
	0.1
);

paint(myPriceLookback, { name: 'Price Reference Chikou', color: 'gray', style: 'ladder', thickness: 1 });