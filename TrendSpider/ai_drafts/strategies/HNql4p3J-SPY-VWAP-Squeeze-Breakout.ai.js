describe_indicator('SPY VWAP + Squeeze Breakout', 'price');

// --- Inputs ---
const myBBLength = input.number('BB Length', 20, { min: 1, max: 300 });
const myBBMult = input.number('BB StdDev', 2.0, { min: 0.1, max: 10 });
const myKCLength = input.number('KC Length', 20, { min: 1, max: 300 });
const myKCMult = input.number('KC Multiplier', 1.5, { min: 0.1, max: 10 });

// Bollinger Bands
const myBasis = sma(close, myBBLength);
const myDev = mult(stdev(close, myBBLength), myBBMult);
const myUpperBB = add(myBasis, myDev);
const myLowerBB = sub(myBasis, myDev);

// Keltner Channels (using ATR-like True Range, length-based SMA, matching ta.tr(true))
const myKCMa = sma(close, myKCLength);
const myRangeKC = atr(high, low, close, 1); // true range per candle (ATR with length 1 == TR)
const myRangeMA = sma(myRangeKC, myKCLength);
const myUpperKC = add(myKCMa, mult(myRangeMA, myKCMult));
const myLowerKC = sub(myKCMa, mult(myRangeMA, myKCMult));

// Session VWAP (resets every new trading session, mimicking ta.vwap default daily behavior)
const mySessionAtIndex = time.map(_t => bar_at(_t).session);
const myVwapVal = series_of(null);

for (let myCandleIndex = 0; myCandleIndex < close.length; myCandleIndex += 1) {
	const myNewSession = myCandleIndex === 0 || mySessionAtIndex[myCandleIndex] !== mySessionAtIndex[myCandleIndex - 1];
	if (myNewSession) {
		myVwapVal[myCandleIndex] = -1; // marker, filled below
	}
}

// find session start indexes and compute vwap per-segment
const mySessionStarts = [];
for (let myCandleIndex = 0; myCandleIndex < close.length; myCandleIndex += 1) {
	if (myCandleIndex === 0 || mySessionAtIndex[myCandleIndex] !== mySessionAtIndex[myCandleIndex - 1]) {
		mySessionStarts.push(myCandleIndex);
	}
}

for (let mySegmentIndex = 0; mySegmentIndex < mySessionStarts.length; mySegmentIndex += 1) {
	const myFromIndex = mySessionStarts[mySegmentIndex];
	const myToIndex = mySegmentIndex + 1 < mySessionStarts.length ? mySessionStarts[mySegmentIndex + 1] - 1 : close.length - 1;
	const mySegmentVwap = vwap(myFromIndex, myToIndex);
	for (let myCandleIndex = myFromIndex; myCandleIndex <= myToIndex; myCandleIndex += 1) {
		myVwapVal[myCandleIndex] = mySegmentVwap[myCandleIndex];
	}
}

// --- Squeeze Condition ---
const mySqzOn = for_every(myLowerBB, myLowerKC, myUpperBB, myUpperKC, (_lowerBB, _lowerKC, _upperBB, _upperKC) => (_lowerBB > _lowerKC) && (_upperBB < _upperKC));
const mySqzOff = for_every(myLowerBB, myLowerKC, myUpperBB, myUpperKC, (_lowerBB, _lowerKC, _upperBB, _upperKC) => (_lowerBB < _lowerKC) || (_upperBB > _upperKC));
const mySqzOnPrev = shift(mySqzOn, 1);
const mySqzFired = for_every(mySqzOff, mySqzOnPrev, (_off, _onPrev) => _off === true && _onPrev === true);

// --- Entry Conditions ---
const myLongCondition = for_every(close, myVwapVal, mySqzFired, open, (_close, _vwap, _fired, _open) => _close > _vwap && _fired === true && _close > _open);
const myShortCondition = for_every(close, myVwapVal, mySqzFired, open, (_close, _vwap, _fired, _open) => _close < _vwap && _fired === true && _close < _open);

// --- Exit Conditions (position-size based logic from Pine can't be replicated
// without live strategy state, so these are expressed as close-crossing-vwap
// signals, usable as exit triggers in a Strategy Tester component) ---
const myLongExitCondition = for_every(close, myVwapVal, (_close, _vwap) => _close < _vwap);
const myShortExitCondition = for_every(close, myVwapVal, (_close, _vwap) => _close > _vwap);

// --- Paint ---
paint(myBasis, { name: 'BBBasis', color: 'gray', style: 'dotted' });
fill(
	paint(myUpperBB, { name: 'BBUpper', color: '#4DA3FF' }),
	paint(myLowerBB, { name: 'BBLower', color: '#4DA3FF' }),
	'blue',
	0.1
);
paint(myUpperKC, { name: 'KCUpper', color: '#EF5350', style: 'dotted' });
paint(myLowerKC, { name: 'KCLower', color: '#EF5350', style: 'dotted' });
paint(myVwapVal, { name: 'VWAP', color: '#FFA726', thickness: 2 });

// --- Signals for scanners, alerts and strategy tester ---
register_signal(myLongCondition, 'Long Squeeze Entry');
register_signal(myShortCondition, 'Short Squeeze Entry');
register_signal(myLongExitCondition, 'Long Squeeze Exit');
register_signal(myShortExitCondition, 'Short Squeeze Exit');
register_signal(mySqzFired, 'Squeeze Fired');
register_signal(mySqzOn, 'Squeeze On');