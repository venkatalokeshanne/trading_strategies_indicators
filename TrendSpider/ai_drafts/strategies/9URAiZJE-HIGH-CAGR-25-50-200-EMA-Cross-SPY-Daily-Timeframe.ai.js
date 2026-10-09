describe_indicator('50 / 200 EMA Cross Filtered Long', 'price');

// === Inputs ===
const tab = input.tab('Settings');

const generalGrp = tab.group('Backtest Window');
const myStartYear = generalGrp.number('Start Year', 1900, { min: 1900, max: 2100 });

const emaGrp = tab.group('EMAs');
const emaRow1 = emaGrp.row();
const myFastLen = emaRow1.number('Fast EMA', 50, { min: 1, max: 1000 });
const mySlowLen = emaRow1.number('Slow EMA', 200, { min: 1, max: 1000 });
const mySmoothLen = emaGrp.number('Extra Smoothing', 1, { min: 1, max: 100 });

const filterGrp = tab.group('Filters');
const myConfirmBars = filterGrp.number('Bars Allowed After Cross', 70, { min: 0, max: 1000 });
const filterRow = filterGrp.row();
const myMinSepPerc = filterRow.number('Min Separation Percent', 0.35, { min: 0, max: 100, step: 0.01 });
const myMinSlopePerc = filterRow.number('Min Slow Slope Percent', 0.0, { min: -100, max: 100, step: 0.01 });

const riskGrp = tab.group('Risk');
const riskRow = riskGrp.row();
const myLeverage = riskRow.number('Leverage', 5, { min: 0.1, max: 100, step: 0.1 });
const myStopPerc = riskRow.number('Hard Stop Percent', 10, { min: 0.1, max: 100, step: 0.1 });

// === Backtest start timestamp (UTC Jan 1st of Start Year) ===
const myStartTime = Date.UTC(myStartYear, 0, 1, 0, 0, 0) / 1000;
const myAllowTrade = for_every(time, _t => _t >= myStartTime);

// === EMAs (double EMA, matching ta.ema(ta.ema(close, fastLen), smoothLen)) ===
const myFast = ema(ema(close, myFastLen), mySmoothLen);
const mySlow = ema(ema(close, mySlowLen), mySmoothLen);

// === Cross detection (crossover / crossunder) ===
// crossover: fast was <= slow on previous bar, and fast > slow on current bar
// crossunder: fast was >= slow on previous bar, and fast < slow on current bar
const myFastPrev = shift(myFast, 1);
const mySlowPrev = shift(mySlow, 1);

const myBullCross = for_every(myFast, mySlow, myFastPrev, mySlowPrev, (_f, _s, _fp, _sp) => {
	return _fp <= _sp && _f > _s;
});

const myBearCross = for_every(myFast, mySlow, myFastPrev, mySlowPrev, (_f, _s, _fp, _sp) => {
	return _fp >= _sp && _f < _s;
});

// === barssince(bullCross) ===
// counts bars since the last true value of bullCross; -1 means "never happened yet"
const myBarsSinceCross = for_every(myBullCross, (_bull, _prev, _index) => {
	if (_bull) return 0;
	if (_prev === null || _prev === undefined || _prev < 0) return -1;
	return _prev + 1;
});

// === Separation filter ===
const mySepPerc = mult(div(for_every(myFast, mySlow, (_f, _s) => Math.abs(_f - _s)), mySlow), 100);
const mySepOk = for_every(mySepPerc, _sep => _sep > myMinSepPerc);

// === Slope filter ===
const mySlowShift5 = shift(mySlow, 5);
const mySlopePerc = mult(div(sub(mySlow, mySlowShift5), mySlow), 100);
const mySlopeOk = for_every(mySlopePerc, _slope => _slope >= myMinSlopePerc);

// === Entry / Exit signals ===
const myEnterLong = for_every(
	myAllowTrade, myBarsSinceCross, myFast, mySlow, mySepOk, mySlopeOk,
	(_allow, _barsSince, _f, _s, _sepOk, _slopeOk) => {
		return _allow && _barsSince >= 0 && _barsSince <= myConfirmBars && _f > _s && _sepOk && _slopeOk;
	}
);

const myExitLong = for_every(myAllowTrade, myBearCross, (_allow, _bear) => _allow && _bear);

// === Hard stop level (based on entry price) ===
// Note: strategy position tracking (equity, position size, average entry price)
// is not available in the Custom JS API; this indicator exposes the entry and
// exit conditions as signals, suitable for scanners, alerts and the Strategy
// Tester, which handles actual position sizing, pyramiding and stop execution.
const myStopLevel = series_of(null);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myEnterLong[myIndex]) {
		myStopLevel[myIndex] = close[myIndex] * (1 - myStopPerc / 100);
	}
	else if (myIndex > 0) {
		myStopLevel[myIndex] = myExitLong[myIndex] ? null : myStopLevel[myIndex - 1];
	}
}

// === Plots ===
paint(myFast, { name: 'Fast EMA', color: '#26A69A', thickness: 2 });
paint(mySlow, { name: 'Slow EMA', color: '#EF5350', thickness: 2 });
paint(myStopLevel, { name: 'Hard Stop Level', color: '#FFA726', thickness: 1, style: 'dotted' });

// === Signals for Scanner / Alerts / Strategy Tester ===
register_signal(myEnterLong, 'Enter Long');
register_signal(myExitLong, 'Exit Long');
register_signal(myBullCross, 'Bullish Cross');
register_signal(myBearCross, 'Bearish Cross');