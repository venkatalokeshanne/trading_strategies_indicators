describe_indicator('9 21 EMA VWAP Volume Spike Bollinger Bands', 'price');

// Inputs, grouped for readability
const emaTab = input.tab('EMA And Volume');
const emaFastLen = emaTab.number('Fast EMA Length', 9, { min: 1, max: 200 });
const emaSlowLen = emaTab.number('Slow EMA Length', 21, { min: 1, max: 300 });
const volLookback = emaTab.number('Avg Volume Lookback', 20, { min: 1, max: 300 });
const volMultiplier = emaTab.number('Volume Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });

const bbTab = input.tab('Bollinger Bands');
const bbLength = bbTab.number('BB Length', 21, { min: 1, max: 300 });
const bbStdDev = bbTab.number('BB StdDev', 2.0, { min: 0.1, max: 10, step: 0.1 });

// Core moving averages
const myEmaFast = ema(close, emaFastLen);
const myEmaSlow = ema(close, emaSlowLen);

// Session-anchored VWAP, reset at the start of each trading day,
// computed manually since the built-in vwap() cannot be called
// incrementally inside a loop. This reproduces Pine's ta.vwap()
// daily reset behavior.
const mySessionAtIndex = time.map(_t => bar_at(_t).session);
const myVwap = series_of(null);
let myCumPV = 0;
let myCumVol = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewSession = myIndex === 0 || mySessionAtIndex[myIndex] !== mySessionAtIndex[myIndex - 1];

	if (myNewSession) {
		myCumPV = 0;
		myCumVol = 0;
	}

	const myTypicalPrice = hlc3[myIndex];
	myCumPV += myTypicalPrice * volume[myIndex];
	myCumVol += volume[myIndex];
	myVwap[myIndex] = myCumVol !== 0 ? (myCumPV / myCumVol) : myTypicalPrice;
}

// Bollinger Bands using EMA basis
const myBbBasis = ema(close, bbLength);
const myBbDev = mult(stdev(close, bbLength), bbStdDev);
const myBbUpper = add(myBbBasis, myBbDev);
const myBbLower = sub(myBbBasis, myBbDev);

// Volume spike condition
const myAvgVol = sma(volume, volLookback);
const myHighVolume = for_every(volume, myAvgVol, (_v, _avg) => _v >= _avg * volMultiplier);

// EMA crossover / crossunder logic (manual, since Pine's
// ta.crossover/crossunder are not built-in functions here)
const myBullishCross = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast > _slow && myEmaFast[_index - 1] <= myEmaSlow[_index - 1];
});

const myBearishCross = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast < _slow && myEmaFast[_index - 1] >= myEmaSlow[_index - 1];
});

// Buy and sell signals require the cross plus a volume spike
const myBuySignal = for_every(myBullishCross, myHighVolume, (_cross, _vol) => _cross && _vol);
const mySellSignal = for_every(myBearishCross, myHighVolume, (_cross, _vol) => _cross && _vol);

// Debug labels: raw EMA cross, regardless of volume
const myDebugBuyMarks = for_every(myBullishCross, (_cross) => _cross ? constants.icons.triangle_up : null);
const myDebugSellMarks = for_every(myBearishCross, (_cross) => _cross ? constants.icons.triangle_down : null);

// True signal labels: cross plus volume spike
const myBuyMarks = for_every(myBuySignal, (_sig) => _sig ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, (_sig) => _sig ? constants.icons.triangle_down : null);

// Paint EMAs
paint(myEmaFast, { name: 'EMA Fast', color: '#26A69A', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#EF5350', thickness: 2 });

// Paint VWAP
paint(myVwap, { name: 'VWAP', color: '#AB47BC', thickness: 2 });

// Paint Bollinger Bands with fill
paint(myBbBasis, { name: 'BB Basis', color: '#FFA726', style: 'dotted' });
fill(
	paint(myBbUpper, { name: 'BB Upper', color: '#42A5F5' }),
	paint(myBbLower, { name: 'BB Lower', color: '#42A5F5' }),
	'#42A5F5',
	0.1
);

// Paint debug cross markers (no volume filter)
paint(myDebugBuyMarks, { name: 'Debug Buy', style: 'labels_below', color: 'green' });
paint(myDebugSellMarks, { name: 'Debug Sell', style: 'labels_above', color: 'red' });

// Paint true buy/sell signal markers (cross plus volume spike)
paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#2E7D32' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#C62828' });

// Register signals for scanners, alerts and strategy testing.
// Names here must be unique across both paint() and register_signal()
// calls, so these have been renamed to avoid colliding with the
// "Buy Signal" / "Sell Signal" names used by the paint() labels above.
register_signal(myBullishCross, 'Bullish EMA Cross Signal');
register_signal(myBearishCross, 'Bearish EMA Cross Signal');
register_signal(myHighVolume, 'High Volume Signal');
register_signal(myBuySignal, 'Buy Entry Signal');
register_signal(mySellSignal, 'Sell Entry Signal');