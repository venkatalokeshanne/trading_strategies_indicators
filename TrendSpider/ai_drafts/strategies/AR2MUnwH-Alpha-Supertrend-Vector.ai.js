describe_indicator('Alpha Supertrend Vector', 'price');

// NOTE: TrendSpider custom indicators cannot run an actual backtesting
// engine (no strategy.entry/exit, no position sizing, no equity curve).
// This script reproduces the Pine SCRIPT's underlying technical logic
// (Supertrend flip, ADX filter, Choppiness filter, ATR based TP/SL
// levels) and exposes Long/Short Entry and Exit conditions as
// register_signal() outputs so they can be used in Scanners, Alerts
// and the Strategy Tester. The actual trade simulation (equity,
// position averaging, pyramiding) is not reproduced.

const myDirTab = input.tab('Trade Direction');
const myTradeDir = myDirTab.select('Allowed Directions', 'Both', ['Long Only', 'Short Only', 'Both']);

const myFiltersTab = input.tab('Entry Filters');
// Shortened title (platform rejects overly long input titles)
const myChopThresh = myFiltersTab.number('Chop Threshold', 61.8, { min: 0, max: 100 });
const myChopLen = myFiltersTab.number('Choppiness Length', 14, { min: 1, max: 200 });

const myIndicatorsTab = input.tab('Indicator Settings');
const myStMult = myIndicatorsTab.number('Supertrend Multiplier', 3.0, { min: 0.1, max: 20 });
const myAtrLen = myIndicatorsTab.number('Fast ATR Length', 7, { min: 1, max: 100 });
const myAdxLen = myIndicatorsTab.number('ADX Length', 7, { min: 1, max: 100 });
// Shortened title
const myAdxMin = myIndicatorsTab.number('ADX Min Threshold', 25.0, { min: 0, max: 100 });

const myExitTab = input.tab('Exit Settings');
// Shortened titles
const myTpMult = myExitTab.number('Take Profit (xATR%)', 3.0, { min: 0, max: 50 });
const mySlMult = myExitTab.number('Stop Loss (xATR%)', 1.0, { min: 0, max: 50 });
const myPlugPct = myExitTab.number('The Plug (Hard SL %)', 1.0, { min: 0, max: 50 });

// ---- Choppiness Index ----
const myTrueRange = atr(high, low, close, 1);
const mySumTR = sum(myTrueRange, myChopLen);
const myRange = sub(highest(high, myChopLen), lowest(low, myChopLen));
const myChop = for_every(mySumTR, myRange, (_sumTR, _range) => {
	if (!_range || _range === 0) return null;
	return 100 * Math.log10(_sumTR / _range) / Math.log10(myChopLen);
});

// ---- Supertrend ----
// Built-in supertrend() returns the Supertrend line only; direction is
// reconstructed here by comparing Close to the Supertrend value, which
// is mathematically equivalent to Pine's dir output (1 = bearish/red,
// -1 = bullish/green).
const mySt = supertrend(myAtrLen, myStMult, false);
const myStDir = for_every(close, mySt, (_close, _st) => {
	if (_st === null || _st === undefined) return null;
	return _close > _st ? -1 : 1;
});

const myStFlipLong = series_of(false);
const myStFlipShort = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevDir = myStDir[myIndex - 1];
	const myCurrDir = myStDir[myIndex];

	myStFlipLong[myIndex] = (myPrevDir === 1 && myCurrDir === -1);
	myStFlipShort[myIndex] = (myPrevDir === -1 && myCurrDir === 1);
}

// ---- ADX ----
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;

// ---- Fast ATR % ----
const myFastAtr = atr(high, low, close, myAtrLen);
const myFastAtrPct = div(mult(myFastAtr, 100), close);

// ---- Entry Filters ----
const myAllowLong = (myTradeDir === 'Both' || myTradeDir === 'Long Only');
const myAllowShort = (myTradeDir === 'Both' || myTradeDir === 'Short Only');

const myTriggerLong = series_of(false);
const myTriggerShort = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myAdxOk = (myAdx[myIndex] !== null && myAdx[myIndex] > myAdxMin);
	const myChopOk = (myChop[myIndex] !== null && myChop[myIndex] < myChopThresh);

	myTriggerLong[myIndex] = Boolean(myStFlipLong[myIndex] && myAdxOk && myChopOk);
	myTriggerShort[myIndex] = Boolean(myStFlipShort[myIndex] && myAdxOk && myChopOk);
}

// ---- Position simulation (single position, no pyramiding) ----
// Simulates one position at a time to compute TP / SL levels and
// generate Exit signals, mirroring the Pine Script's exit logic.
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);
const myTpLevel = series_of(null);
const mySlLevel = series_of(null);

let myPositionState = 0; // 0 flat, 1 long, -1 short
let myEntryPrice = null;
let myEntryAtrPct = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTriggeredLong = myTriggerLong[myIndex] && myAllowLong;
	const myTriggeredShort = myTriggerShort[myIndex] && myAllowShort;

	// Check exits first, using levels established at entry
	if (myPositionState === 1 && myEntryPrice !== null) {
		const myLongTp = myEntryPrice * (1 + myEntryAtrPct * myTpMult / 100);
		const myAtrSl = myEntryPrice * (1 - myEntryAtrPct * mySlMult / 100);
		const myPlugSl = myEntryPrice * (1 - myPlugPct / 100);
		const myLongSl = Math.max(myAtrSl, myPlugSl);

		myTpLevel[myIndex] = myLongTp;
		mySlLevel[myIndex] = myLongSl;

		if (high[myIndex] >= myLongTp || low[myIndex] <= myLongSl) {
			myLongExitSignal[myIndex] = true;
			myPositionState = 0;
			myEntryPrice = null;
			myEntryAtrPct = null;
		}
	}
	else if (myPositionState === -1 && myEntryPrice !== null) {
		const myShortTp = myEntryPrice * (1 - myEntryAtrPct * myTpMult / 100);
		const myAtrSl = myEntryPrice * (1 + myEntryAtrPct * mySlMult / 100);
		const myPlugSl = myEntryPrice * (1 + myPlugPct / 100);
		const myShortSl = Math.min(myAtrSl, myPlugSl);

		myTpLevel[myIndex] = myShortTp;
		mySlLevel[myIndex] = myShortSl;

		if (low[myIndex] <= myShortTp || high[myIndex] >= myShortSl) {
			myShortExitSignal[myIndex] = true;
			myPositionState = 0;
			myEntryPrice = null;
			myEntryAtrPct = null;
		}
	}

	// Entries (no pyramiding, flat only)
	if (myPositionState === 0) {
		if (myTriggeredLong) {
			myLongEntrySignal[myIndex] = true;
			myPositionState = 1;
			myEntryPrice = close[myIndex];
			myEntryAtrPct = myFastAtrPct[myIndex];
		}
		else if (myTriggeredShort) {
			myShortEntrySignal[myIndex] = true;
			myPositionState = -1;
			myEntryPrice = close[myIndex];
			myEntryAtrPct = myFastAtrPct[myIndex];
		}
	}
}

// ---- Visuals ----
const myStColor = for_every(myStDir, _dir => _dir === 1 ? '#ef5350' : '#26a69a');
paint(mySt, { name: 'Supertrend', color: myStColor, thickness: 2 });
paint(myTpLevel, { name: 'Take Profit Level', color: '#2196f3', style: 'dotted' });
paint(mySlLevel, { name: 'Stop Loss Level', color: '#ff9800', style: 'dotted' });

// ---- Signals for Scanners / Alerts / Strategy Tester ----
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');