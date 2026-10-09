describe_indicator('WMA plus RSI Trailing Scalp', 'price');

// Date filter inputs (as Unix timestamps, seconds)
const myDateTab = input.tab('Date Filter');
const myStartDateStr = myDateTab.text('Start Date (YYYY-MM-DD)', '2020-01-01');
const myEndDateStr = myDateTab.text('End Date (YYYY-MM-DD)', '2030-12-31');

// renamed from "Inputs" because that tab name is reserved by the platform
const mySettingsTab = input.tab('Settings');
const myFastLen = mySettingsTab.number('Fast WMA', 9, { min: 1, max: 500 });
const mySlowLen = mySettingsTab.number('Slow WMA', 21, { min: 1, max: 500 });
const myRsiLen = mySettingsTab.number('RSI Period', 14, { min: 1, max: 500 });
const myTrailPercRow = mySettingsTab.row();
const myTrailPerc = myTrailPercRow.number('Trailing Stop percent', 1.5, { min: 0, max: 100, step: 0.1 });

// convert date strings to unix seconds (midnight UTC approximation)
const myStartTimestamp = Date.parse(myStartDateStr + 'T00:00:00Z') / 1000;
const myEndTimestamp = Date.parse(myEndDateStr + 'T23:59:59Z') / 1000;
assert(!isNaN(myStartTimestamp), 'Invalid start date');
assert(!isNaN(myEndTimestamp), 'Invalid end date');

const myFastWMA = wma(close, myFastLen);
const mySlowWMA = wma(close, mySlowLen);
const myRsiVal = rsi(close, myRsiLen);

// crossover / crossunder of fast vs slow WMA
const myFastPrev = shift(myFastWMA, 1);
const mySlowPrev = shift(mySlowWMA, 1);

const myCrossover = for_every(myFastWMA, mySlowWMA, myFastPrev, mySlowPrev, (_fast, _slow, _fastPrev, _slowPrev) => {
	return _fastPrev <= _slowPrev && _fast > _slow;
});

const myCrossunder = for_every(myFastWMA, mySlowWMA, myFastPrev, mySlowPrev, (_fast, _slow, _fastPrev, _slowPrev) => {
	return _fastPrev >= _slowPrev && _fast < _slow;
});

// in date range flag per candle
const myInRange = for_every(time, _t => _t >= myStartTimestamp && _t <= myEndTimestamp);

// long/short conditions, exactly mirroring Pine logic
const myLongCondition = for_every(myCrossover, close, myFastWMA, mySlowWMA, myRsiVal, myInRange,
	(_cross, _close, _fast, _slow, _rsi, _inRange) => {
		return !!(_inRange && _cross && _close > _fast && _close > _slow && _rsi > 50);
	});

const myShortCondition = for_every(myCrossunder, close, myFastWMA, mySlowWMA, myRsiVal, myInRange,
	(_cross, _close, _fast, _slow, _rsi, _inRange) => {
		return !!(_inRange && _cross && _close < _fast && _close < _slow && _rsi < 50);
	});

paint(myFastWMA, { name: 'Fast WMA', color: '#2962FF', thickness: 2 });
paint(mySlowWMA, { name: 'Slow WMA', color: '#FF9800', thickness: 2 });

const myLongMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'Short Entry', style: 'labels_above', color: '#EF5350', thickness: 3 });

register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');