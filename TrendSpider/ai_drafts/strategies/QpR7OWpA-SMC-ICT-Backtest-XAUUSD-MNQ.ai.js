describe_indicator('SMC ICT XAUUSD MNQ', 'price');

// NOTE: this reproduces the Pine Script's SIGNAL logic (sweeps, MSS, FVG,
// session filter, buy/sell triggers) as closely as the platform allows.
// There is no broker/strategy simulation engine available in Custom JS
// (no strategy.entry/strategy.exit, no actual position tracking, no
// stop/limit order execution). We expose buy/sell entry signals plus the
// theoretical SL/TP levels for the signal bar only, which is the closest
// equivalent achievable here.

const myswingLen = input.number('Swing Length', 5, { min: 1, max: 50 });
const myrr = input.number('Risk Reward', 2.0, { min: 0.1, max: 20, step: 0.5 });

// ===== SESSIONS =====
// Pine's time(timeframe.period, "0700-1000") uses the exchange timezone,
// same as time_of() here.
function myInSessionRange(myHours, myMinutes, myFromH, myFromM, myToH, myToM) {
	const myTotal = myHours * 60 + myMinutes;
	const myFrom = myFromH * 60 + myFromM;
	const myTo = myToH * 60 + myToM;
	return myTotal >= myFrom && myTotal < myTo;
}

const myTradeSession = time.map(_t => {
	const myParsed = time_of(_t);
	const myLondon = myInSessionRange(myParsed.hours, myParsed.minutes, 7, 0, 10, 0);
	const myNewYork = myInSessionRange(myParsed.hours, myParsed.minutes, 12, 30, 16, 0);
	return myLondon || myNewYork;
});

// ===== SWINGS =====
// pivot_high/pivot_low with equal left/right length match ta.pivothigh/pivotlow
const myPivotHigh = pivot_high(high, myswingLen, myswingLen);
const myPivotLow = pivot_low(low, myswingLen, myswingLen);

const myLastHigh = series_of(null);
const myLastLow = series_of(null);

const myBullSweep = series_of(false);
const myBearSweep = series_of(false);
const myBullMSS = series_of(false);
const myBearMSS = series_of(false);
const myBullFVG = series_of(false);
const myBearFVG = series_of(false);
const myBuy = series_of(false);
const mySell = series_of(false);

const myBuySLArr = series_of(null);
const myBuyTPArr = series_of(null);
const mySellSLArr = series_of(null);
const mySellTPArr = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// forward-fill last pivot high/low, like Pine's "var" persistence
	myLastHigh[myIndex] = myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined
		? myPivotHigh[myIndex]
		: (myIndex > 0 ? myLastHigh[myIndex - 1] : null);

	myLastLow[myIndex] = myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined
		? myPivotLow[myIndex]
		: (myIndex > 0 ? myLastLow[myIndex - 1] : null);

	const myPrevHigh = myIndex >= 1 ? high[myIndex - 1] : null;
	const myPrevLow = myIndex >= 1 ? low[myIndex - 1] : null;
	const myPrev2High = myIndex >= 2 ? high[myIndex - 2] : null;
	const myPrev2Low = myIndex >= 2 ? low[myIndex - 2] : null;

	myBullSweep[myIndex] = myLastLow[myIndex] !== null && low[myIndex] < myLastLow[myIndex] && close[myIndex] > myLastLow[myIndex];
	myBearSweep[myIndex] = myLastHigh[myIndex] !== null && high[myIndex] > myLastHigh[myIndex] && close[myIndex] < myLastHigh[myIndex];

	myBullMSS[myIndex] = myBullSweep[myIndex] && myPrevHigh !== null && close[myIndex] > myPrevHigh;
	myBearMSS[myIndex] = myBearSweep[myIndex] && myPrevLow !== null && close[myIndex] < myPrevLow;

	myBullFVG[myIndex] = myPrev2High !== null && low[myIndex] > myPrev2High;
	myBearFVG[myIndex] = myPrev2Low !== null && high[myIndex] < myPrev2Low;

	myBuy[myIndex] = myTradeSession[myIndex] && myBullMSS[myIndex] && myBullFVG[myIndex];
	mySell[myIndex] = myTradeSession[myIndex] && myBearMSS[myIndex] && myBearFVG[myIndex];

	if (myBuy[myIndex]) {
		const myBuySL = low[myIndex];
		const myBuyRisk = close[myIndex] - myBuySL;
		myBuySLArr[myIndex] = myBuySL;
		myBuyTPArr[myIndex] = close[myIndex] + myBuyRisk * myrr;
	}

	if (mySell[myIndex]) {
		const mySellSL = high[myIndex];
		const mySellRisk = mySellSL - close[myIndex];
		mySellSLArr[myIndex] = mySellSL;
		mySellTPArr[myIndex] = close[myIndex] - mySellRisk * myrr;
	}
}

// ===== VISUALS =====
const myBuyMarks = for_every(close, (_c, _p, _i) => myBuy[_i] ? constants.icons.triangle_up : null);
const mySellMarks = for_every(close, (_c, _p, _i) => mySell[_i] ? constants.icons.triangle_down : null);

paint(myBuyMarks, { style: 'labels_below', color: '#26A69A', name: 'Buy' });
paint(mySellMarks, { style: 'labels_above', color: '#EF5350', name: 'Sell' });

// theoretical SL/TP levels, shown only on the signal bar
paint(myBuySLArr, { style: 'dotted', color: '#26A69A', name: 'Buy Stop Loss', forceUsePriceAxis: true });
paint(myBuyTPArr, { style: 'dotted', color: '#1E88E5', name: 'Buy Take Profit', forceUsePriceAxis: true });
paint(mySellSLArr, { style: 'dotted', color: '#EF5350', name: 'Sell Stop Loss', forceUsePriceAxis: true });
paint(mySellTPArr, { style: 'dotted', color: '#1E88E5', name: 'Sell Take Profit', forceUsePriceAxis: true });

// ===== SIGNALS (for scanners/alerts/backtests) =====
register_signal(myBuy, 'Buy Signal');
register_signal(mySell, 'Sell Signal');