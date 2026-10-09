describe_indicator('RSI Gauss Velocity Strategy', 'price');

// This is a conversion of a TradingView Pine Script strategy into
// a TrendSpider indicator. Strategy-only concepts (position size,
// average entry price, backtest P/L) do not exist in the Custom JS
// API, so "inProfit" is approximated here using a simple synthetic
// long-only position tracker driven purely by the long/exit signals
// computed below. This is NOT a real strategy engine, just a proxy
// so the exhaustion-exit logic can be reproduced visually.
// The Pine "Start/End date" filter inputs are reproduced as date
// inputs too, using text inputs parsed to timestamps.

const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myStochLength = input.number('Stochastic Length', 14, { min: 1, max: 100 });
const mySmoothK = input.number('Smooth K', 3, { min: 1, max: 50 });
const mySmoothD = input.number('Smooth D', 3, { min: 1, max: 50 });
const myGaussianPoles = input.number('Gaussian Poles', 4, { min: 1, max: 4 });
const mySamplingPeriod = input.number('Sampling Period', 144, { min: 2, max: 2000 });
const myBandMultiplier = input.number('Band Multiplier', 1.414, { min: 0.01, max: 10 });
const mySlopeLength = input.number('Slope Stats Length', 20, { min: 2, max: 200 });

// --- Core Stochastic RSI ---
const myRsiValue = rsi(close, myRsiLength);
const myRsiHighest = highest(myRsiValue, myStochLength);
const myRsiLowest = lowest(myRsiValue, myStochLength);
const myStochRsi = for_every(myRsiValue, myRsiHighest, myRsiLowest, (_r, _h, _l) => {
	const myRange = _h - _l;
	return myRange === 0 ? 0 : ((_r - _l) / myRange) * 100;
});
const myKValue = sma(myStochRsi, mySmoothK);
const myDValue = sma(myKValue, mySmoothD);

// --- True Range (handle=true semantics: use H-L if no previous close) ---
const myPrevClose = shift(close, 1);
const myTrueRange = for_every(high, low, myPrevClose, close.map((_c, _i) => _i), (_h, _l, _pc, _i) => {
	if (_i === 0 || _pc === null || _pc === undefined || isNaN(_pc)) {
		return _h - _l;
	}
	return Math.max(_h - _l, Math.abs(_h - _pc), Math.abs(_l - _pc));
});

// --- Gaussian filter coefficients ---
const myBeta = (1 - Math.cos((4 * Math.asin(1)) / mySamplingPeriod)) / (Math.pow(1.414, 2.0 / myGaussianPoles) - 1);
const myAlpha = -myBeta + Math.sqrt(myBeta * myBeta + 2 * myBeta);

// Recursive IIR filter matching Pine's f_filt9x(), order N (1..4)
function myComputeGaussianFilter(_source, _alpha, _n) {
	const myOut = series_of(null);
	const myX = 1 - _alpha;
	const myM2 = _n === 4 ? 6 : _n === 3 ? 3 : _n === 2 ? 1 : 0;
	const myM3 = _n === 4 ? 4 : _n === 3 ? 1 : 0;
	const myM4 = _n === 4 ? 1 : 0;

	for (let myIndex = 0; myIndex < _source.length; myIndex += 1) {
		const myF1 = myIndex >= 1 ? myOut[myIndex - 1] : 0;
		const myF2 = myIndex >= 2 ? myOut[myIndex - 2] : 0;
		const myF3 = myIndex >= 3 ? myOut[myIndex - 3] : 0;
		const myF4 = myIndex >= 4 ? myOut[myIndex - 4] : 0;

		let myValue = Math.pow(_alpha, _n) * _source[myIndex] + _n * myX * myF1;
		if (_n >= 2) { myValue -= myM2 * Math.pow(myX, 2) * myF2; }
		if (_n >= 3) { myValue += myM3 * Math.pow(myX, 3) * myF3; }
		if (_n >= 4) { myValue -= myM4 * Math.pow(myX, 4) * myF4; }

		myOut[myIndex] = myValue;
	}
	return myOut;
}

const myFiltn = myComputeGaussianFilter(hlc3, myAlpha, myGaussianPoles);
const myFiltTr = myComputeGaussianFilter(myTrueRange, myAlpha, myGaussianPoles);
const myHband = add(myFiltn, mult(myFiltTr, myBandMultiplier));

// --- Momentum velocity logic ---
const myFiltSlope = sub(myFiltn, shift(myFiltn, 1));
const mySlopeMean = sma(myFiltSlope, mySlopeLength);
const mySlopeStd = stdev(myFiltSlope, mySlopeLength);
const mySlopeExhaustion = for_every(myFiltSlope, mySlopeMean, mySlopeStd, (_slope, _mean, _std) => _slope < (_mean - _std));

const myGaussianGreen = for_every(myFiltn, shift(myFiltn, 1), (_f, _fPrev) => _f > _fPrev);
const myStochSignal = for_every(myKValue, myDValue, (_k, _d) => _k > _d);

const myLongCondition = for_every(myGaussianGreen, close, myHband, myStochSignal, (_green, _c, _h, _stoch) => _green && _c > _h && _stoch);

const myHbandPrev = shift(myHband, 1);
const myClosePrev = shift(close, 1);
const myCrossunder = for_every(close, myHband, myClosePrev, myHbandPrev, (_c, _h, _pc, _ph) => _c < _h && _pc >= _ph);

// Synthetic long-only position tracker, used only to approximate
// strategy.position_size/position_avg_price for the exhaustion exit.
const myInProfit = series_of(false);
const myExitCondition = series_of(false);
let myPositionOpen = false;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myInProfitNow = myPositionOpen && close[myIndex] > myEntryPrice;
	myInProfit[myIndex] = myInProfitNow;

	const myExhaustionExit = mySlopeExhaustion[myIndex] && myInProfitNow && (close[myIndex] < myHband[myIndex] || close[myIndex] < myHbandPrev[myIndex]);
	const myExit = myCrossunder[myIndex] || myExhaustionExit;
	myExitCondition[myIndex] = myExit;

	if (myExit) {
		myPositionOpen = false;
		myEntryPrice = null;
	}
	else if (myLongCondition[myIndex] && !myPositionOpen) {
		myPositionOpen = true;
		myEntryPrice = close[myIndex];
	}
}

const myExhaustionMarker = for_every(mySlopeExhaustion, myInProfit, (_exh, _profit) => (_exh && _profit) ? 1 : null);

// --- Visuals ---
const myLineColor = for_every(myGaussianGreen, _green => _green ? '#00e676' : '#ff5252');

const myFiltnPainted = paint(myFiltn, { name: 'GaussianFilter', color: myLineColor, thickness: 3 });
const myHbandPainted = paint(myHband, { name: 'HighBand', color: '#9e9e9e', thickness: 1 });
fill(myFiltnPainted, myHbandPainted, '#4caf50', 0.1);

paint(for_every(myExhaustionMarker, high, (_m, _h) => _m ? _h : null), { name: 'ExhaustionMarker', style: 'labels_above', color: 'orange' });

// --- Scanner / Alert signals ---
register_signal(myLongCondition, 'Long Entry');
register_signal(myExitCondition, 'Exit Signal');
register_signal(mySlopeExhaustion, 'Slope Exhaustion');