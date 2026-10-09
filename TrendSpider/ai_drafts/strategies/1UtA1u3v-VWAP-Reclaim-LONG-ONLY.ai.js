describe_indicator('VWAP Squeeze Reclaim (LONG ONLY)', 'price');

// NOTE: this script approximates several TradingView built-ins
// (ta.vwap daily reset, ta.supertrend, ta.dmi) using the closest
// equivalents available in the Custom JS API. See flagged notes.

const myBBLength = input.number('BB Length', 20, { min: 1, max: 300 });
const myBBMult = input.number('BB Multiplier', 2.0, { min: 0.1, max: 10 });
const myRSILength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myEntryCutoffHour = input.number('Entry Cutoff Hour', 15, { min: 0, max: 23 });
const myEntryCutoffMinute = input.number('Entry Cutoff Minute', 0, { min: 0, max: 59 });

// === Daily-reset VWAP (approximates ta.vwap(close) which resets per session) ===
const mySessionAtIndex = time.map(_t => bar_at(_t).session);
const myVwap = series_of(null);
{
	let myCumPV = 0;
	let myCumVol = 0;
	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const myNewSession = myIndex === 0 || mySessionAtIndex[myIndex] !== mySessionAtIndex[myIndex - 1];
		if (myNewSession) {
			myCumPV = 0;
			myCumVol = 0;
		}
		myCumPV += close[myIndex] * volume[myIndex];
		myCumVol += volume[myIndex];
		myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : close[myIndex];
	}
}

// === Bollinger Bands ===
const myBasis = sma(close, myBBLength);
const myDev = mult(stdev(close, myBBLength), myBBMult);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);
const myBBWidth = div(sub(myUpper, myLower), myBasis);

// === MACD (ta.macd equivalent) ===
const myMacdLine = sub(ema(close, 12), ema(close, 26));
const mySignalLine = ema(myMacdLine, 9);

// === RSI ===
const myRsi = rsi(close, myRSILength);

// === DMI / ADX ===
const myAdxObject = indicators.adx(14);

// === Supertrend ===
// Assumption: supertrend() returns an object with { trend, direction },
// mirroring the pattern used by other multi-output indicators (e.g. vortex()).
const mySupertrendObject = supertrend(21, 1.5, false);
const mySupertrendLine = mySupertrendObject.trend !== undefined ? mySupertrendObject.trend : mySupertrendObject;
const mySupertrendDirection = mySupertrendObject.direction !== undefined ? mySupertrendObject.direction : series_of(null);

// === Time info per candle ===
const myHourAtIndex = time.map(_t => time_of(_t).hours);
const myMinuteAtIndex = time.map(_t => time_of(_t).minutes);

// === Build signals with stateful simulation of strategy.position_size ===
const myBuySignalRaw = series_of(false);
const myExitSignalRaw = series_of(false);
const myPositionState = series_of(0);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myAboveVWAP = close[myIndex] > myVwap[myIndex];
	const myBelowVWAP = close[myIndex] < myVwap[myIndex];
	const myVwapCrossDown = myIndex > 0 && close[myIndex - 1] >= myVwap[myIndex - 1] && close[myIndex] < myVwap[myIndex];

	const myMacdBull = myMacdLine[myIndex] > mySignalLine[myIndex];
	const myDmiBull = myAdxObject.dmiPlus[myIndex] > myAdxObject.dmiMinus[myIndex];
	const mySupertrendBull = mySupertrendDirection[myIndex] < 0;

	const myNoNewEntries = (myHourAtIndex[myIndex] > myEntryCutoffHour) ||
		(myHourAtIndex[myIndex] === myEntryCutoffHour && myMinuteAtIndex[myIndex] >= myEntryCutoffMinute);

	const myBuyCondition = mySupertrendDirection[myIndex] < 0 &&
		myAboveVWAP &&
		myMacdBull &&
		!myNoNewEntries &&
		myMacdLine[myIndex] > 0 &&
		myRsi[myIndex] < 60 &&
		myDmiBull &&
		mySupertrendBull;

	const mySellCondition = myVwapCrossDown ||
		myBelowVWAP ||
		myMacdLine[myIndex] < mySignalLine[myIndex] ||
		mySupertrendDirection[myIndex] > 0;

	const myPrevPosition = myIndex > 0 ? myPositionState[myIndex - 1] : 0;
	let myCurrentPosition = myPrevPosition;

	myBuySignalRaw[myIndex] = myBuyCondition && myPrevPosition === 0;
	if (myBuySignalRaw[myIndex]) {
		myCurrentPosition = 1;
	}

	myExitSignalRaw[myIndex] = mySellCondition && myCurrentPosition > 0;
	if (myExitSignalRaw[myIndex]) {
		myCurrentPosition = 0;
	}

	myPositionState[myIndex] = myCurrentPosition;
}

// === Plots ===
const mySupertrendColor = for_every(mySupertrendDirection, _d => _d < 0 ? 'green' : 'red');
paint(mySupertrendLine, { name: 'Supertrend', color: mySupertrendColor, thickness: 2 });
paint(myVwap, { name: 'VWAP', color: 'blue', thickness: 1 });

// === Signal markers ===
const myBuyMarks = for_every(myBuySignalRaw, _b => _b ? 1 : null);
const myExitMarks = for_every(myExitSignalRaw, _e => _e ? 1 : null);
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(myExitMarks, { name: 'Exit', style: 'labels_above', color: 'red' });

// === Signals for scanner / alerts / strategy tester ===
register_signal(myBuySignalRaw, 'Buy Signal');
register_signal(myExitSignalRaw, 'Exit Signal');