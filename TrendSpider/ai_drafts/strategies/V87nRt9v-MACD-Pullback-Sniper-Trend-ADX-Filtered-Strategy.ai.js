describe_indicator('MACD Pullback Sniper', 'lower');

// NOTE: TrendSpider Custom JS API has no strategy/broker simulation
// (no equity, position sizing, order fills, commissions or slippage).
// This script reproduces the MACD/trend/ADX/zero-line entry logic
// and projects a stop/target level using ATR, but it cannot replicate
// the exact equity-based position sizing or order execution engine
// of the original Pine strategy.

const myMacdTab = input.tab('MACD');
const myFastLen = myMacdTab.number('Fast EMA', 12, { min: 1, max: 200 });
const mySlowLen = myMacdTab.number('Slow EMA', 26, { min: 1, max: 400 });
const mySignalLen = myMacdTab.number('Signal EMA', 9, { min: 1, max: 200 });

const myFiltersTab = input.tab('Filters');
const myUseTrend = myFiltersTab.boolean('Trend filter (price vs EMA)', true);
const myTrendLen = myFiltersTab.number('Trend EMA length', 200, { min: 2, max: 500 });
const myUseZero = myFiltersTab.boolean('Zero line filter', true);
const myUseAdx = myFiltersTab.boolean('ADX filter', true);
const myAdxRow = myFiltersTab.row();
const myAdxLen = myAdxRow.number('ADX length', 14, { min: 1, max: 100 });
const myAdxMin = myAdxRow.number('ADX minimum', 20, { min: 1, max: 100 });

const myRiskTab = input.tab('Risk');
const myAtrLen = myRiskTab.number('ATR length', 14, { min: 1, max: 100 });
const mySlMult = myRiskTab.number('Stop distance (x ATR)', 2, { min: 0.1, max: 20 });
const myRrRatio = myRiskTab.number('Reward Risk', 2, { min: 0.5, max: 20 });
const myExitCross = myRiskTab.boolean('Exit on opposite MACD cross', true);

const myGeneralTab = input.tab('General');
const myAllowShort = myGeneralTab.boolean('Allow shorts', true);
const myStartTime = myGeneralTab.number('Start timestamp (unix)', 1514764800);
const myEndTime = myGeneralTab.number('End timestamp (unix)', 3155673540);

// --- Core calculations ---
const myFastEma = ema(close, myFastLen);
const mySlowEma = ema(close, mySlowLen);
const myMacdLine = sub(myFastEma, mySlowEma);
const mySignalLine = ema(myMacdLine, mySignalLen);
const myHist = sub(myMacdLine, mySignalLine);

const myTrendEma = ema(close, myTrendLen);
const myAdxObject = indicators.adx(myAdxLen);
const myAtr = atr(high, low, close, myAtrLen);

const myN = close.length;

const myBullCross = series_of(false);
const myBearCross = series_of(false);
for (let myIndex = 1; myIndex < myN; myIndex += 1) {
	myBullCross[myIndex] = myMacdLine[myIndex] > mySignalLine[myIndex] && myMacdLine[myIndex - 1] <= mySignalLine[myIndex - 1];
	myBearCross[myIndex] = myMacdLine[myIndex] < mySignalLine[myIndex] && myMacdLine[myIndex - 1] >= mySignalLine[myIndex - 1];
}

const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const mySlLine = series_of(null);
const myTpLine = series_of(null);

// 0 = flat, 1 = long, -1 = short
let myPositionState = 0;
let myEntryAtr = null;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myInRange = time[myIndex] >= myStartTime && time[myIndex] <= myEndTime;

	const myTrendLongOk = !myUseTrend || close[myIndex] > myTrendEma[myIndex];
	const myTrendShortOk = !myUseTrend || close[myIndex] < myTrendEma[myIndex];
	const myZeroLongOk = !myUseZero || myMacdLine[myIndex] < 0;
	const myZeroShortOk = !myUseZero || myMacdLine[myIndex] > 0;
	const myAdxOk = !myUseAdx || myAdxObject.adx[myIndex] > myAdxMin;

	const myLongCandidate = myBullCross[myIndex] && myTrendLongOk && myZeroLongOk && myAdxOk && myInRange;
	const myShortCandidate = myBearCross[myIndex] && myTrendShortOk && myZeroShortOk && myAdxOk && myInRange && myAllowShort;

	myLongSignal[myIndex] = myLongCandidate && myPositionState <= 0;
	myShortSignal[myIndex] = myShortCandidate && myPositionState >= 0;

	// exit on opposite cross
	if (myExitCross && myBearCross[myIndex] && myPositionState > 0 && !myShortSignal[myIndex]) {
		myPositionState = 0;
		myEntryAtr = null;
		myEntryPrice = null;
	}
	if (myExitCross && myBullCross[myIndex] && myPositionState < 0 && !myLongSignal[myIndex]) {
		myPositionState = 0;
		myEntryAtr = null;
		myEntryPrice = null;
	}

	if (myLongSignal[myIndex]) {
		myPositionState = 1;
		myEntryAtr = myAtr[myIndex];
		myEntryPrice = close[myIndex];
	}
	else if (myShortSignal[myIndex]) {
		myPositionState = -1;
		myEntryAtr = myAtr[myIndex];
		myEntryPrice = close[myIndex];
	}

	// check stop/target hit (approximation using high/low of current candle)
	if (myPositionState === 1 && myEntryAtr !== null) {
		const myStop = myEntryPrice - myEntryAtr * mySlMult;
		const myTarget = myEntryPrice + myEntryAtr * mySlMult * myRrRatio;
		mySlLine[myIndex] = myStop;
		myTpLine[myIndex] = myTarget;
		if (low[myIndex] <= myStop || high[myIndex] >= myTarget) {
			myPositionState = 0;
			myEntryAtr = null;
			myEntryPrice = null;
		}
	}
	else if (myPositionState === -1 && myEntryAtr !== null) {
		const myStop = myEntryPrice + myEntryAtr * mySlMult;
		const myTarget = myEntryPrice - myEntryAtr * mySlMult * myRrRatio;
		mySlLine[myIndex] = myStop;
		myTpLine[myIndex] = myTarget;
		if (high[myIndex] >= myStop || low[myIndex] <= myTarget) {
			myPositionState = 0;
			myEntryAtr = null;
			myEntryPrice = null;
		}
	}
}

const myHistColor = for_every(myHist, shift(myHist, 1), (_h, _hPrev) => {
	if (_h >= 0) {
		return _h > _hPrev ? '#00897B' : '#80CBC4';
	}
	return _h < _hPrev ? '#E53935' : '#EF9A9A';
});

paint(myHist, { name: 'Histogram', style: 'column', color: myHistColor });
paint(myMacdLine, { name: 'MACD', color: '#1E88E5', thickness: 2 });
paint(mySignalLine, { name: 'Signal', color: '#FB8C00', thickness: 1 });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });

paint(myTrendEma, { name: 'Trend EMA', color: '#9E9E9E', thickness: 2, forceUsePriceAxis: true });
paint(mySlLine, { name: 'Stop', color: 'red', style: 'ladder', forceUsePriceAxis: true });
paint(myTpLine, { name: 'Target', color: 'green', style: 'ladder', forceUsePriceAxis: true });

const myLongMarks = for_every(myLongSignal, low, (_isLong, _low) => _isLong ? _low : null);
const myShortMarks = for_every(myShortSignal, high, (_isShort, _high) => _isShort ? _high : null);

paint(myLongMarks, { name: 'Long', style: 'labels_below', color: '#00897B' });
paint(myShortMarks, { name: 'Short', style: 'labels_above', color: '#E53935' });

register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');
register_signal(myBullCross, 'MACD Bull Cross');
register_signal(myBearCross, 'MACD Bear Cross');