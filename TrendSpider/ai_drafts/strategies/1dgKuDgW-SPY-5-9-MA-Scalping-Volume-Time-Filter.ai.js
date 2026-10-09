describe_indicator('SPY 5/9 MA Scalping Volume Time Filter', 'price');

// NOTE: TrendSpider Custom JS does not support actual strategy
// order management (position sizing, limit/stop exits, equity).
// This indicator reproduces the Pine Script signal logic
// (MA crossover + volume + time filter) and exposes Long/Short
// entry signals for scanners, alerts and backtests. Take Profit
// and Stop Loss distances are exposed as inputs but are not
// executed as actual orders - they are provided for reference
// only, since there is no strategy engine available here.

const myFastLen = input.number('Fast MA Length', 5, { min: 1, max: 200 });
const mySlowLen = input.number('Slow MA Length', 9, { min: 1, max: 200 });
const myTakeProfitDollars = input.number('Take Profit (dollar move)', 0.40, { min: 0, max: 1000 });
const myStopLossDollars = input.number('Stop Loss (dollar move)', 0.50, { min: 0, max: 1000 });

const myStartHour = input.number('Session Start Hour', 9, { min: 0, max: 23 });
const myStartMinute = input.number('Session Start Minute', 32, { min: 0, max: 59 });
const myEndHour = input.number('Session End Hour', 11, { min: 0, max: 23 });
const myEndMinute = input.number('Session End Minute', 12, { min: 0, max: 59 });

const myFastMA = sma(close, myFastLen);
const mySlowMA = sma(close, mySlowLen);

// Volume condition: current volume greater than previous candle volume
const myPrevVolume = shift(volume, 1);
const myVolumeCondition = for_every(volume, myPrevVolume, (_v, _pv) => _v > _pv);

// Time filter, based on exchange time zone of the current symbol
const myMinutesOfDay = time.map(_t => {
	const myParsed = time_of(_t);
	return myParsed.hours * 60 + myParsed.minutes;
});
const myStartMinutesOfDay = myStartHour * 60 + myStartMinute;
const myEndMinutesOfDay = myEndHour * 60 + myEndMinute;
const myTimeCondition = myMinutesOfDay.map(_m => _m >= myStartMinutesOfDay && _m <= myEndMinutesOfDay);

// Crossover / crossunder of fast MA vs slow MA
const myPrevFastMA = shift(myFastMA, 1);
const myPrevSlowMA = shift(mySlowMA, 1);

const myCrossover = for_every(
	myFastMA, mySlowMA, myPrevFastMA, myPrevSlowMA,
	(_f, _s, _pf, _ps) => _f > _s && _pf <= _ps
);

const myCrossunder = for_every(
	myFastMA, mySlowMA, myPrevFastMA, myPrevSlowMA,
	(_f, _s, _pf, _ps) => _f < _s && _pf >= _ps
);

const myLongCondition = for_every(
	myCrossover, myVolumeCondition, myTimeCondition,
	(_co, _vol, _tf) => _co && _vol && _tf
);

const myShortCondition = for_every(
	myCrossunder, myVolumeCondition, myTimeCondition,
	(_cu, _vol, _tf) => _cu && _vol && _tf
);

paint(myFastMA, { name: 'Fast MA', color: '#2ecc71', thickness: 2 });
paint(mySlowMA, { name: 'Slow MA', color: '#e74c3c', thickness: 2 });

const myLongMarks = for_every(myLongCondition, close, (_c, _close) => _c ? _close : null);
const myShortMarks = for_every(myShortCondition, close, (_c, _close) => _c ? _close : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: '#2ecc71', thickness: 3 });
paint(myShortMarks, { name: 'Short Entry', style: 'labels_above', color: '#e74c3c', thickness: 3 });

register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');