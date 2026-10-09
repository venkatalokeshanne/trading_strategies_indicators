describe_indicator('NQ BTC Gold Multi TF Signal Bot v2', 'price');

// This Custom JS API does not support strategy backtesting
// (strategy.entry, strategy.exit, stop/limit orders) or webhook
// alerts with custom JSON payloads. This script reproduces the
// EMA/RSI/HTF trend signal logic exactly, paints the EMAs, and
// exposes Long and Short conditions via register_signal so they
// can be used in Scanners, Alerts and the Strategy Tester.

const myTab = input.tab('Settings');

const myEmaGroup = myTab.group('EMAs');
const myEmaRow = myEmaGroup.row();
const myFastLen = myEmaRow.number('Fast EMA', 9, { min: 1, max: 500 });
const mySlowLen = myEmaRow.number('Slow EMA', 21, { min: 1, max: 500 });

const myRsiGroup = myTab.group('RSI');
const myRsiRow = myRsiGroup.row();
const myRsiLen = myRsiRow.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOB = myRsiRow.number('RSI Overbought', 70, { min: 1, max: 100 });
const myRsiOS = myRsiRow.number('RSI Oversold', 30, { min: 0, max: 99 });

const myHtfGroup = myTab.group('Higher Timeframe');
const myHtfTf = myHtfGroup.select('Higher TF', '60', constants.time_frames);

// Current timeframe indicators
const myFastEma = ema(close, myFastLen);
const mySlowEma = ema(close, mySlowLen);
const myRsiVal = rsi(close, myRsiLen);

// Higher timeframe data, used to compute HTF EMA trend
const myHtfData = await request.history(current.ticker, myHtfTf);
assert(!myHtfData.error, "Error fetching higher timeframe data: " + myHtfData.error);

const myHtfFastEma = ema(myHtfData.close, myFastLen);
const myHtfSlowEma = ema(myHtfData.close, mySlowLen);
const myHtfTrendUpRaw = for_every(myHtfFastEma, myHtfSlowEma, (_f, _s) => _f > _s);

// Land the HTF trend flag onto the current chart's candles
const myHtfTrendLanded = land_points_onto_series(myHtfData.time, myHtfTrendUpRaw, time, 'le');
const myHtfTrendUp = interpolate_sparse_series(myHtfTrendLanded, 'constant');

// Crossover / crossunder of fast and slow EMA (current timeframe)
const myCrossUp = for_every(myFastEma, mySlowEma, (_f, _s, _p, _i) => {
	if (_i === 0) return false;
	return _f > _s && myFastEma[_i - 1] <= mySlowEma[_i - 1];
});

const myCrossDown = for_every(myFastEma, mySlowEma, (_f, _s, _p, _i) => {
	if (_i === 0) return false;
	return _f < _s && myFastEma[_i - 1] >= mySlowEma[_i - 1];
});

// Long/Short conditions, mirroring the Pine script logic exactly
const myLongCondition = for_every(myCrossUp, myRsiVal, myHtfTrendUp, (_c, _r, _t) => _c && _r < myRsiOB && _t);
const myShortCondition = for_every(myCrossDown, myRsiVal, (_c, _r) => _c && _r > myRsiOS);

paint(myFastEma, { name: 'Fast EMA', color: '#2962FF', thickness: 2 });
paint(mySlowEma, { name: 'Slow EMA', color: '#FF6D00', thickness: 2 });

paint(for_every(myLongCondition, _l => _l ? low[close.length - 1] : null), { name: 'Long Signal', style: 'labels_below', color: '#26A69A' });
paint(for_every(myShortCondition, _s => _s ? high[close.length - 1] : null), { name: 'Short Signal', style: 'labels_above', color: '#EF5350' });

register_signal(myLongCondition, "Long Entry");
register_signal(myShortCondition, "Short Entry");