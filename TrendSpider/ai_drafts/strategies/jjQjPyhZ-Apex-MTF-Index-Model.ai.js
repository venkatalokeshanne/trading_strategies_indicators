describe_indicator('Apex MTF Index Model', 'price');

// ===================== INPUTS =====================
const myTab = input.tab('Settings');

const myEmaLenRow = myTab.row();
const myLenEMA = myEmaLenRow.number('EMA Length', 21, { min: 1, max: 500 });
const myAtrLen = myEmaLenRow.number('ATR Length', 14, { min: 1, max: 500 });

const myRRRow = myTab.row();
const myRR = myRRRow.number('Runner RR', 2.5, { min: 0.1, max: 20 });
const myOrbMinutes = myRRRow.number('Opening Range Minutes', 15, { min: 1, max: 240 });

const mySessionGroup = myTab.group('Session');
const mySessionText = mySessionGroup.text('NY Session (HHMM-HHMM)', '0930-1130');

// ===================== SESSION PARSING =====================
// Parses "HHMM-HHMM" into minute-of-day boundaries. Assumes current.session
// timezone already matches "NY Session" intent (exchange timezone of the symbol).
const mySessionParts = mySessionText.split('-');
const mySessionStartMin = parseInt(mySessionParts[0].slice(0, 2), 10) * 60 + parseInt(mySessionParts[0].slice(2, 4), 10);
const mySessionEndMin = parseInt(mySessionParts[1].slice(0, 2), 10) * 60 + parseInt(mySessionParts[1].slice(2, 4), 10);

const myTimeInfo = time.map(_t => time_of(_t));
const myInSession = myTimeInfo.map(_ti => {
	const myMinuteOfDay = _ti.hours * 60 + _ti.minutes;
	return myMinuteOfDay >= mySessionStartMin && myMinuteOfDay <= mySessionEndMin;
});

// ===================== HIGHER TIMEFRAME BIAS =====================
const [myMonthlyData, myWeeklyData, myDailyData] = await Promise.all([
	request.history(current.ticker, 'M'),
	request.history(current.ticker, 'W'),
	request.history(current.ticker, 'D')
]);

assert(!myMonthlyData.error, `Error fetching Monthly data: ${myMonthlyData.error}`);
assert(!myWeeklyData.error, `Error fetching Weekly data: ${myWeeklyData.error}`);
assert(!myDailyData.error, `Error fetching Daily data: ${myDailyData.error}`);

function myBiasSeries(_htfData) {
	const myHtfEma = ema(_htfData.close, myLenEMA);
	const myHtfBias = for_every(_htfData.close, myHtfEma, (_c, _e) => (_c > _e ? 1 : (_c < _e ? -1 : 0)));
	const myLanded = land_points_onto_series(_htfData.time, myHtfBias, time, 'le');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myBiasM = myBiasSeries(myMonthlyData);
const myBiasW = myBiasSeries(myWeeklyData);
const myBiasD = myBiasSeries(myDailyData);

const myBias = for_every(myBiasM, myBiasW, myBiasD, (_m, _w, _d) => (_m || 0) * 5 + (_w || 0) * 4 + (_d || 0) * 3);

const myMaxBias = 12;
const myProbBull = for_every(myBias, _b => (_b + myMaxBias) / (2 * myMaxBias) * 100);

const myBullBias = for_every(myProbBull, _p => _p > 60);
const myBearBias = for_every(myProbBull, _p => _p < 40);

// ===================== EMA + VWAP (session anchored, resets daily) =====================
const myEma = ema(close, myLenEMA);

const myNewDayFlags = time.map((_t, _i) => {
	if (_i === 0) {
		return true;
	}
	const myCur = time_of(_t);
	const myPrev = time_of(time[_i - 1]);
	return myCur.dayOfYear !== myPrev.dayOfYear || myCur.year !== myPrev.year;
});

const myPV = mult(hlc3, volume);
const myCumPV = for_every(myPV, myNewDayFlags, (_pv, _isNew, _prev) => (_isNew ? _pv : _prev + _pv));
const myCumVol = for_every(volume, myNewDayFlags, (_v, _isNew, _prev) => (_isNew ? _v : _prev + _v));
const myVwap = div(myCumPV, myCumVol);

// ===================== VOLATILITY FILTER =====================
const myAtr = atr(high, low, close, myAtrLen);
const myAtrAvg = sma(myAtr, myAtrLen);
const myVolOk = for_every(myAtr, myAtrAvg, (_a, _aAvg) => _a > _aAvg);

// ===================== PREVIOUS DAY LEVELS =====================
const myPdhLanded = land_points_onto_series(myDailyData.time, shift(myDailyData.high, 1), time, 'le');
const myPdlLanded = land_points_onto_series(myDailyData.time, shift(myDailyData.low, 1), time, 'le');
const myPdh = interpolate_sparse_series(myPdhLanded, 'constant');
const myPdl = interpolate_sparse_series(myPdlLanded, 'constant');

// ===================== OPENING RANGE (ORB) =====================
const mySessionStartTime = for_every(time, myNewDayFlags, (_t, _isNew, _prev) => (_isNew ? _t : _prev));
const myInORB = for_every(time, mySessionStartTime, (_t, _s) => (_t - _s) <= myOrbMinutes * 60);

const myOrbHigh = for_every(high, myInORB, myNewDayFlags, (_h, _inO, _isNew, _prev) => {
	if (_isNew) {
		return _inO ? _h : null;
	}
	if (_inO) {
		return (_prev === null || _prev === undefined) ? _h : Math.max(_prev, _h);
	}
	return (_prev === undefined) ? null : _prev;
});

const myOrbLow = for_every(low, myInORB, myNewDayFlags, (_l, _inO, _isNew, _prev) => {
	if (_isNew) {
		return _inO ? _l : null;
	}
	if (_inO) {
		return (_prev === null || _prev === undefined) ? _l : Math.min(_prev, _l);
	}
	return (_prev === undefined) ? null : _prev;
});

// ===================== ENTRY CONDITIONS =====================
const myLongPullback = for_every(
	myBullBias, myInSession, myVolOk, close, myEma, myVwap, low,
	(_bull, _inSess, _volOk, _c, _e, _vw, _l) => _bull && _inSess && _volOk && _c > _e && _c > _vw && _l <= _e
);

const myShortPullback = for_every(
	myBearBias, myInSession, myVolOk, close, myEma, myVwap, high,
	(_bear, _inSess, _volOk, _c, _e, _vw, _h) => _bear && _inSess && _volOk && _c < _e && _c < _vw && _h >= _e
);

const myLongORB = for_every(
	myBullBias, myInSession, myVolOk, myInORB, myOrbHigh, close, myVwap,
	(_bull, _inSess, _volOk, _inO, _oh, _c, _vw) => _bull && _inSess && _volOk && !_inO && _oh !== null && _oh !== undefined && _c > _oh && _c > _vw
);

const myShortORB = for_every(
	myBearBias, myInSession, myVolOk, myInORB, myOrbLow, close, myVwap,
	(_bear, _inSess, _volOk, _inO, _ol, _c, _vw) => _bear && _inSess && _volOk && !_inO && _ol !== null && _ol !== undefined && _c < _ol && _c < _vw
);

const myLongEntry = for_every(myLongPullback, myLongORB, (_a, _b) => _a || _b);
const myShortEntry = for_every(myShortPullback, myShortORB, (_a, _b) => _a || _b);

// ===================== STOPS & TARGETS (informational only) =====================
const myLongSL = sub(low, myAtr);
const myShortSL = add(high, myAtr);
const myLongTP1 = add(close, mult(sub(close, myLongSL), 1.5));
const myLongTP2 = add(close, mult(sub(close, myLongSL), myRR));
const myShortTP1 = sub(close, mult(sub(myShortSL, close), 1.5));
const myShortTP2 = sub(close, mult(sub(myShortSL, close), myRR));

// ===================== VISUALS =====================
const myCandleColors = for_every(myBullBias, myBearBias, (_bull, _bear) => (_bull ? 'rgba(0,200,0,0.15)' : (_bear ? 'rgba(200,0,0,0.15)' : null)));
color_candles(myCandleColors);

paint(myEma, { name: 'EMA', color: '#2962FF', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#FF6D00', thickness: 2 });
paint(myPdh, { name: 'PDH', color: '#2E7D32', style: 'ladder' });
paint(myPdl, { name: 'PDL', color: '#C62828', style: 'ladder' });
paint(myOrbHigh, { name: 'ORB High', color: '#1E88E5', style: 'ladder' });
paint(myOrbLow, { name: 'ORB Low', color: '#F57C00', style: 'ladder' });

// ===================== SIGNALS (for scanners, alerts, strategy tester) =====================
register_signal(myLongPullback, 'Long Pullback');
register_signal(myShortPullback, 'Short Pullback');
register_signal(myLongORB, 'Long ORB Breakout');
register_signal(myShortORB, 'Short ORB Breakout');
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myBullBias, 'Bullish Bias');
register_signal(myBearBias, 'Bearish Bias');