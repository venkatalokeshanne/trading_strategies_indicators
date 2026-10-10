describe_indicator('RSI Volume Ladder', 'price');

// NOTE: This indicator approximates the Pine Script strategy logic as closely
// as the Custom JS API allows. Strategy-specific concepts from Pine
// (strategy.entry, strategy.exit, strategy.closedtrades, pyramiding engine,
// equity sizing, commissions) do not exist in this API, so position
// management, average price, TP/SL and exits are manually simulated bar by
// bar using close/high/low. Intrabar SL/TP priority (which one would hit
// first within a single candle) is approximated by checking SL first, then
// TP, using the candle's low/high.

const myRsiTab = input.tab('RSI');
const myRsiLength = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOversold = myRsiTab.number('RSI Oversold', 30, { min: 1, max: 99 });

const myVolumeTab = input.tab('Volume');
const myVolLength = myVolumeTab.number('Volume SMA Length', 20, { min: 1, max: 500 });
const myVolMultiplier = myVolumeTab.number('High Volume Multiplier', 1.5, { min: 1, max: 10, step: 0.1 });

const myPyramidTab = input.tab('Pyramiding');
// shortened title to satisfy platform's input name length limit
const myDropPercent = myPyramidTab.number('Min Drop Percent', 1.5, { min: 0, max: 50, step: 0.1 });
const myMaxPositions = myPyramidTab.number('Max Positions', 3, { min: 1, max: 3 });

const myExitTab = input.tab('Exit');
const myTpPercent = myExitTab.number('Take Profit Percent', 4.0, { min: 0.1, max: 100, step: 0.1 });
const mySlPercent = myExitTab.number('Stop Loss Percent', 3.0, { min: 0.1, max: 100, step: 0.1 });

const myCooldownTab = input.tab('Cooldown');
// shortened titles to satisfy platform's input name length limit
const myCooldownAfterSl = myCooldownTab.number('Cooldown After SL', 3, { min: 0, max: 1000 });
const myCooldownAfterTp = myCooldownTab.number('Cooldown After TP', 0, { min: 0, max: 1000 });

const myRsiValues = rsi(close, myRsiLength);
const myVolSmaValues = sma(volume, myVolLength);
const myCandleCount = close.length;

const myEntryMarks = series_of(null);
const myAvgPriceLine = series_of(null);
const myTpLine = series_of(null);
const mySlLine = series_of(null);
const myTpHitMarks = series_of(null);
const mySlHitMarks = series_of(null);
const myEntrySignalOut = series_of(false);
const myTpHitOut = series_of(false);
const mySlHitOut = series_of(false);

let myLowestEntryPrice = null;
let myLastEntryPrice = null;
let myOpenEntries = 0;
let myTpPrice = null;
let mySlPrice = null;
let myLastExitBar = -9999;
let myLastExitWasSl = false;
let myPositionSize = 0;
let myEntryPrices = [];

function myLow(myIdx) {
	return low[myIdx];
}

function myHigh(myIdx) {
	return high[myIdx];
}

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	let myTpHit = false;
	let mySlHit = false;
	let myExitHitPrice = null;

	// === EXIT CHECK (intrabar approximation using low/high) ===
	if (myPositionSize > 0 && mySlPrice !== null && myLow(myIndex) <= mySlPrice) {
		mySlHit = true;
		myExitHitPrice = mySlPrice;
	}
	else if (myPositionSize > 0 && myTpPrice !== null && myHigh(myIndex) >= myTpPrice) {
		myTpHit = true;
		myExitHitPrice = myTpPrice;
	}

	if (myTpHit || mySlHit) {
		myLastExitBar = myIndex;
		myLastExitWasSl = mySlHit;
		myTpPrice = null;
		mySlPrice = null;
		myLowestEntryPrice = null;
		myLastEntryPrice = null;
		myOpenEntries = 0;
		myPositionSize = 0;
		myEntryPrices = [];
	}

	// === COOLDOWN CHECK ===
	const myBarsSinceExit = myIndex - myLastExitBar;
	const myRequiredCooldown = myLastExitWasSl ? myCooldownAfterSl : myCooldownAfterTp;
	const myCooldownActive = myBarsSinceExit <= myRequiredCooldown;

	// === ENTRY LOGIC ===
	const myOversold = myRsiValues[myIndex] !== null && myRsiValues[myIndex] < myRsiOversold;
	const myHighVolume = myVolSmaValues[myIndex] !== null && volume[myIndex] > myVolSmaValues[myIndex] * myVolMultiplier;
	const myEntrySignal = myOversold && myHighVolume;
	const myPriceDroppedEnough = myLastEntryPrice === null || close[myIndex] < myLastEntryPrice * (1 - myDropPercent / 100);
	const myCanEnter = myOpenEntries < myMaxPositions && myEntrySignal && myPriceDroppedEnough && !myCooldownActive;

	if (myCanEnter) {
		myEntryPrices.push(close[myIndex]);
		myLowestEntryPrice = myLowestEntryPrice === null ? close[myIndex] : Math.min(myLowestEntryPrice, close[myIndex]);
		myLastEntryPrice = close[myIndex];
		myOpenEntries += 1;
		myPositionSize = myOpenEntries;
	}

	let myAvgPrice = null;
	if (myPositionSize > 0 && myEntryPrices.length > 0) {
		myAvgPrice = myEntryPrices.reduce((myAcc, myVal) => myAcc + myVal, 0) / myEntryPrices.length;
		myTpPrice = myAvgPrice * (1 + myTpPercent / 100);
		mySlPrice = myLowestEntryPrice * (1 - mySlPercent / 100);
	}

	myEntryMarks[myIndex] = myCanEnter ? close[myIndex] : null;
	myAvgPriceLine[myIndex] = myPositionSize > 0 ? myAvgPrice : null;
	myTpLine[myIndex] = myPositionSize > 0 ? myTpPrice : null;
	mySlLine[myIndex] = myPositionSize > 0 ? mySlPrice : null;
	myTpHitMarks[myIndex] = myTpHit ? myExitHitPrice : null;
	mySlHitMarks[myIndex] = mySlHit ? myExitHitPrice : null;
	myEntrySignalOut[myIndex] = myCanEnter;
	myTpHitOut[myIndex] = myTpHit;
	mySlHitOut[myIndex] = mySlHit;
}

paint(myEntryMarks, { name: 'EntryArrow', style: 'labels_below', color: 'blue' });
paint(myAvgPriceLine, { name: 'AveragePrice', style: 'line', color: 'blue', thickness: 2 });
paint(myTpLine, { name: 'TakeProfit', style: 'line', color: 'fuchsia', thickness: 2 });
paint(mySlLine, { name: 'StopLoss', style: 'line', color: 'red', thickness: 2 });
paint(myTpHitMarks, { name: 'TakeProfitHit', style: 'labels_above', color: 'fuchsia' });
paint(mySlHitMarks, { name: 'StopLossHit', style: 'labels_below', color: 'red' });

register_signal(myEntrySignalOut, 'Entry Signal');
register_signal(myTpHitOut, 'Take Profit Hit');
register_signal(mySlHitOut, 'Stop Loss Hit');