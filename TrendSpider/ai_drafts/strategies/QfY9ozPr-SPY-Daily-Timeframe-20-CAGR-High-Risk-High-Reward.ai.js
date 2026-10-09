describe_indicator('21 75 EMA Cross Filtered Long Only', 'price');

// This is a translation of a Pine Script STRATEGY into an INDICATOR.
// The Custom JS API has no strategy/order/position-sizing engine
// (no strategy.entry, strategy.exit, strategy.equity, qty sizing,
// pyramiding, stop orders, etc). So this script reproduces the Pine
// signal logic (EMA of EMA, crossover/crossunder, time filter) EXACTLY,
// and exposes Enter Long / Exit Long as scanner/alert signals.
// The hard stop level is approximated as a reference line computed
// from the close price at the last Enter Long signal (a proxy for
// strategy.position_avg_price, since there is no real position
// tracking here).

const myStartYear = input.number('Start Year', 1940, { min: 1900, max: 2100 });
const myFastLen = input.number('Fast EMA', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA', 70, { min: 1, max: 500 });
const mySmoothLen = input.number('Extra Smoothing', 100, { min: 1, max: 500 });
const myStopPerc = input.number('Hard Stop Percent', 10, { min: 0, max: 100 });

// startTime = timestamp(startYear, 1, 1, 0, 0) -> approximated as Jan 1st UTC
const myStartTimestamp = Date.UTC(myStartYear, 0, 1, 0, 0, 0) / 1000;
const myAllowTrade = time.map(myT => myT >= myStartTimestamp);

// fast = ema(ema(close, fastLen), smoothLen)
const myFastRaw = ema(close, myFastLen);
const myFast = ema(myFastRaw, mySmoothLen);

// slow = ema(ema(close, slowLen), smoothLen)
const mySlowRaw = ema(close, mySlowLen);
const mySlow = ema(mySlowRaw, mySmoothLen);

// crossover / crossunder, computed manually since no built-in crossover function
const myBullCross = for_every(myFast, mySlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast > _slow && myFast[_index - 1] <= mySlow[_index - 1];
});

const myBearCross = for_every(myFast, mySlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast < _slow && myFast[_index - 1] >= mySlow[_index - 1];
});

const myEnterLong = for_every(myBullCross, myAllowTrade, (_bull, _allow) => _bull && _allow);
const myExitLong = for_every(myBearCross, myAllowTrade, (_bear, _allow) => _bear && _allow);

// Tracks the close price at the most recent Enter Long signal,
// used as a proxy for strategy.position_avg_price.
const myLastEntryPrice = for_every(myEnterLong, close, (_enter, _close, _prev, _index) => {
	if (_enter) return _close;
	return _index === 0 ? null : _prev;
});

const myStopLine = mult(myLastEntryPrice, 1 - myStopPerc / 100);

paint(myFast, { name: 'Fast EMA', color: '#26A69A', thickness: 2 });
paint(mySlow, { name: 'Slow EMA', color: '#EF5350', thickness: 2 });
paint(myStopLine, { name: 'Hard Stop Level', color: '#FFA726', style: 'dotted', thickness: 1 });

register_signal(myEnterLong, 'Enter Long');
register_signal(myExitLong, 'Exit Long');