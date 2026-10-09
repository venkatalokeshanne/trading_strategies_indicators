describe_indicator('UT Bot Options Seller (5 Min Spike Protected)', 'price');

// ==========================================
// INPUTS
// ==========================================
const utTab = input.tab('UT Bot');
const myUtKey = utTab.number('UT Bot Key Value', 2.0, { min: 0.1, max: 20 });
const myUtAtrPeriod = utTab.number('UT Bot ATR Period', 10, { min: 1, max: 100 });

const rsiAdxTab = input.tab('RSI and ADX');
const myRsiPeriod = rsiAdxTab.number('RSI Period', 14, { min: 1, max: 100 });
const peRow = rsiAdxTab.row();
const myRsiPeMin = peRow.number('PE Sell Min RSI', 3, { min: 0, max: 100 });
const myRsiPeMax = peRow.number('PE Sell Max RSI', 60, { min: 0, max: 100 });
const ceRow = rsiAdxTab.row();
const myRsiCeMin = ceRow.number('CE Sell Min RSI', 40, { min: 0, max: 100 });
const myRsiCeMax = ceRow.number('CE Sell Max RSI', 100, { min: 0, max: 100 });
const myAdxPeriod = rsiAdxTab.number('ADX Period', 14, { min: 1, max: 100 });
const myAdxThreshold = rsiAdxTab.number('Minimum ADX', 20.0, { min: 0, max: 100 });

const spikeTab = input.tab('Spike Filter');
const mySpikeMultiplier = spikeTab.number('Max Candle Spike Multiplier', 2.0, { min: 0.1, max: 20 });

const timeTab = input.tab('Trade Window');
const myStartHour = timeTab.number('Start Hour (exchange tz)', 9, { min: 0, max: 23 });
const myStartMinute = timeTab.number('Start Minute', 15, { min: 0, max: 59 });
const myEndHour = timeTab.number('End Hour (exchange tz)', 15, { min: 0, max: 23 });
const myEndMinute = timeTab.number('End Minute', 0, { min: 0, max: 59 });

// ==========================================
// UT BOT TRAILING STOP (recursive, matches Pine logic exactly)
// ==========================================
const myAtr = atr(high, low, close, myUtAtrPeriod);
const myNLoss = mult(myAtr, myUtKey);
const myPrevClose = shift(close, 1);

// Recursive trailing stop. prevValue (3rd-to-last callback arg) holds
// the previous candle's trailing stop value, mirroring Pine's "var float"
// persistent variable behavior.
const myTrailingStop = for_every(close, myPrevClose, myNLoss, (_c, _pc, _nl, _prev) => {
	const myPrevStop = _prev || 0;
	if (_c > myPrevStop && _pc > myPrevStop) {
		return Math.max(myPrevStop, _c - _nl);
	}
	else if (_c < myPrevStop && _pc < myPrevStop) {
		return Math.min(myPrevStop, _c + _nl);
	}
	else if (_c > myPrevStop) {
		return _c - _nl;
	}
	else {
		return _c + _nl;
	}
});

const myPrevTrailingStop = shift(myTrailingStop, 1);

// crossover / crossunder, matching ta.crossover / ta.crossunder
const myBuySignal = for_every(close, myTrailingStop, myPrevClose, myPrevTrailingStop,
	(_c, _ts, _pc, _pts) => _c > _ts && _pc <= _pts
);
const mySellSignal = for_every(close, myTrailingStop, myPrevClose, myPrevTrailingStop,
	(_c, _ts, _pc, _pts) => _c < _ts && _pc >= _pts
);

// ==========================================
// RSI AND ADX
// ==========================================
const myRsiValue = rsi(close, myRsiPeriod);
const myAdxObject = indicators.adx(myAdxPeriod);
const myAdxValue = myAdxObject.adx;

// ==========================================
// SPIKE FILTER
// ==========================================
const myCurrentCandleSize = sub(high, low);
const myAverageCandleSize = atr(high, low, close, 14);
const myIsNotASpike = for_every(myCurrentCandleSize, myAverageCandleSize,
	(_size, _avg) => _size <= (_avg * mySpikeMultiplier)
);

// ==========================================
// TIME WINDOW FILTER
// NOTE: Pine's time() with "Asia/Kolkata" forces the Kolkata session
// regardless of the exchange the chart is on. The Custom JS API's
// time_of() always uses the current symbol's EXCHANGE time zone and
// cannot be forced to an arbitrary zone. This is only an exact match
// of the Pine logic if the current symbol's exchange time zone is
// Asia/Kolkata (i.e. Indian instruments). For other exchanges this is
// an approximation using the exchange's own local time instead.
// ==========================================
const myInTradeWindow = time.map(_t => {
	const myTimeInfo = time_of(_t);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myStartMinutes = myStartHour * 60 + myStartMinute;
	const myEndMinutes = myEndHour * 60 + myEndMinute;
	const myIsWeekday = myTimeInfo.dayOfWeek >= 1 && myTimeInfo.dayOfWeek <= 7;
	return myIsWeekday && myMinutesOfDay >= myStartMinutes && myMinutesOfDay <= myEndMinutes;
});

// ==========================================
// ENTRY CONDITIONS
// ==========================================
const myEnterPeSell = for_every(myBuySignal, myRsiValue, myAdxValue, myIsNotASpike, myInTradeWindow,
	(_buy, _rsi, _adx, _notSpike, _inWindow) =>
		_buy && (_rsi >= myRsiPeMin && _rsi <= myRsiPeMax) && _adx > myAdxThreshold && _notSpike && _inWindow
);

const myEnterCeSell = for_every(mySellSignal, myRsiValue, myAdxValue, myIsNotASpike, myInTradeWindow,
	(_sell, _rsi, _adx, _notSpike, _inWindow) =>
		_sell && (_rsi >= myRsiCeMin && _rsi <= myRsiCeMax) && _adx > myAdxThreshold && _notSpike && _inWindow
);

// ==========================================
// SIGNALS (for Scanner, Alerts, Strategy Tester)
// ==========================================
register_signal(myEnterPeSell, 'Enter PE Sell');
register_signal(myEnterCeSell, 'Enter CE Sell');
register_signal(myInTradeWindow, 'In Trade Window');

// ==========================================
// PAINT
// ==========================================
const myStopColor = for_every(close, myTrailingStop, (_c, _ts) => _c > _ts ? 'green' : 'red');
paint(myTrailingStop, { name: 'UT Bot Stop', color: myStopColor, thickness: 2, style: 'line', forceUsePriceAxis: true });