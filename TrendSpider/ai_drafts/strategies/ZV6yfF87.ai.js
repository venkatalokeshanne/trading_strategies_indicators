describe_indicator('SuperTrend Strategy Long Short', 'price');

// SuperTrend settings
const atrPeriod = input.number('ATR Length', 10, { min: 1 });
const multiplier = input.number('Factor', 3.0, { min: 0.01, step: 0.01 });

// built-in supertrend() returns the trend line series; direction is
// derived by comparing it to close, matching Pine's ta.supertrend logic
// (stDir < 0 means uptrend/bullish, stDir > 0 means downtrend/bearish)
const myStLine = supertrend(atrPeriod, multiplier, false);

// Determine direction: bullish when price is above the SuperTrend line
const myIsBull = for_every(close, myStLine, (_c, _s) => _s !== null && _c > _s);
const myIsBear = for_every(close, myStLine, (_c, _s) => _s !== null && _c < _s);

// Detect direction change (equivalent to ta.change(stDir) != 0)
const myDirChanged = for_every(myIsBull, (_bull, _prev, _i) => {
	if (_i === 0) return false;
	return _bull !== myIsBull[_i - 1];
});

const myBuySignal = for_every(myDirChanged, myIsBull, (_changed, _bull) => _changed && _bull);
const mySellSignal = for_every(myDirChanged, myIsBear, (_changed, _bear) => _changed && _bear);

// Up/Down trend lines (plotted with gaps, like plot.style_linebr)
const myUpTrendLine = for_every(myIsBull, myStLine, (_bull, _s) => _bull ? _s : null);
const myDownTrendLine = for_every(myIsBear, myStLine, (_bear, _s) => _bear ? _s : null);

paint(myUpTrendLine, { name: 'UpTrend', color: '#26A69A', thickness: 2, style: 'line' });
paint(myDownTrendLine, { name: 'DownTrend', color: '#EF5350', thickness: 2, style: 'line' });

// Buy/Sell shapes
const myBuyMarks = for_every(myBuySignal, _b => _b ? true : null);
const mySellMarks = for_every(mySellSignal, _s => _s ? true : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

paint_label_at_line(paint(myUpTrendLine, { name: 'UpTrendLabel', color: '#26A69A', thickness: 2, style: 'line' }), close.length - 1, 'ST');

// Register signals for scanner/alerts/strategy use
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myIsBull, 'Bullish Trend');
register_signal(myIsBear, 'Bearish Trend');