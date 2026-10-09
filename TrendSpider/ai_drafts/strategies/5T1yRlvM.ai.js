describe_indicator('PRO Scalping EMA50 RSI3 ADX5', 'price');

// ===== INPUTS =====
const emaTab = input.tab('Core Settings');
const emaLength = emaTab.number('EMA Length', 50, { min: 1, max: 500 });
const rsiLength = emaTab.number('RSI Length', 3, { min: 1, max: 100 });

const rsiRow = emaTab.row();
const rsiOverbought = rsiRow.number('RSI Overbought', 80, { min: 1, max: 100 });
const rsiOversold = rsiRow.number('RSI Oversold', 20, { min: 1, max: 100 });

const adxRow = emaTab.row();
const myAdxLength = adxRow.number('ADX Length', 5, { min: 1, max: 100 });
const myAdxThreshold = adxRow.number('ADX Strength', 30, { min: 1, max: 100 });

const myRiskReward = emaTab.number('Risk Reward', 1.5, { min: 0.1, max: 10, step: 0.1 });

const sessionTab = input.tab('Sessions');
// Pine's input.session() has no direct equivalent in the Custom JS API.
// We approximate using "HHMM-HHMM" text inputs, parsed and compared against
// the exchange local time of each candle (via time_of()).
const mySessionLondon = sessionTab.text('London Session', '0800-1200');
const mySessionNY = sessionTab.text('New York Session', '1300-1700');

// ===== HELPERS =====
function myParseSession(_sessionStr) {
	const myParts = _sessionStr.split('-');
	const myFrom = parseInt(myParts[0], 10);
	const myTo = parseInt(myParts[1], 10);
	return {
		fromH: Math.floor(myFrom / 100), fromM: myFrom % 100,
		toH: Math.floor(myTo / 100), toM: myTo % 100
	};
}

const myLondonRange = myParseSession(mySessionLondon);
const myNYRange = myParseSession(mySessionNY);

function myIsInSession(_hours, _minutes, _range) {
	const myCurrentMinutes = _hours * 60 + _minutes;
	const myFromMinutes = _range.fromH * 60 + _range.fromM;
	const myToMinutes = _range.toH * 60 + _range.toM;
	return myCurrentMinutes >= myFromMinutes && myCurrentMinutes < myToMinutes;
}

// ===== INDICATORS =====
const myEma50 = ema(close, emaLength);
const myRsi = rsi(close, rsiLength);
const myAdxObject = indicators.adx(myAdxLength);
const myAdx = myAdxObject.adx;

// EMA slope (vs 5 candles ago)
const myEmaSlope = sub(myEma50, shift(myEma50, 5));

// candle strength
const myCandleBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myCandleRange = sub(high, low);
const myStrongCandle = for_every(myCandleBody, myCandleRange, (_b, _r) => _b > _r * 0.6);

// session filter, computed per-candle using exchange local time
const mySessionFilter = for_every(time, (_t) => {
	const myTimeInfo = time_of(_t);
	const myInLondon = myIsInSession(myTimeInfo.hours, myTimeInfo.minutes, myLondonRange);
	const myInNY = myIsInSession(myTimeInfo.hours, myTimeInfo.minutes, myNYRange);
	return myInLondon || myInNY;
});

// trend conditions
const myTrendLong = for_every(close, myEma50, myEmaSlope, (_c, _e, _s) => _c > _e && _s > 0);
const myTrendShort = for_every(close, myEma50, myEmaSlope, (_c, _e, _s) => _c < _e && _s < 0);

// momentum: crossover/crossunder of RSI vs thresholds
const myRsiLong = for_every(myRsi, (_r, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevRsi = myRsi[_i - 1];
	return myPrevRsi <= rsiOversold && _r > rsiOversold;
});

const myRsiShort = for_every(myRsi, (_r, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevRsi = myRsi[_i - 1];
	return myPrevRsi >= rsiOverbought && _r < rsiOverbought;
});

// volatility
const myStrongTrend = for_every(myAdx, (_a) => _a > myAdxThreshold);

// final conditions
const myLongCondition = for_every(
	myTrendLong, myRsiLong, myStrongTrend, myStrongCandle, mySessionFilter,
	(_tl, _rl, _st, _sc, _sf) => _tl && _rl && _st && _sc && _sf
);

const myShortCondition = for_every(
	myTrendShort, myRsiShort, myStrongTrend, myStrongCandle, mySessionFilter,
	(_ts, _rs, _st, _sc, _sf) => _ts && _rs && _st && _sc && _sf
);

// ===== PLOTS =====
paint(myEma50, { name: 'EMA50', color: 'orange', thickness: 2 });

const myBuyLabels = for_every(myLongCondition, (_cond) => _cond ? constants.icons.arrow_up : null);
const mySellLabels = for_every(myShortCondition, (_cond) => _cond ? constants.icons.arrow_down : null);

paint(myBuyLabels, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellLabels, { name: 'Sell', style: 'labels_above', color: 'red' });

// ===== SIGNALS FOR SCANNER STRATEGY TESTER =====
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');