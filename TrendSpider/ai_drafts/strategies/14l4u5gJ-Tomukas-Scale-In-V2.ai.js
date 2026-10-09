// Converted from a TradingView Pine Script v6 strategy ("Tomukas Scale-In V2").
// IMPORTANT: TrendSpider Custom JS indicators cannot place real orders, manage
// pyramiding, or execute limit-order take-profits intrabar. This script
// reproduces the Pine SIGNAL LOGIC (trend filter + liquidity sweep + scale-in
// cascade + take-profit tracking) as faithfully as possible using a manual
// bar-by-bar simulation, and exposes everything as paint()/register_signal()
// outputs so it can be used for scanning/alerts. Take-profit fills are
// approximated using the bar's high/low touching the TP level (since true
// intrabar limit fill order isn't available here).

describe_indicator('Tomukas Scale In V2', 'price');

const myLookback = input.number('Sweep Lookback', 20, { min: 1, max: 500 });
const myQ1 = input.number('Entry 1', 10, { min: 0 });
const myQ2 = input.number('Entry 2', 10, { min: 0 });
const myQ3 = input.number('Entry 3', 20, { min: 0 });
const myQ4 = input.number('Entry 4', 40, { min: 0 });
const myQ5 = input.number('Entry 5', 80, { min: 0 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myTpAtrMultiplier = input.number('TP ATR Multiplier', 1.5, { min: 0.1, max: 20 });

// Trend filter
const myEma100 = ema(close, 100);
const myEma200 = ema(close, 200);

const myBullTrend = for_every(myEma100, myEma200, (_e100, _e200) => _e100 > _e200);
const myBearTrend = for_every(myEma100, myEma200, (_e100, _e200) => _e100 < _e200);

// Liquidity sweep thresholds, mirroring ta.lowest(low[1], lookback) / ta.highest(high[1], lookback)
const myPrevLow = lowest(shift(low, 1), myLookback);
const myPrevHigh = highest(shift(high, 1), myLookback);

const myLongSweep = for_every(myBullTrend, low, close, open, myPrevLow,
	(_bull, _low, _close, _open, _prevLow) => Boolean(_bull && _low < _prevLow && _close > _prevLow && _close > _open));

const myShortSweep = for_every(myBearTrend, high, close, open, myPrevHigh,
	(_bear, _high, _close, _open, _prevHigh) => Boolean(_bear && _high > _prevHigh && _close < _prevHigh && _close < _open));

const myAtr = atr(high, low, close, myAtrLength);

// Manual simulation of the scale-in / take-profit strategy engine
const myBuyShapeArr = series_of(null);
const mySellShapeArr = series_of(null);
const myEntrySignalArr = series_of(false);
const myScaleInSignalArr = series_of(false);
const myExitSignalArr = series_of(false);
const myLongTpLevelArr = series_of(null);
const myShortTpLevelArr = series_of(null);

let myPositionSize = 0;
let myOpenTrades = 0;
let myAvgPrice = 0;

function myAddEntry(_qty, _price, _isLong) {
	const mySignedQty = _isLong ? _qty : -_qty;
	const myNewSize = myPositionSize + mySignedQty;
	const myNewAbsSize = Math.abs(myNewSize);
	const myOldAbsSize = Math.abs(myPositionSize);
	myAvgPrice = myOldAbsSize === 0
		? _price
		: ((myAvgPrice * myOldAbsSize) + (_price * _qty)) / myNewAbsSize;
	myPositionSize = myNewSize;
	myOpenTrades += 1;
}

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPositionBeforeEntries = myPositionSize;
	let myDidEntry = false;
	let myDidScaleIn = false;

	if (myLongSweep[myIndex]) {
		if (myPositionSize === 0) { myAddEntry(myQ1, close[myIndex], true); myDidEntry = true; }
		if (myPositionSize > 0 && myOpenTrades === 1) { myAddEntry(myQ2, close[myIndex], true); myDidScaleIn = true; }
		if (myPositionSize > 0 && myOpenTrades === 2) { myAddEntry(myQ3, close[myIndex], true); myDidScaleIn = true; }
		if (myPositionSize > 0 && myOpenTrades === 3) { myAddEntry(myQ4, close[myIndex], true); myDidScaleIn = true; }
		if (myPositionSize > 0 && myOpenTrades === 4) { myAddEntry(myQ5, close[myIndex], true); myDidScaleIn = true; }
	}

	if (myShortSweep[myIndex]) {
		if (myPositionSize === 0) { myAddEntry(myQ1, close[myIndex], false); myDidEntry = true; }
		if (myPositionSize < 0 && myOpenTrades === 1) { myAddEntry(myQ2, close[myIndex], false); myDidScaleIn = true; }
		if (myPositionSize < 0 && myOpenTrades === 2) { myAddEntry(myQ3, close[myIndex], false); myDidScaleIn = true; }
		if (myPositionSize < 0 && myOpenTrades === 3) { myAddEntry(myQ4, close[myIndex], false); myDidScaleIn = true; }
		if (myPositionSize < 0 && myOpenTrades === 4) { myAddEntry(myQ5, close[myIndex], false); myDidScaleIn = true; }
	}

	myBuyShapeArr[myIndex] = (myLongSweep[myIndex] && myPositionBeforeEntries === 0) ? low[myIndex] : null;
	mySellShapeArr[myIndex] = (myShortSweep[myIndex] && myPositionBeforeEntries === 0) ? high[myIndex] : null;
	myEntrySignalArr[myIndex] = myDidEntry;
	myScaleInSignalArr[myIndex] = myDidScaleIn;

	let myDidExit = false;
	if (myPositionSize > 0) {
		const myLongTp = myAvgPrice + (myAtr[myIndex] || 0) * myTpAtrMultiplier;
		myLongTpLevelArr[myIndex] = myLongTp;
		myShortTpLevelArr[myIndex] = null;
		if (high[myIndex] >= myLongTp) {
			myDidExit = true;
			myPositionSize = 0;
			myOpenTrades = 0;
			myAvgPrice = 0;
		}
	}
	else if (myPositionSize < 0) {
		const myShortTp = myAvgPrice - (myAtr[myIndex] || 0) * myTpAtrMultiplier;
		myShortTpLevelArr[myIndex] = myShortTp;
		myLongTpLevelArr[myIndex] = null;
		if (low[myIndex] <= myShortTp) {
			myDidExit = true;
			myPositionSize = 0;
			myOpenTrades = 0;
			myAvgPrice = 0;
		}
	}
	else {
		myLongTpLevelArr[myIndex] = null;
		myShortTpLevelArr[myIndex] = null;
	}

	myExitSignalArr[myIndex] = myDidExit;
}

paint(myEma100, { name: 'EMA100', color: '#f0c419', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: '#e67e22', thickness: 2 });
paint(myLongTpLevelArr, { name: 'LongTP', color: '#2ecc71', style: 'dotted' });
paint(myShortTpLevelArr, { name: 'ShortTP', color: '#e74c3c', style: 'dotted' });

paint(myBuyShapeArr, { name: 'Buy', style: 'labels_below', color: '#00e676' });
paint(mySellShapeArr, { name: 'Sell', style: 'labels_above', color: '#ff1744' });

register_signal(myLongSweep, 'Long Sweep');
register_signal(myShortSweep, 'Short Sweep');
register_signal(myEntrySignalArr, 'First Entry');
register_signal(myScaleInSignalArr, 'Scale In Entry');
register_signal(myExitSignalArr, 'Take Profit Exit');