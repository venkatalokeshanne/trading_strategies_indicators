// EXPERIMENT NOTE: TrendSpider Custom JS has no strategy/broker module
// (no strategy.entry, strategy.opentrades, pyramiding, etc). This code
// reproduces the Pine logic by manually simulating the "open trades"
// state (entries, DCA adds, average price, close-all) bar by bar in a
// sequential loop. This is the closest possible equivalent, but it is
// a simulation, not an actual backtest/strategy engine integration.
describe_indicator('Value Trend plus RSI Arrows', 'price');

const myTab = input.tab('Value Trend');
const myRsiLength = myTab.number('RSI Length', 14, { min: 2, max: 100 });
const myVtRange = myTab.number('VT Range Length', 75, { min: 10, max: 300 });
const myVtNormLen = myTab.number('VT Norm Smooth', 20, { min: 1, max: 100 });
const myVtSignalLen = myTab.number('VT Signal Smooth', 5, { min: 1, max: 100 });
const myBuyLevel = myTab.number('VT Buy Crossover Level', 25, { min: -50, max: 150 });

const myTradeTab = input.tab('Trade Simulation');
const myRsiOversold = myTradeTab.number('RSI Oversold Arm Level', 30, { min: 1, max: 50 });
const myDcaDrop = myTradeTab.number('DCA Drop %', 25, { min: 1, max: 90 });
const myMaxEntries = myTradeTab.number('Max Entries (Pyramiding)', 10, { min: 1, max: 50 });
const myProfitBuffer = myTradeTab.number('Exit Profit Buffer %', 0.2, { min: 0, max: 20 });

const myExitRow = myTradeTab.row();
const myExitLow = myExitRow.number('Exit RSI Low', 78, { min: 1, max: 99 });
const myExitHigh = myExitRow.number('Exit RSI High', 80, { min: 1, max: 100 });

// RSI
const myRsi14 = rsi(close, myRsiLength);

// VALUE TREND block
const myLowest75 = lowest(low, myVtRange);
const myHighest75 = highest(high, myVtRange);
const myRangeDivider = div(sub(myHighest75, myLowest75), 100);

// raw normalized close, guarded against division by zero
const myRawNorm = for_every(close, myLowest75, myRangeDivider, (_c, _l, _r) => (_r !== 0 && _r !== null) ? (_c - _l) / _r : 0);

// weightedSma(src, len) from Pine: recursive, alpha = 1/len, seeded with
// first value (not a standard EMA since alpha != 2/(len+1)). Built via a
// plain sequential loop since there is no built-in function matching it.
function myWeightedSma(_src, _len) {
	const myAlpha = 1 / _len;
	const myResult = series_of(null);
	for (let myIndex = 0; myIndex < _src.length; myIndex += 1) {
		const myCurrentValue = _src[myIndex];
		if (myCurrentValue === null || myCurrentValue === undefined || isNaN(myCurrentValue)) {
			myResult[myIndex] = myIndex > 0 ? myResult[myIndex - 1] : null;
			continue;
		}
		const myPrev = myIndex > 0 ? myResult[myIndex - 1] : null;
		myResult[myIndex] = (myPrev === null || myPrev === undefined) ? myCurrentValue : (myAlpha * myCurrentValue + (1 - myAlpha) * myPrev);
	}
	return myResult;
}

const myCloseNorm = myWeightedSma(myRawNorm, myVtNormLen);
const myValueTrend = sub(mult(myCloseNorm, 3), mult(myWeightedSma(myCloseNorm, myVtSignalLen), 2));

// Trade state simulation (sequential, no look-ahead): reproduces
// readyToBuy, strategy.opentrades, DCA, average price and close_all.
const myBuyMarks = series_of(null);
const myDcaMarks = series_of(null);
const myExitMarks = series_of(null);
const myBuySignalFlags = series_of(false);
const myDcaSignalFlags = series_of(false);
const myExitSignalFlags = series_of(false);

let myReadyToBuy = false;
let myOpenTradePrices = [];

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myRsi14[myIndex] !== null && myRsi14[myIndex] < myRsiOversold) {
		myReadyToBuy = true;
	}

	const myCurrentVt = myValueTrend[myIndex];
	const myPrevVt = myIndex > 0 ? myValueTrend[myIndex - 1] : null;
	const myBuySignal = (myIndex > 0 && myCurrentVt !== null && myPrevVt !== null) ? (myCurrentVt > myBuyLevel && myPrevVt <= myBuyLevel) : false;

	const myEntryCondition = myReadyToBuy && myBuySignal;
	const myCanEnter = myOpenTradePrices.length === 0;

	if (myEntryCondition && myCanEnter) {
		myOpenTradePrices.push(close[myIndex]);
		myReadyToBuy = false;
		myBuyMarks[myIndex] = low[myIndex];
		myBuySignalFlags[myIndex] = true;
	}

	const myLastEntryPrice = myOpenTradePrices.length > 0 ? myOpenTradePrices[myOpenTradePrices.length - 1] : null;
	const myDcaCondition = myOpenTradePrices.length > 0 && myOpenTradePrices.length < myMaxEntries && myLastEntryPrice !== null && close[myIndex] <= myLastEntryPrice * (1 - myDcaDrop / 100);

	if (myDcaCondition) {
		myOpenTradePrices.push(close[myIndex]);
		myDcaMarks[myIndex] = low[myIndex];
		myDcaSignalFlags[myIndex] = true;
	}

	const myAvgPrice = myOpenTradePrices.length > 0 ? (myOpenTradePrices.reduce((_a, _b) => _a + _b, 0) / myOpenTradePrices.length) : 0;
	const myInProfitOrBE = myOpenTradePrices.length > 0 && close[myIndex] >= myAvgPrice * (1 + myProfitBuffer / 100);

	const myRsiNow = myRsi14[myIndex];
	const myRsiPrev = myIndex > 0 ? myRsi14[myIndex - 1] : null;
	const myExitZoneNow = myRsiNow !== null && myRsiNow >= myExitLow && myRsiNow <= myExitHigh;
	const myExitZonePrev = myRsiPrev !== null && myRsiPrev >= myExitLow && myRsiPrev <= myExitHigh;
	const myExitCondition = myExitZoneNow && !myExitZonePrev && myInProfitOrBE;

	if (myExitCondition) {
		myOpenTradePrices = [];
		myExitMarks[myIndex] = high[myIndex];
		myExitSignalFlags[myIndex] = true;
	}
}

paint(myBuyMarks, { style: 'labels_below', color: 'green', name: 'Buy Entry' });
paint(myDcaMarks, { style: 'labels_below', color: 'orange', name: 'Dca Entry' });
paint(myExitMarks, { style: 'labels_above', color: 'red', name: 'Exit' });

register_signal(myBuySignalFlags, 'Buy Signal');
register_signal(myDcaSignalFlags, 'Dca Signal');
register_signal(myExitSignalFlags, 'Exit Signal');