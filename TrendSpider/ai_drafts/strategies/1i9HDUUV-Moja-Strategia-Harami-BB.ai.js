describe_indicator('Harami BB Strategy Signals', 'price');

// Note: strategy TP/SL execution (profit=40, loss=20 in price points)
// cannot be backtested inside a plain indicator script - Custom JS API
// has no strategy/order engine here. We expose the entry signals
// (bullSignal/bearSignal) via register_signal() so they can be used
// in TrendSpider's Strategy Tester / Scanner / Alerts modules instead.

const myBbLen = input.number('BB Length', 20, { min: 1, max: 500 });
const myBbMult = input.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

// Using regular OHLC (Pine script's "Heikin Ashi" vars were just
// assigned to plain open/high/low/close, so no HA transform happens)
const myHaOpen = open;
const myHaHigh = high;
const myHaLow = low;
const myHaClose = close;

const myBasis = sma(myHaClose, myBbLen);
const myDev = mult(stdev(myHaClose, myBbLen), myBbMult);
const myUpperBB = add(myBasis, myDev);
const myLowerBB = sub(myBasis, myDev);

const myPrevHigh = shift(max_of(myHaOpen, myHaClose), 1);
const myPrevLow = shift(min_of(myHaOpen, myHaClose), 1);
const myCurrHigh = max_of(myHaOpen, myHaClose);
const myCurrLow = min_of(myHaOpen, myHaClose);

const myFirstTouchLower = for_every(shift(myHaLow, 1), shift(myLowerBB, 1), (_lo, _lb) => _lo <= _lb);
const myFirstTouchUpper = for_every(shift(myHaHigh, 1), shift(myUpperBB, 1), (_hi, _ub) => _hi >= _ub);

const myBodyInside = for_every(myCurrHigh, myCurrLow, myPrevHigh, myPrevLow,
	(_ch, _cl, _ph, _pl) => _ch <= _ph && _cl >= _pl);

const myPrevClose = shift(myHaClose, 1);
const myPrevOpen = shift(myHaOpen, 1);

const myBullSignal = for_every(myFirstTouchLower, myPrevClose, myPrevOpen, myBodyInside,
	(_ftl, _pc, _po, _bi) => _ftl && (_pc < _po) && _bi);

const myBearSignal = for_every(myFirstTouchUpper, myPrevClose, myPrevOpen, myBodyInside,
	(_ftu, _pc, _po, _bi) => _ftu && (_pc > _po) && _bi);

paint(myBasis, { name: 'BB Basis', color: '#2962FF' });

fill(
	paint(myUpperBB, { name: 'Upper BB', color: '#90CAF9' }),
	paint(myLowerBB, { name: 'Lower BB', color: '#90CAF9' }),
	'#2962FF',
	0.1
);

const myBullMarks = for_every(myBullSignal, low, (_sig, _lo) => _sig ? _lo : null);
const myBearMarks = for_every(myBearSignal, high, (_sig, _hi) => _sig ? _hi : null);

paint(myBullMarks, { name: 'Bull Harami', style: 'labels_below', color: '#00E676' });
paint(myBearMarks, { name: 'Bear Harami', style: 'labels_above', color: '#FF1744' });

register_signal(myBullSignal, 'Bull Harami Reversal');
register_signal(myBearSignal, 'Bear Harami Reversal');