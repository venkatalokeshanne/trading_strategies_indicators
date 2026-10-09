describe_indicator('RSI Gauss Velocity Strategy', 'price');

// -------------------------------------------------------------------
// Converted from a TradingView Pine Script v6 strategy. Pine's
// strategy.* calls (entry/close/position tracking) have no 1:1
// equivalent in TrendSpider Custom JS; this script reproduces the
// exact same math (RSI, Stochastic RSI, 4-pole Gaussian filter,
// slope exhaustion) and exposes long/exit conditions as signals
// (via register_signal) so they can be used in Scanner/Alerts/
// Strategy Tester, plus paints the Gaussian filter and High Band.
// -------------------------------------------------------------------

const myLengthRSI = input.number('RSI Length', 14, { min: 1, max: 200 });
const myLengthStoch = input.number('Stochastic Length', 14, { min: 1, max: 200 });
const mySmoothK = input.number('Smooth K', 3, { min: 1, max: 50 });
const mySmoothD = input.number('Smooth D', 3, { min: 1, max: 50 });

const myGaussianPoles = input.number('Gaussian Poles', 4, { min: 1, max: 4 });
const mySamplingPeriod = input.number('Sampling Period', 144, { min: 2, max: 2000 });
const myBandMultiplier = input.number('Band Multiplier', 1.414, { min: 0.1, max: 10 });

const myStartTimestamp = input.number('Start Date (unix seconds)', 1414800000, { min: 0 });
const myEndTimestamp = input.number('End Date (unix seconds)', 1893455940, { min: 0 });

const myN = close.length;

// --- Core Stochastic RSI ---
const myRsiValue = rsi(close, myLengthRSI);
const myStochRaw = stochastic(myRsiValue, myRsiValue, myRsiValue, myLengthStoch);
const myKValue = sma(myStochRaw, mySmoothK);
const myDValue = sma(myKValue, mySmoothD);

// --- True Range (manual, matches Pine's ta.tr(true)) ---
const myTrueRange = series_of(null);
for (let myIdx = 0; myIdx < myN; myIdx += 1) {
	if (myIdx === 0) {
		myTrueRange[myIdx] = high[myIdx] - low[myIdx];
	}
	else {
		const myRange1 = high[myIdx] - low[myIdx];
		const myRange2 = Math.abs(high[myIdx] - close[myIdx - 1]);
		const myRange3 = Math.abs(low[myIdx] - close[myIdx - 1]);
		myTrueRange[myIdx] = Math.max(myRange1, myRange2, myRange3);
	}
}

// --- Gaussian Filter Math (recursive 4-pole filter, f_filt9x) ---
const myBeta = (1 - Math.cos((4 * Math.asin(1)) / mySamplingPeriod)) / (Math.pow(1.414, 2.0 / myGaussianPoles) - 1);
const myAlpha = -myBeta + Math.sqrt(myBeta * myBeta + 2 * myBeta);

function computeGaussFilter(mySource, myOrder) {
	const myResult = series_of(0);
	const myX = 1 - myAlpha;
	const myM2 = myOrder === 4 ? 6 : myOrder === 3 ? 3 : myOrder === 2 ? 1 : 0;
	const myM3 = myOrder === 4 ? 4 : myOrder === 3 ? 1 : 0;
	const myM4 = myOrder === 4 ? 1 : 0;

	for (let myIdx = 0; myIdx < myN; myIdx += 1) {
		const myF1 = myIdx >= 1 ? myResult[myIdx - 1] : 0;
		const myF2 = myIdx >= 2 ? myResult[myIdx - 2] : 0;
		const myF3 = myIdx >= 3 ? myResult[myIdx - 3] : 0;
		const myF4 = myIdx >= 4 ? myResult[myIdx - 4] : 0;

		let myValue = Math.pow(myAlpha, myOrder) * (mySource[myIdx] || 0) + myOrder * myX * myF1;
		if (myOrder >= 2) myValue -= myM2 * Math.pow(myX, 2) * myF2;
		if (myOrder >= 3) myValue += myM3 * Math.pow(myX, 3) * myF3;
		if (myOrder >= 4) myValue -= myM4 * Math.pow(myX, 4) * myF4;

		myResult[myIdx] = myValue;
	}

	return myResult;
}

const myFiltN = computeGaussFilter(hlc3, myGaussianPoles);
const myFiltTR = computeGaussFilter(myTrueRange, myGaussianPoles);
const myHBand = add(myFiltN, mult(myFiltTR, myBandMultiplier));

// --- Momentum Velocity Logic ---
const myFiltSlope = sub(myFiltN, shift(myFiltN, 1));
const mySlopeMean = sma(myFiltSlope, 20);
const mySlopeStd = stdev(myFiltSlope, 20);

const mySlopeExhaustion = for_every(myFiltSlope, mySlopeMean, mySlopeStd, (_slope, _mean, _std) => _slope < (_mean - _std));

// --- Strategy conditions ---
const myGaussianGreen = for_every(myFiltN, shift(myFiltN, 1), (_f, _fPrev) => _f > _fPrev);
const myStochSignal = for_every(myKValue, myDValue, (_k, _d) => _k > _d);

const myTimeFilter = for_every(time, (_t) => _t >= myStartTimestamp && _t <= myEndTimestamp);

const myLongCondition = for_every(myGaussianGreen, close, myHBand, myStochSignal, myTimeFilter, (_green, _close, _hband, _stoch, _timeOk) => Boolean(_green && _close > _hband && _stoch && _timeOk));

// strategy.position_size / position_avg_price have no equivalent here;
// approximated "inProfit" with close > previous bar's hband-cross entry
// is not reproducible exactly, so we approximate inProfit as "price
// currently above the Gaussian filter line" (a reasonable in-trend proxy).
const myInProfitProxy = for_every(close, myFiltN, (_close, _filt) => _close > _filt);

const myCrossUnder = for_every(close, myHBand, shift(close, 1), shift(myHBand, 1), (_close, _hband, _closePrev, _hbandPrev) => Boolean(_closePrev >= _hbandPrev && _close < _hband));

const myExitCondition = for_every(myCrossUnder, mySlopeExhaustion, myInProfitProxy, close, myHBand, shift(myHBand, 1), (_crossUnder, _exhaustion, _inProfit, _close, _hband, _hbandPrev) => Boolean(_crossUnder || (_exhaustion && _inProfit && (_close < _hband || _close < _hbandPrev))));

// --- Visuals ---
const myFilterColor = for_every(myGaussianGreen, (_green) => _green ? '#39FF14' : '#FF3B30');
const myFiltLinePainted = paint(myFiltN, { name: 'Gaussian Filter', color: myFilterColor, thickness: 3 });
const myHBandLinePainted = paint(myHBand, { name: 'High Band', color: '#808080' });
fill(myFiltLinePainted, myHBandLinePainted, 'gray', 0.1);

const myExhaustionMarks = for_every(mySlopeExhaustion, myInProfitProxy, high, (_exh, _profit, _high) => (_exh && _profit) ? _high : null);
paint(myExhaustionMarks, { name: 'Exhaustion Detected', style: 'labels_above', color: 'orange' });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(myLongCondition, 'Long Entry');
register_signal(myExitCondition, 'Exit Signal');