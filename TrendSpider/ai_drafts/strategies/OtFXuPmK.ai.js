describe_indicator('EMA Crossover with Regime Filter', 'price');

// Date range inputs
const dateTab = input.tab('Backtest Period');
const dateRow1 = dateTab.row();
const myStartYear = dateRow1.number('Start Year', 2020, { min: 1970, max: 2100 });
const myStartMonth = dateRow1.number('Start Month', 1, { min: 1, max: 12 });
const myStartDay = dateRow1.number('Start Day', 1, { min: 1, max: 31 });
const dateRow2 = dateTab.row();
const myEndYear = dateRow2.number('End Year', 2030, { min: 1970, max: 2100 });
const myEndMonth = dateRow2.number('End Month', 12, { min: 1, max: 12 });
const myEndDay = dateRow2.number('End Day', 31, { min: 1, max: 31 });

// Strategy parameters
const stratTab = input.tab('Strategy Parameters');
const myFastLen = stratTab.number('Fast EMA', 9, { min: 1, max: 500 });
const mySlowLen = stratTab.number('Slow EMA', 21, { min: 1, max: 500 });
const myRegimeLen = stratTab.number('Regime EMA', 200, { min: 1, max: 1000 });

// Compute EMAs
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);
const myRegimeEMA = ema(close, myRegimeLen);

// Build start/end unix timestamps (assumes UTC midnight boundaries, since
// Pine's timestamp() uses exchange timezone which is not reproducible exactly
// without the exchange timezone offset logic here)
const myStartTimestamp = Date.UTC(myStartYear, myStartMonth - 1, myStartDay, 0, 0, 0) / 1000;
const myEndTimestamp = Date.UTC(myEndYear, myEndMonth - 1, myEndDay, 23, 59, 0) / 1000;

// In-date-range flag per candle
const myInDateRange = for_every(time, _t => _t >= myStartTimestamp && _t <= myEndTimestamp);

// Crossover / crossunder detection (equivalent of ta.crossover / ta.crossunder)
const myLongCondRaw = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevFast = myFastEMA[_i - 1];
	const myPrevSlow = mySlowEMA[_i - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myShortCondRaw = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevFast = myFastEMA[_i - 1];
	const myPrevSlow = mySlowEMA[_i - 1];
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

// Apply regime filter and date range filter
const myLongCond = for_every(myLongCondRaw, close, myRegimeEMA, myInDateRange, (_cond, _c, _regime, _inRange) => _cond && _c > _regime && _inRange);
const myShortCond = for_every(myShortCondRaw, close, myRegimeEMA, myInDateRange, (_cond, _c, _regime, _inRange) => _cond && _c < _regime && _inRange);

// Register signals so they can be used in scanners, alerts and strategy tester.
// Note: register_signal and paint output names share the same namespace, so
// these signal names must differ from the paint() names used below for the
// visual markers (previously both used "Long Entry" / "Short Entry", causing
// a duplicate output series error).
register_signal(myLongCond, 'Long Entry Signal');
register_signal(myShortCond, 'Short Entry Signal');

// Visual markers for entries
const myLongMarks = for_every(myLongCond, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCond, high, (_cond, _high) => _cond ? _high : null);

// Plot EMAs
paint(myFastEMA, { name: 'Fast EMA', color: '#2962FF', thickness: 1 });
paint(mySlowEMA, { name: 'Slow EMA', color: '#FF9800', thickness: 1 });
paint(myRegimeEMA, { name: 'Regime EMA', color: '#E0E0E0', thickness: 2 });

// Plot entry markers
paint(myLongMarks, { name: 'Long Entry Marker', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'Short Entry Marker', style: 'labels_above', color: '#EF5350', thickness: 3 });