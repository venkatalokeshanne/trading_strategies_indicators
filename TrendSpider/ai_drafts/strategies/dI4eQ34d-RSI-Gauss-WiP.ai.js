describe_indicator('RSI Stochastic Gaussian Channel', 'price');

// ---------- Inputs ----------
const myTabRSI = input.tab('RSI Stochastic');
const mySmoothK = myTabRSI.number('K Smoothing', 3, { min: 1, max: 50 });
const mySmoothD = myTabRSI.number('D Smoothing', 3, { min: 1, max: 50 });
const myRsiLength = myTabRSI.number('RSI Length', 14, { min: 1, max: 200 });
const myStochLength = myTabRSI.number('Stochastic Length', 14, { min: 1, max: 200 });

const myTabGauss = input.tab('Gaussian Channel');
const myPoles = myTabGauss.number('Poles', 4, { min: 1, max: 9 });
const mySamplingPeriod = myTabGauss.number('Sampling Period', 144, { min: 2, max: 2000 });
// shortened input name to satisfy the engine's input name length limit
const myMultiplier = myTabGauss.number('TR Multiplier', 1.414, { min: 0, max: 10 });
const myModeLag = myTabGauss.boolean('Reduced Lag Mode', false);
const myModeFast = myTabGauss.boolean('Fast Response Mode', false);

// ---------- RSI Stochastic (K/D) ----------
const myRsiValue = rsi(close, myRsiLength);
const myRsiHighest = highest(myRsiValue, myStochLength);
const myRsiLowest = lowest(myRsiValue, myStochLength);

// manual stochastic of rsi vs itself (close=high=low=rsi in Pine's ta.stoch call)
const myStochRaw = for_every(myRsiValue, myRsiHighest, myRsiLowest, (_rsi, _hh, _ll) => {
	const myRange = _hh - _ll;
	return myRange === 0 ? 0 : 100 * (_rsi - _ll) / myRange;
});

const myKValue = sma(myStochRaw, mySmoothK);
const myDValue = sma(myKValue, mySmoothD);

// ---------- True Range (manual, since we need raw series, not averaged) ----------
const myPrevClose = shift(close, 1);
const myTrueRange = for_every(high, low, myPrevClose, (_h, _l, _pc) => {
	if (_pc === null || _pc === undefined) {
		return _h - _l;
	}
	return Math.max(_h - _l, Math.abs(_h - _pc), Math.abs(_l - _pc));
});

// ---------- Source series ----------
const mySource = hlc3;

// Reduced lag mode uses a float lag index for a historical shift; the
// scripting engine only supports integer offsets, so the lag value is
// rounded to the nearest integer candle count (approximation of Pine's
// float-indexed series[] access).
const myLag = Math.round((mySamplingPeriod - 1) / (2 * myPoles));
const mySrcData = myModeLag
	? for_every(mySource, shift(mySource, myLag), (_s, _sLag) => _s + (_s - (_sLag === null ? _s : _sLag)))
	: mySource;
const myTrData = myModeLag
	? for_every(myTrueRange, shift(myTrueRange, myLag), (_t, _tLag) => _t + (_t - (_tLag === null ? _t : _tLag)))
	: myTrueRange;

// ---------- Generic N-pole Gaussian recursive filter (binomial expansion) ----------
function myBinomial(_n, _k) {
	let myResult = 1;
	for (let myIndex = 0; myIndex < _k; myIndex += 1) {
		myResult = myResult * (_n - myIndex) / (myIndex + 1);
	}
	return myResult;
}

function myComputeGaussianOrder(_alpha, _srcArray, _order) {
	const myLength = _srcArray.length;
	const myX = 1 - _alpha;
	// "new Array(...)" is not allowed by the scripting engine;
	// use Array(...).fill(0) instead (works identically without "new")
	const myOutput = Array(myLength).fill(0);

	for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
		let myValue = Math.pow(_alpha, _order) * _srcArray[myIndex];
		myValue += _order * myX * (myIndex - 1 >= 0 ? myOutput[myIndex - 1] : 0);

		for (let myK = 2; myK <= 9; myK += 1) {
			if (_order >= myK) {
				const mySign = (myK % 2 === 0) ? -1 : 1;
				const myCoeff = myBinomial(_order, myK);
				const myPrevIndex = myIndex - myK;
				const myPrevValue = myPrevIndex >= 0 ? myOutput[myPrevIndex] : 0;
				myValue += mySign * myCoeff * Math.pow(myX, myK) * myPrevValue;
			}
		}

		myOutput[myIndex] = myValue;
	}

	return myOutput;
}

// ---------- Alpha / Beta coefficients ----------
const myBeta = (1 - Math.cos(4 * Math.asin(1) / mySamplingPeriod)) / (Math.pow(1.414, 2 / myPoles) - 1);
const myAlpha = -myBeta + Math.sqrt(myBeta * myBeta + 2 * myBeta);

const myFiltN = myComputeGaussianOrder(myAlpha, mySrcData, myPoles);
const myFilt1 = myComputeGaussianOrder(myAlpha, mySrcData, 1);
const myFiltNTr = myComputeGaussianOrder(myAlpha, myTrData, myPoles);
const myFilt1Tr = myComputeGaussianOrder(myAlpha, myTrData, 1);

const myFilt = myModeFast
	? for_every(myFiltN, myFilt1, (_fn, _f1) => (_fn + _f1) / 2)
	: myFiltN;
const myFiltTr = myModeFast
	? for_every(myFiltNTr, myFilt1Tr, (_fn, _f1) => (_fn + _f1) / 2)
	: myFiltNTr;

const myHBand = for_every(myFilt, myFiltTr, (_f, _ftr) => _f + _ftr * myMultiplier);
const myLBand = for_every(myFilt, myFiltTr, (_f, _ftr) => _f - _ftr * myMultiplier);

// ---------- Filter direction color ----------
const myPrevFilt = shift(myFilt, 1);
const myFiltColor = for_every(myFilt, myPrevFilt, (_f, _pf) => {
	if (_pf === null || _pf === undefined) return 'gray';
	if (_f > _pf) return '#0aff68';
	if (_f < _pf) return '#ff0a5a';
	return 'gray';
});

// ---------- Candle coloring ----------
const myPrevSrc = shift(mySource, 1);
const myBarColor = for_every(mySource, myPrevSrc, myFilt, myHBand, myLBand, (_s, _ps, _f, _hb, _lb) => {
	if (_ps === null || _ps === undefined) return 'gray';
	if (_s > _ps && _s > _f && _s < _hb) return '#0aff68';
	if (_s > _ps && _s >= _hb) return '#0aff1b';
	if (_s <= _ps && _s > _f) return '#00752d';
	if (_s < _ps && _s < _f && _s > _lb) return '#ff0a5a';
	if (_s < _ps && _s <= _lb) return '#ff0a11';
	if (_s >= _ps && _s < _f) return '#990032';
	return 'gray';
});
color_candles(myBarColor);

// ---------- Paint lines ----------
const myFiltPainted = paint(myFilt, { name: 'Filter', color: '#4DA3FF', thickness: 3 });
const myHBandPainted = paint(myHBand, { name: 'HighBand', color: '#4DA3FF', forceUsePriceAxis: true });
const myLBandPainted = paint(myLBand, { name: 'LowBand', color: '#4DA3FF', forceUsePriceAxis: true });
fill(myHBandPainted, myLBandPainted, '#4DA3FF', 0.2, 'Channel Fill');

// ---------- Signals ----------
const myGaussianGreen = for_every(myFilt, myPrevFilt, (_f, _pf) => _pf !== null && _pf !== undefined && _f > _pf);
const myStochSignal = for_every(myKValue, myDValue, (_k, _d) => _k > _d);
const myLongCondition = for_every(myGaussianGreen, mySource, myHBand, myStochSignal, (_gg, _s, _hb, _ss) => _gg && _s > _hb && _ss);

const myPrevSrcForCross = shift(mySource, 1);
const myPrevHBand = shift(myHBand, 1);
const myCloseLongCondition = for_every(mySource, myHBand, myPrevSrcForCross, myPrevHBand, (_s, _hb, _ps, _phb) => {
	if (_ps === null || _ps === undefined || _phb === null || _phb === undefined) return false;
	return _ps >= _phb && _s < _hb;
});

register_signal(myLongCondition, 'Long Entry');
register_signal(myCloseLongCondition, 'Close Long');