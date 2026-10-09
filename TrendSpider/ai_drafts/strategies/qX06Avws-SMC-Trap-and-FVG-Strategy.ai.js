// EXPERIMENTAL CONVERSION: this is a best-effort line-by-line port of the
// Pine Script SMC Trap -> FVG strategy into TrendSpider Custom JS. Strategy
// orders (TP/SL execution, equity sizing) can't be replicated 1:1 since
// Custom JS indicators don't run a strategy backtester; instead we expose
// Long/Short entry signals (plus their SL/TP levels) via register_signal()
// so they can be used in Scanners/Alerts/Strategy Tester components.
describe_indicator('SMC Trap to FVG Signals', 'lower');

const myLookback = input.number('Structure Lookback', 10, { min: 1, max: 200 });
const myCooldown = input.number('Trap Cooldown', 3, { min: 0, max: 100 });
const myWickPercent = input.number('Trap Wick Percent', 0.1, { min: 0, max: 1, step: 0.01 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMultSL = input.number('SL Buffer ATR', 0.3, { min: 0, max: 10, step: 0.1 });

const myAtr = atr(high, low, close, myAtrLen);

// swingHigh/swingLow = highest(high[1], lookback) / lowest(low[1], lookback)
const myShiftedHigh1 = shift(high, 1);
const myShiftedLow1 = shift(low, 1);
const mySwingHigh = highest(myShiftedHigh1, myLookback);
const mySwingLow = lowest(myShiftedLow1, myLookback);

const myBarRange = sub(high, low);
const myUpperWick = sub(high, max_of(open, close));
const myLowerWick = sub(min_of(open, close), low);

const myUpperPct = for_every(myBarRange, myUpperWick, (_br, _uw) => _br > 0 ? _uw / _br : 0);
const myLowerPct = for_every(myBarRange, myLowerWick, (_br, _lw) => _br > 0 ? _lw / _br : 0);

const myHigh2 = shift(high, 2);
const myLow2 = shift(low, 2);

// output series
const myBullTrapSeries = series_of(null);
const myBearTrapSeries = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongSlSeries = series_of(null);
const myLongTpSeries = series_of(null);
const myShortSlSeries = series_of(null);
const myShortTpSeries = series_of(null);

// state kept across the sequential loop (mirrors Pine "var" variables)
let myLastBullTrap = null;
let myLastBearTrap = null;

const myTopArr = [];
const myBotArr = [];
const myBullArr = [];

function myGetNearestFVG(_isLong) {
	let myTarget = null;
	for (let myI = myTopArr.length - 1; myI >= 0; myI -= 1) {
		const myT = myTopArr[myI];
		const myB = myBotArr[myI];
		const myBull = myBullArr[myI];

		if (_isLong && !myBull && myB > close[myCurrentIndexRef.index]) {
			myTarget = myB;
			break;
		}
		if (!_isLong && myBull && myT < close[myCurrentIndexRef.index]) {
			myTarget = myT;
			break;
		}
	}
	return myTarget;
}

// small ref object so myGetNearestFVG can see current index without
// being redeclared on every iteration
const myCurrentIndexRef = { index: 0 };

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myCurrentIndexRef.index = myIndex;

	const myRawBullTrap = (myIndex >= 1) &&
		high[myIndex] > mySwingHigh[myIndex] &&
		close[myIndex] < mySwingHigh[myIndex] &&
		myUpperPct[myIndex] >= myWickPercent;

	const myRawBearTrap = (myIndex >= 1) &&
		low[myIndex] < mySwingLow[myIndex] &&
		close[myIndex] > mySwingLow[myIndex] &&
		myLowerPct[myIndex] >= myWickPercent;

	const myBullTrap = myRawBullTrap && (myLastBullTrap === null || (myIndex - myLastBullTrap) > myCooldown);
	const myBearTrap = myRawBearTrap && (myLastBearTrap === null || (myIndex - myLastBearTrap) > myCooldown);

	if (myBullTrap) {
		myLastBullTrap = myIndex;
	}
	if (myBearTrap) {
		myLastBearTrap = myIndex;
	}

	// FVG detection (needs at least 2 prior candles)
	const myBullFVG = myIndex >= 2 && myHigh2[myIndex] < low[myIndex];
	const myBearFVG = myIndex >= 2 && myLow2[myIndex] > high[myIndex];

	if (myBullFVG) {
		myTopArr.push(low[myIndex]);
		myBotArr.push(myHigh2[myIndex]);
		myBullArr.push(true);
	}
	if (myBearFVG) {
		myTopArr.push(myLow2[myIndex]);
		myBotArr.push(high[myIndex]);
		myBullArr.push(false);
	}

	myBullTrapSeries[myIndex] = myBullTrap ? high[myIndex] : null;
	myBearTrapSeries[myIndex] = myBearTrap ? low[myIndex] : null;

	// LONG on bear trap
	if (myBearTrap) {
		const mySl = low[myIndex] - myAtr[myIndex] * myAtrMultSL;
		const myTp = myGetNearestFVG(true);

		if (myTp !== null && myTp !== undefined && !isNaN(myTp)) {
			myLongEntrySignal[myIndex] = true;
			myLongSlSeries[myIndex] = mySl;
			myLongTpSeries[myIndex] = myTp;
		}
	}

	// SHORT on bull trap
	if (myBullTrap) {
		const mySl = high[myIndex] + myAtr[myIndex] * myAtrMultSL;
		const myTp = myGetNearestFVG(false);

		if (myTp !== null && myTp !== undefined && !isNaN(myTp)) {
			myShortEntrySignal[myIndex] = true;
			myShortSlSeries[myIndex] = mySl;
			myShortTpSeries[myIndex] = myTp;
		}
	}
}

// visual markers for traps
paint(myBullTrapSeries, { style: 'labels_above', color: 'red', name: 'Bull Trap' });
paint(myBearTrapSeries, { style: 'labels_below', color: 'green', name: 'Bear Trap' });

// price-axis levels for the triggered entries (sparse lines)
paint(myLongSlSeries, { style: 'dotted', color: '#ef5350', name: 'Long SL', forceUsePriceAxis: true });
paint(myLongTpSeries, { style: 'dotted', color: '#26a69a', name: 'Long TP', forceUsePriceAxis: true });
paint(myShortSlSeries, { style: 'dotted', color: '#ef5350', name: 'Short SL', forceUsePriceAxis: true });
paint(myShortTpSeries, { style: 'dotted', color: '#26a69a', name: 'Short TP', forceUsePriceAxis: true });

// signals usable in Scanners, Alerts and Strategy Tester
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');