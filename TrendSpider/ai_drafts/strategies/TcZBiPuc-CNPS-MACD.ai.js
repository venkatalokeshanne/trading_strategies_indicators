describe_indicator('CNPS1 MACD Strategy', 'price');

// ===== INPUTS =====
const myUseTP = input.boolean('Use Take Profit (TP)', true);
const myTradeMode = input.select('Trade Mode', 'Both', ['Long Only', 'Short Only', 'Both']);
const mySlPoints = input.number('Stop Loss (points)', 10, { min: 0 });
const myTpPoints = input.number('Take Profit (points)', 30, { min: 0 });

// ===== MACD =====
const myFastEma = ema(close, 12);
const mySlowEma = ema(close, 26);
const myMacdLine = sub(myFastEma, mySlowEma);
const mySignalLine = ema(myMacdLine, 9);

// ===== CONDITIONS (crossover / crossunder) =====
// crossover: macd was <= signal, now > signal
// crossunder: macd was >= signal, now < signal
const myLongCondition = series_of(false);
const myCloseLongCond = series_of(false);
const myShortCondition = series_of(false);
const myCloseShortCond = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevDiff = myMacdLine[myIndex - 1] - mySignalLine[myIndex - 1];
	const myCurrDiff = myMacdLine[myIndex] - mySignalLine[myIndex];

	const myCrossover = myPrevDiff <= 0 && myCurrDiff > 0;
	const myCrossunder = myPrevDiff >= 0 && myCurrDiff < 0;

	myLongCondition[myIndex] = myCrossover;
	myCloseLongCond[myIndex] = myCrossunder;

	myShortCondition[myIndex] = myCrossunder;
	myCloseShortCond[myIndex] = myCrossover;
}

// ===== POSITION SIMULATION (replicates strategy.entry/exit/close logic) =====
// position: 0 = flat, 1 = long, -1 = short
const myLongSlSeries = series_of(null);
const myLongTpSeries = series_of(null);
const myShortSlSeries = series_of(null);
const myShortTpSeries = series_of(null);

const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);

let myPosition = 0;
let myAvgPrice = null;

const myAllowLong = (myTradeMode === 'Both' || myTradeMode === 'Long Only');
const myAllowShort = (myTradeMode === 'Both' || myTradeMode === 'Short Only');

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrice = close[myIndex];
	let myEntered = false;
	let myExited = false;

	// entries (only when flat, mirroring Pine's single-position behavior)
	if (myPosition === 0 && myLongCondition[myIndex] && myAllowLong) {
		myPosition = 1;
		myAvgPrice = myPrice;
		myEntered = true;
		myLongEntrySignal[myIndex] = true;
	}
	else if (myPosition === 0 && myShortCondition[myIndex] && myAllowShort) {
		myPosition = -1;
		myAvgPrice = myPrice;
		myEntered = true;
		myShortEntrySignal[myIndex] = true;
	}

	// exits via SL/TP touch or opposite cross
	if (myPosition === 1) {
		const myLongSl = myAvgPrice - mySlPoints;
		const myLongTp = myAvgPrice + myTpPoints;

		myLongSlSeries[myIndex] = myLongSl;
		myLongTpSeries[myIndex] = myUseTP ? myLongTp : null;

		const mySlHit = low[myIndex] <= myLongSl;
		const myTpHit = myUseTP && high[myIndex] >= myLongTp;

		if (mySlHit || myTpHit || myCloseLongCond[myIndex]) {
			myPosition = 0;
			myAvgPrice = null;
			myExited = true;
		}
	}
	else if (myPosition === -1) {
		const myShortSl = myAvgPrice + mySlPoints;
		const myShortTp = myAvgPrice - myTpPoints;

		myShortSlSeries[myIndex] = myShortSl;
		myShortTpSeries[myIndex] = myUseTP ? myShortTp : null;

		const mySlHit = high[myIndex] >= myShortSl;
		const myTpHit = myUseTP && low[myIndex] <= myShortTp;

		if (mySlHit || myTpHit || myCloseShortCond[myIndex]) {
			myPosition = 0;
			myAvgPrice = null;
			myExited = true;
		}
	}

	myEntrySignal[myIndex] = myEntered;
	myExitSignal[myIndex] = myExited;
}

// ===== PAINTING =====
paint(myLongSlSeries, { name: 'Long Stop Loss', color: 'red', style: 'line' });
paint(myLongTpSeries, { name: 'Long Take Profit', color: 'green', style: 'line' });
paint(myShortSlSeries, { name: 'Short Stop Loss', color: 'red', style: 'line' });
paint(myShortTpSeries, { name: 'Short Take Profit', color: 'green', style: 'line' });

// ===== SIGNALS (for scanners, alerts, strategy tester) =====
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myExitSignal, 'Exit Position');
register_signal(myLongCondition, 'MACD Crossover');
register_signal(myShortCondition, 'MACD Crossunder');