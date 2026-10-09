describe_indicator('Smart Scalping PRO Strategy', 'price');

// ===== INPUTS =====
const tabTrend = input.tab('Trend/Momentum');
const emaFastLen = tabTrend.number('EMA Fast', 50, { min: 1, max: 500 });
const emaSlowLen = tabTrend.number('EMA Slow', 200, { min: 1, max: 500 });

const rsiRow = tabTrend.row();
const rsiLen = rsiRow.number('RSI Length', 3, { min: 1, max: 100 });
const rsiOB = rsiRow.number('RSI Overbought', 80, { min: 50, max: 99 });
const rsiOS = rsiRow.number('RSI Oversold', 20, { min: 1, max: 50 });

const adxRow = tabTrend.row();
const adxLen = adxRow.number('ADX Length', 5, { min: 1, max: 100 });
const adxLevel = adxRow.number('ADX Threshold', 30, { min: 1, max: 100 });

const tabRisk = input.tab('Risk/Session');
const atrRow = tabRisk.row();
const atrLen = atrRow.number('ATR Length', 14, { min: 1, max: 100 });
const atrMult = atrRow.number('ATR Multiplier', 1.2, { min: 0.1, max: 10, step: 0.1 });
const rr = tabRisk.number('Risk Reward', 1.5, { min: 0.1, max: 10, step: 0.1 });

const sessionRow = tabRisk.row();
// Session strings in "HHMM-HHMM" format, evaluated against exchange local time
// (approximation of Pine's time(timeframe, session) with chart timezone).
const londonSession = sessionRow.text('London Session', '0800-1200');
const newYorkSession = sessionRow.text('New York Session', '1300-1700');

// ===== INDICATORS =====
const myEma50 = ema(close, emaFastLen);
const myEma200 = ema(close, emaSlowLen);
const myRsi = rsi(close, rsiLen);
const myAdxObject = indicators.adx(adxLen);
const myAtr = atr(high, low, close, atrLen);
const myAtrSma = sma(myAtr, 20);

// trend slope: ema50 - ema50[5]
const myEmaSlope = sub(myEma50, shift(myEma50, 5));

// volatility filter
const myVolatilityOk = for_every(myAtr, myAtrSma, (_atrVal, _atrSmaVal) => _atrVal > _atrSmaVal);

// ===== SESSION PARSING (approximation using exchange local time) =====
function parseSession(_sessionString) {
	const myParts = _sessionString.split('-');
	const myFromH = parseInt(myParts[0].slice(0, 2), 10);
	const myFromM = parseInt(myParts[0].slice(2, 4), 10);
	const myToH = parseInt(myParts[1].slice(0, 2), 10);
	const myToM = parseInt(myParts[1].slice(2, 4), 10);
	return { fromMinutes: myFromH * 60 + myFromM, toMinutes: myToH * 60 + myToM };
}

const myLondonRange = parseSession(londonSession);
const myNYRange = parseSession(newYorkSession);

const mySessionOk = time.map(_t => {
	const myTimeInfo = time_of(_t);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;

	const myInLondon = myMinutesOfDay >= myLondonRange.fromMinutes && myMinutesOfDay < myLondonRange.toMinutes;
	const myInNY = myMinutesOfDay >= myNYRange.fromMinutes && myMinutesOfDay < myNYRange.toMinutes;

	return myInLondon || myInNY;
});

// ===== TREND FILTER =====
const myTrendLong = for_every(close, myEma50, myEma200, myEmaSlope, (_c, _e50, _e200, _slope) =>
	_c > _e50 && _e50 > _e200 && _slope > 0
);

const myTrendShort = for_every(close, myEma50, myEma200, myEmaSlope, (_c, _e50, _e200, _slope) =>
	_c < _e50 && _e50 < _e200 && _slope < 0
);

// ===== MOMENTUM: crossover / crossunder =====
const myRsiShifted = shift(myRsi, 1);

const myRsiLong = for_every(myRsi, myRsiShifted, (_cur, _prev) => _prev <= rsiOS && _cur > rsiOS);
const myRsiShort = for_every(myRsi, myRsiShifted, (_cur, _prev) => _prev >= rsiOB && _cur < rsiOB);

// ===== STRENGTH =====
const myStrongTrend = for_every(myAdxObject.adx, _adxVal => _adxVal > adxLevel);

// ===== FINAL CONDITIONS =====
const myLongCondition = for_every(
	myTrendLong, myRsiLong, myStrongTrend, mySessionOk, myVolatilityOk,
	(_tl, _rl, _st, _so, _vo) => _tl && _rl && _st && _so && _vo
);

const myShortCondition = for_every(
	myTrendShort, myRsiShort, myStrongTrend, mySessionOk, myVolatilityOk,
	(_ts, _rs, _st, _so, _vo) => _ts && _rs && _st && _so && _vo
);

// ===== STOP / TARGET LEVELS (informational, not executed as trades) =====
const myLongStop = sub(close, mult(myAtr, atrMult));
const myShortStop = add(close, mult(myAtr, atrMult));
const myLongTarget = add(close, mult(sub(close, myLongStop), rr));
const myShortTarget = sub(close, mult(sub(myShortStop, close), rr));

// ===== PLOTS =====
paint(myEma50, { name: 'EMA Fast', color: 'orange', thickness: 2 });
paint(myEma200, { name: 'EMA Slow', color: 'blue', thickness: 2 });

const myBuyMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const mySellMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// Levels (hidden from main view by default style, shown on price axis for reference)
paint(myLongStop, { name: 'Long Stop', color: 'silver', style: 'dotted', forceUsePriceAxis: true });
paint(myLongTarget, { name: 'Long Target', color: 'silver', style: 'dotted', forceUsePriceAxis: true });
paint(myShortStop, { name: 'Short Stop', color: 'gray', style: 'dotted', forceUsePriceAxis: true });
paint(myShortTarget, { name: 'Short Target', color: 'gray', style: 'dotted', forceUsePriceAxis: true });

// ===== SIGNALS (for scanners/alerts/backtests) =====
register_signal(myLongCondition, 'Buy Signal');
register_signal(myShortCondition, 'Sell Signal');