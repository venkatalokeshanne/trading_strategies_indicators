describe_indicator('NQ Scalp Fix Plus Signals', 'price');

// === INPUTS ===
const tabMA = input.tab('Moving Averages');
const myEmaFastLen = tabMA.number('EMA Fast', 5, { min: 1, max: 500 });
const myEmaMidLen = tabMA.number('EMA Mid', 24, { min: 1, max: 500 });
const myEmaSlowLen = tabMA.number('EMA Slow', 150, { min: 1, max: 1000 });
const myEma600Len = tabMA.number('EMA 600 Length', 600, { min: 1, max: 2000 });

const tabRsi = input.tab('RSI');
const myRsiLen = tabRsi.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiBull = tabRsi.number('RSI Bull Level', 55, { min: 1, max: 99 });
const myRsiBear = tabRsi.number('RSI Bear Level', 45, { min: 1, max: 99 });

const tabRisk = input.tab('Risk');
const myAtrLen = tabRisk.number('ATR Length', 14, { min: 1, max: 200 });
const mySlAtr = tabRisk.number('Stop Loss ATR Mult', 1.5, { min: 0.1, max: 20 });
const myTpAtr = tabRisk.number('Take Profit ATR Mult', 2.5, { min: 0.1, max: 20 });

// === CALC (built-in functions, computed once, outside any loop) ===
const myEmaFast = ema(close, myEmaFastLen);
const myEmaMid = ema(close, myEmaMidLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myEma600 = ema(close, myEma600Len);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);

// === SIMULATION LOOP (position state is inherently sequential, so a loop is required) ===
const myCandleCount = close.length;
const myPositionSize = series_of(0);     // -1 short, 0 flat, 1 long
const myAvgPrice = series_of(null);
const myLongSlLine = series_of(null);
const myLongTpLine = series_of(null);
const myShortSlLine = series_of(null);
const myShortTpLine = series_of(null);
const myLongEntered = series_of(false);
const myShortEntered = series_of(false);
const myLongClosed = series_of(false);
const myShortClosed = series_of(false);
const myBullTrend = series_of(false);
const myBearTrend = series_of(false);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myPrevPosition = myIndex > 0 ? myPositionSize[myIndex - 1] : 0;
	const myPrevAvgPrice = myIndex > 0 ? myAvgPrice[myIndex - 1] : null;
	let myCurrentPosition = myPrevPosition;
	let myCurrentAvgPrice = myPrevAvgPrice;

	const myBull = myEmaFast[myIndex] > myEmaMid[myIndex] && myEmaMid[myIndex] > myEmaSlow[myIndex];
	const myBear = myEmaFast[myIndex] < myEmaMid[myIndex] && myEmaMid[myIndex] < myEmaSlow[myIndex];
	myBullTrend[myIndex] = myBull;
	myBearTrend[myIndex] = myBear;

	// crossover / crossunder of close vs e_fast, using previous candle values
	const myCrossover = myIndex > 0 &&
		close[myIndex - 1] <= myEmaFast[myIndex - 1] &&
		close[myIndex] > myEmaFast[myIndex];

	const myCrossunder = myIndex > 0 &&
		close[myIndex - 1] >= myEmaFast[myIndex - 1] &&
		close[myIndex] < myEmaFast[myIndex];

	const myLongCond = myBull && myCrossover && myRsi[myIndex] > myRsiBull;
	const myShortCond = myBear && myCrossunder && myRsi[myIndex] < myRsiBear;

	let myDidClose = false;
	let myWasLong = false;
	let myWasShort = false;

	// === EXIT: check stop/limit touch using this candle's high/low ===
	if (myCurrentPosition > 0) {
		const myLongSl = myCurrentAvgPrice - myAtr[myIndex] * mySlAtr;
		const myLongTp = myCurrentAvgPrice + myAtr[myIndex] * myTpAtr;

		if (low[myIndex] <= myLongSl || high[myIndex] >= myLongTp) {
			myCurrentPosition = 0;
			myCurrentAvgPrice = null;
			myDidClose = true;
			myWasLong = true;
		}
	}
	else if (myCurrentPosition < 0) {
		const myShortSl = myCurrentAvgPrice + myAtr[myIndex] * mySlAtr;
		const myShortTp = myCurrentAvgPrice - myAtr[myIndex] * myTpAtr;

		if (high[myIndex] >= myShortSl || low[myIndex] <= myShortTp) {
			myCurrentPosition = 0;
			myCurrentAvgPrice = null;
			myDidClose = true;
			myWasShort = true;
		}
	}

	// === ENTRY: only if flat ===
	let myDidEnterLong = false;
	let myDidEnterShort = false;

	if (myCurrentPosition === 0) {
		if (myLongCond) {
			myCurrentPosition = 1;
			myCurrentAvgPrice = close[myIndex];
			myDidEnterLong = true;
		}
		else if (myShortCond) {
			myCurrentPosition = -1;
			myCurrentAvgPrice = close[myIndex];
			myDidEnterShort = true;
		}
	}

	myPositionSize[myIndex] = myCurrentPosition;
	myAvgPrice[myIndex] = myCurrentAvgPrice;
	myLongEntered[myIndex] = myDidEnterLong;
	myShortEntered[myIndex] = myDidEnterShort;
	myLongClosed[myIndex] = myDidClose && myWasLong;
	myShortClosed[myIndex] = myDidClose && myWasShort;

	if (myCurrentPosition > 0) {
		myLongSlLine[myIndex] = myCurrentAvgPrice - myAtr[myIndex] * mySlAtr;
		myLongTpLine[myIndex] = myCurrentAvgPrice + myAtr[myIndex] * myTpAtr;
	}
	else if (myCurrentPosition < 0) {
		myShortSlLine[myIndex] = myCurrentAvgPrice + myAtr[myIndex] * mySlAtr;
		myShortTpLine[myIndex] = myCurrentAvgPrice - myAtr[myIndex] * myTpAtr;
	}
}

// === CANDLE COLORING ===
const myCandleColors = for_every(myEmaFast, myEmaMid, myEmaSlow, (_myFast, _myMid, _mySlow) => {
	if (_myFast > _myMid && _myMid > _mySlow) return '#0ce600';
	if (_myFast < _myMid && _myMid < _mySlow) return '#dd0000';
	return '#dbd700';
});
color_candles(myCandleColors);

// === PLOTS: moving averages ===
paint(myEmaFast, { name: 'EMA Fast', color: '#00bbd4', thickness: 1 });
paint(myEmaMid, { name: 'EMA Mid', color: '#ff9900', style: 'dotted', thickness: 1 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#df40fb', style: 'line', thickness: 1 });
paint(myEma600, { name: 'EMA 600', color: 'blue', style: 'dotted', thickness: 1 });

// === ENTRY / EXIT SIGNAL MARKERS ===
const myLongEntryMarker = series_of(null);
const myShortEntryMarker = series_of(null);
const myLongExitMarker = series_of(null);
const myShortExitMarker = series_of(null);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	myLongEntryMarker[myIndex] = myLongEntered[myIndex] ? low[myIndex] : null;
	myShortEntryMarker[myIndex] = myShortEntered[myIndex] ? high[myIndex] : null;
	myLongExitMarker[myIndex] = myLongClosed[myIndex] ? high[myIndex] : null;
	myShortExitMarker[myIndex] = myShortClosed[myIndex] ? low[myIndex] : null;
}

// Note: markers are painted with "Marker" suffixes so their names
// never collide with the register_signal() names below. The engine
// shares one naming namespace across paint() and register_signal(),
// so reusing the same name for both caused the
// "signal already exists" error.
paint(myLongEntryMarker, { name: 'Long Entry Marker', style: 'labels_below', color: 'lime' });
paint(myShortEntryMarker, { name: 'Short Entry Marker', style: 'labels_above', color: 'red' });
paint(myLongExitMarker, { name: 'Long Exit Marker', style: 'labels_above', color: '#4caf4f' });
paint(myShortExitMarker, { name: 'Short Exit Marker', style: 'labels_below', color: '#ff9900' });

// === SL / TP LINES ===
paint(myLongSlLine, { name: 'Long Stop Loss', color: '#ff5252', style: 'line' });
paint(myLongTpLine, { name: 'Long Take Profit', color: '#4caf4f', style: 'line' });
paint(myShortSlLine, { name: 'Short Stop Loss', color: '#ff5252', style: 'line' });
paint(myShortTpLine, { name: 'Short Take Profit', color: '#4caf4f', style: 'line' });

// === SIGNALS FOR SCANNERS / ALERTS / STRATEGY TESTER ===
register_signal(myLongEntered, 'Long Entry Signal');
register_signal(myShortEntered, 'Short Entry Signal');
register_signal(myLongClosed, 'Long Exit Signal');
register_signal(myShortClosed, 'Short Exit Signal');
register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');