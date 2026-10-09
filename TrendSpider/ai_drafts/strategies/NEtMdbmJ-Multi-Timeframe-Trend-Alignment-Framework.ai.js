describe_indicator('Multi-Timeframe Trend Alignment Framework', 'price');

// Inputs organized in tabs
const myEmaTab = input.tab('EMA Settings');
const myHigherTF = myEmaTab.select('Higher Timeframe', '240', constants.time_frames);
const myFastLen = myEmaTab.number('Fast EMA', 20, { min: 1, max: 500 });
const mySlowLen = myEmaTab.number('Slow EMA', 50, { min: 1, max: 500 });
const myHtfLen = myEmaTab.number('Higher TF EMA', 200, { min: 1, max: 500 });

const myRiskTab = input.tab('Risk Settings');
const myAtrLen = myRiskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = myRiskTab.number('Stop ATR Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myRR = myRiskTab.number('Risk Reward', 2, { min: 0.1, max: 20, step: 0.1 });

// Current timeframe EMAs
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);

// Higher timeframe EMA, fetched via request.history and landed onto the current chart.
// This replicates request.security() with lookahead_off (no future data leaking in).
const myHtfData = await request.history(current.ticker, myHigherTF);
assert(!myHtfData.error, `Error fetching higher timeframe data: ${myHtfData.error}`);

const myHtfEmaRaw = ema(myHtfData.close, myHtfLen);
const myHtfEmaLanded = land_points_onto_series(myHtfData.time, myHtfEmaRaw, time, 'le');
const myHtfEMA = interpolate_sparse_series(myHtfEmaLanded, 'constant');

// Trend alignment
const myBullTrend = for_every(close, myHtfEMA, (_c, _h) => _c > _h);
const myBearTrend = for_every(close, myHtfEMA, (_c, _h) => _c < _h);

// Cross signals (crossover / crossunder of fast vs slow EMA)
const myBullCross = for_every(myFastEMA, mySlowEMA, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _f > _s && myFastEMA[_i - 1] <= mySlowEMA[_i - 1];
});
const myBearCross = for_every(myFastEMA, mySlowEMA, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _f < _s && myFastEMA[_i - 1] >= mySlowEMA[_i - 1];
});

// Entry conditions
const myLongCondition = for_every(myBullTrend, myBullCross, (_bt, _bc) => _bt && _bc);
const myShortCondition = for_every(myBearTrend, myBearCross, (_bt, _bc) => _bt && _bc);

// ATR for risk management reference lines
const myAtrValue = atr(high, low, close, myAtrLen);

// Reference stop/target levels computed off the close at the signal bar,
// shown as sparse series (only populated on the signal bar itself).
const myLongStop = for_every(myLongCondition, close, myAtrValue, (_cond, _c, _a) => _cond ? (_c - _a * myAtrMult) : null);
const myLongTarget = for_every(myLongCondition, close, myAtrValue, (_cond, _c, _a) => _cond ? (_c + _a * myAtrMult * myRR) : null);
const myShortStop = for_every(myShortCondition, close, myAtrValue, (_cond, _c, _a) => _cond ? (_c + _a * myAtrMult) : null);
const myShortTarget = for_every(myShortCondition, close, myAtrValue, (_cond, _c, _a) => _cond ? (_c - _a * myAtrMult * myRR) : null);

// Plot EMAs
paint(myFastEMA, { name: 'Fast EMA', color: 'orange', thickness: 1 });
paint(mySlowEMA, { name: 'Slow EMA', color: 'blue', thickness: 1 });
paint(myHtfEMA, { name: 'Higher Timeframe EMA', color: 'green', thickness: 2 });

// Entry markers
paint(for_every(myLongCondition, close, (_c, _p) => _c ? _p : null), { name: 'Long Entry', style: 'labels_below', color: 'green' });
paint(for_every(myShortCondition, close, (_c, _p) => _c ? _p : null), { name: 'Short Entry', style: 'labels_above', color: 'red' });

// Reference risk levels (sparse, shown only on signal bars)
paint(myLongStop, { name: 'Long Stop', style: 'labels_below', color: 'maroon' });
paint(myLongTarget, { name: 'Long Target', style: 'labels_above', color: 'darkgreen' });
paint(myShortStop, { name: 'Short Stop', style: 'labels_above', color: 'maroon' });
paint(myShortTarget, { name: 'Short Target', style: 'labels_below', color: 'darkgreen' });

// Signals usable in Scanners, Alerts and Strategy Tester
register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');
register_signal(myBullTrend, 'Bull Trend (Close above Higher TF EMA)');
register_signal(myBearTrend, 'Bear Trend (Close below Higher TF EMA)');