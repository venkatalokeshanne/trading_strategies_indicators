describe_indicator('EMA Ichimoku Base Strategy with RSI Zones', 'lower');

// ----------------------------------------------------
// INPUTS
// ----------------------------------------------------
const rsiTab = input.tab('RSI');
const myRsiLen = rsiTab.number('RSI Length', 7, { min: 1, max: 200 });
const myRsiWmaLen = rsiTab.number('RSI WMA Length', 5, { min: 1, max: 200 });
const rsiRow = rsiTab.row();
const myUpperBand = rsiRow.number('RSI Upper Band', 60.0, { min: 0, max: 100 });
const myMiddleBand = rsiRow.number('RSI Middle Band', 40.0, { min: 0, max: 100 });
const myLowerBand = rsiRow.number('RSI Lower Band', 32.0, { min: 0, max: 100 });

const maTab = input.tab('Moving Averages');
const maRow = maTab.row();
const myEmaLen = maRow.number('EMA Length', 4, { min: 1, max: 500 });
const mySmaLen = maRow.number('SMA Length', 6, { min: 1, max: 500 });
const myKijunLen = maTab.number('Ichimoku Base Line Length', 10, { min: 1, max: 500 });

const myTpPercent = input.number('Take Profit Percent', 30.0, { min: 0, max: 1000 }) / 100.0;

// ----------------------------------------------------
// INDICATORS
// ----------------------------------------------------
const myRsiValue = rsi(close, myRsiLen);
const myRsiWma = wma(myRsiValue, myRsiWmaLen);
const myEmaVal = ema(close, myEmaLen);
const mySmaVal = sma(close, mySmaLen);
const myHighestHigh = highest(high, myKijunLen);
const myLowestLow = lowest(low, myKijunLen);
const myKijun = div(add(myHighestHigh, myLowestLow), 2);

// ----------------------------------------------------
// CROSSOVER / CROSSUNDER HELPERS (computed outside loop)
// ----------------------------------------------------
const mySmaCrossOverRsi = for_every(mySmaVal, myRsiValue, (_s, _r, _p, _i) => {
	if (_i === 0) return false;
	return _s > _r && mySmaVal[_i - 1] <= myRsiValue[_i - 1];
});

const mySmaCrossUnderRsi = for_every(mySmaVal, myRsiValue, (_s, _r, _p, _i) => {
	if (_i === 0) return false;
	return _s < _r && mySmaVal[_i - 1] >= myRsiValue[_i - 1];
});

const myCloseCrossOverEma = for_every(close, myEmaVal, (_c, _e, _p, _i) => {
	if (_i === 0) return false;
	return _c > _e && close[_i - 1] <= myEmaVal[_i - 1];
});

const myCloseCrossUnderEma = for_every(close, myEmaVal, (_c, _e, _p, _i) => {
	if (_i === 0) return false;
	return _c < _e && close[_i - 1] >= myEmaVal[_i - 1];
});

// ----------------------------------------------------
// RSI ZONE CROSS SIGNAL
// ----------------------------------------------------
const mySignalLevel = series_of(null);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myOversoldCross = mySmaCrossOverRsi[myIndex] && myRsiValue[myIndex] <= myLowerBand;
	const myOverboughtCross = mySmaCrossUnderRsi[myIndex] && myRsiValue[myIndex] >= myUpperBand;

	if (myOversoldCross || myOverboughtCross) {
		mySignalLevel[myIndex] = close[myIndex];
	}
}

// ----------------------------------------------------
// STRATEGY STATE SIMULATION (position, stop, tp, exits)
// Position: 0 = flat, 1 = long, -1 = short. Pyramiding allowed up
// to 10 entries, position avg price is the average entry price.
// ----------------------------------------------------
const myLongEntryMark = series_of(null);
const myShortEntryMark = series_of(null);
const myLongExitMark = series_of(null);
const myShortExitMark = series_of(null);

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

const MY_MAX_PYRAMID = 10;
let myPositionSize = 0;
let myAvgPrice = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myCloseVal = close[myIndex];
	const myKijunCur = myKijun[myIndex];
	const myLongEntry = myCloseCrossOverEma[myIndex];
	const myShortEntry = myCloseCrossUnderEma[myIndex];

	// ENTRIES (with pyramiding up to 10)
	if (myLongEntry) {
		if (myPositionSize >= 0 && myPositionSize < MY_MAX_PYRAMID) {
			myAvgPrice = (myAvgPrice * myPositionSize + myCloseVal) / (myPositionSize + 1);
			myPositionSize += 1;
		}
		else if (myPositionSize < 0) {
			myPositionSize = 1;
			myAvgPrice = myCloseVal;
		}
	}

	if (myShortEntry) {
		if (myPositionSize <= 0 && Math.abs(myPositionSize) < MY_MAX_PYRAMID) {
			myAvgPrice = (myAvgPrice * Math.abs(myPositionSize) + myCloseVal) / (Math.abs(myPositionSize) + 1);
			myPositionSize -= 1;
		}
		else if (myPositionSize > 0) {
			myPositionSize = -1;
			myAvgPrice = myCloseVal;
		}
	}

	const myLongStop = myKijunCur;
	const myShortStop = myKijunCur;
	const myLongTp = myAvgPrice * (1 + myTpPercent);
	const myShortTp = myAvgPrice * (1 - myTpPercent);

	const myEmaCrossDown = myCloseCrossUnderEma[myIndex];
	const myEmaCrossUp = myCloseCrossOverEma[myIndex];

	let myLongExit = false;
	let myShortExit = false;

	if (myPositionSize > 0) {
		myLongExit = myEmaCrossDown || myCloseVal <= myLongStop || myCloseVal >= myLongTp;
		if (myLongExit) {
			myPositionSize = 0;
			myAvgPrice = 0;
		}
	}

	if (myPositionSize < 0) {
		myShortExit = myEmaCrossUp || myCloseVal >= myShortStop || myCloseVal <= myShortTp;
		if (myShortExit) {
			myPositionSize = 0;
			myAvgPrice = 0;
		}
	}

	myLongEntryMark[myIndex] = myLongEntry ? constants.icons.arrow_up : null;
	myShortEntryMark[myIndex] = myShortEntry ? constants.icons.arrow_down : null;
	myLongExitMark[myIndex] = myLongExit ? constants.icons.circle : null;
	myShortExitMark[myIndex] = myShortExit ? constants.icons.circle : null;

	myLongEntrySignal[myIndex] = myLongEntry;
	myShortEntrySignal[myIndex] = myShortEntry;
	myLongExitSignal[myIndex] = myLongExit;
	myShortExitSignal[myIndex] = myShortExit;
}

// ----------------------------------------------------
// PLOTS
// ----------------------------------------------------
paint(myEmaVal, { name: 'EMA', color: '#FF9800', thickness: 2 });
paint(mySmaVal, { name: 'SMA', color: '#2196F3', thickness: 2, forceUsePriceAxis: true });
paint(myKijun, { name: 'Ichimoku Base Line', color: '#9C27B0', thickness: 2, forceUsePriceAxis: true });
paint(myRsiValue, { name: 'RSI', color: '#4CAF50', thickness: 1 });
paint(myRsiWma, { name: 'RSI WMA', color: '#F44336', thickness: 1 });
paint(horizontal_line(myUpperBand), { name: 'Upper Band', color: '#F44336', style: 'dotted' });
paint(horizontal_line(myMiddleBand), { name: 'Middle Band', color: 'gray', style: 'dotted' });
paint(horizontal_line(myLowerBand), { name: 'Lower Band', color: '#4CAF50', style: 'dotted' });
paint(mySignalLevel, { name: 'RSI Zone Signal', color: '#4CAF50', thickness: 2, style: 'line', forceUsePriceAxis: true });
paint(myLongEntryMark, { name: 'Long Entry Mark', style: 'labels_below', color: '#4CAF50' });
paint(myShortEntryMark, { name: 'Short Entry Mark', style: 'labels_above', color: '#F44336' });
paint(myLongExitMark, { name: 'Long Exit Mark', style: 'labels_above', color: '#F44336' });
paint(myShortExitMark, { name: 'Short Exit Mark', style: 'labels_below', color: '#4CAF50' });

// ----------------------------------------------------
// SIGNALS (for scanners, alerts, strategy tester)
// Each signal is registered exactly once, with a unique name.
// ----------------------------------------------------
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');