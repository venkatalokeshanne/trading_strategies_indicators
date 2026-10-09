describe_indicator('Gold Pro EMA Cross Strategy', 'price');

// NOTE: TrendSpider Custom JS API has no strategy.entry/exit or
// backtesting engine. This script reproduces the Pine Script's
// EMA cross LOGIC and SIGNALS (long/short, TP/SL levels), but
// actual trade simulation (equity, position sizing) is not
// available here. See errors_and_warnings_flagged for details.

const myEmaFastLen = input.number('EMA Fast Length', 9, { min: 1, max: 500 });
const myEmaSlowLen = input.number('EMA Slow Length', 21, { min: 1, max: 500 });

// Pine "points" are expressed in ticks (minimum price increment).
// We assume a tick size of 0.01 (common for Gold/XAUUSD CFDs),
// so tpPoints/slPoints are converted to price distance by *0.01.
// If your instrument's tick size differs, adjust these inputs.
const myTickSize = input.number('Tick Size', 0.01, { min: 0.0000001, max: 10 });
const myTpPoints = input.number('Take Profit Points', 10000, { min: 1, max: 1000000 });
const mySlPoints = input.number('Stop Loss Points', 5000, { min: 1, max: 1000000 });

const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);

// crossover / crossunder detection, same semantics as ta.crossover/crossunder
const myLongCondition = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return myEmaFast[_index - 1] <= myEmaSlow[_index - 1] && _fast > _slow;
});

const myShortCondition = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return myEmaFast[_index - 1] >= myEmaSlow[_index - 1] && _fast < _slow;
});

const myTpDistance = myTpPoints * myTickSize;
const mySlDistance = mySlPoints * myTickSize;

// Compute TP/SL target levels for reference, anchored at the signal bar's close
const myLongTp = for_every(close, myLongCondition, (_c, _long) => _long ? _c + myTpDistance : null);
const myLongSl = for_every(close, myLongCondition, (_c, _long) => _long ? _c - mySlDistance : null);
const myShortTp = for_every(close, myShortCondition, (_c, _short) => _short ? _c - myTpDistance : null);
const myShortSl = for_every(close, myShortCondition, (_c, _short) => _short ? _c + mySlDistance : null);

paint(myEmaFast, { name: 'EmaFast', color: '#2962FF', thickness: 2 });
paint(myEmaSlow, { name: 'EmaSlow', color: '#FF9800', thickness: 2 });

paint(myLongTp, { name: 'LongTakeProfit', style: 'labels_above', color: '#26A69A' });
paint(myLongSl, { name: 'LongStopLoss', style: 'labels_below', color: '#EF5350' });
paint(myShortTp, { name: 'ShortTakeProfit', style: 'labels_below', color: '#26A69A' });
paint(myShortSl, { name: 'ShortStopLoss', style: 'labels_above', color: '#EF5350' });

// Approximate the Pine bgcolor() highlight by coloring the candles
// on the signal bars (green for long signal, red for short signal).
const myCandleColors = for_every(myLongCondition, myShortCondition, (_long, _short) => {
	if (_long) return 'rgba(0,255,0,0.5)';
	if (_short) return 'rgba(255,0,0,0.5)';
	return null;
});
color_candles(myCandleColors);

// Signals for scanners, alerts and strategy tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');