describe_indicator('Harami BB Strategy Signals', 'price');

// Note: TradingView strategy TP/SL execution (profit=40, loss=20 cash
// points) and backtesting equity are not reproducible in this API.
// Only the signal logic (entries) is translated 1:1; use TrendSpider's
// Strategy Tester component with these registered signals to apply
// TP/SL rules.

const myBBLength = input.number('BB Length', 20, { min: 1, max: 500 });
const myBBMultiplier = input.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

// Using chart's open/high/low/close directly (script uses "ha_" naming
// but assigns plain open/high/low/close, no actual Heikin Ashi math)
const myBasis = sma(close, myBBLength);
const myDev = mult(stdev(close, myBBLength), myBBMultiplier);
const myUpperBB = add(myBasis, myDev);
const myLowerBB = sub(myBasis, myDev);

const myPrevHigh = shift(max_of(open, close), 1);
const myPrevLow = shift(min_of(open, close), 1);
const myCurrHigh = max_of(open, close);
const myCurrLow = min_of(open, close);

const myPrevLowShifted = shift(low, 1);
const myPrevHighShifted = shift(high, 1);
const myPrevUpperBB = shift(myUpperBB, 1);
const myPrevLowerBB = shift(myLowerBB, 1);
const myPrevClose = shift(close, 1);
const myPrevOpen = shift(open, 1);

const myFirstTouchLower = for_every(myPrevLowShifted, myPrevLowerBB, (_l, _lb) => _l <= _lb);
const myFirstTouchUpper = for_every(myPrevHighShifted, myPrevUpperBB, (_h, _ub) => _h >= _ub);

const myBodyInside = for_every(myCurrHigh, myCurrLow, myPrevHigh, myPrevLow, (_ch, _cl, _ph, _pl) => _ch <= _ph && _cl >= _pl);

const myBullSignal = for_every(myFirstTouchLower, myPrevClose, myPrevOpen, myBodyInside, (_ftl, _pc, _po, _bi) => _ftl && (_pc < _po) && _bi);
const myBearSignal = for_every(myFirstTouchUpper, myPrevClose, myPrevOpen, myBodyInside, (_ftu, _pc, _po, _bi) => _ftu && (_pc > _po) && _bi);

paint(myBasis, { name: 'BB Basis', color: '#2962FF' });

const myUpperLinePainted = paint(myUpperBB, { name: 'Upper BB', color: '#90A4AE' });
const myLowerLinePainted = paint(myLowerBB, { name: 'Lower BB', color: '#90A4AE' });
fill(myUpperLinePainted, myLowerLinePainted, '#2962FF', 0.1);

const myBullMarks = for_every(myBullSignal, low, (_s, _l) => _s ? _l : null);
const myBearMarks = for_every(myBearSignal, high, (_s, _h) => _s ? _h : null);

paint(myBullMarks, { name: 'Bull Harami', style: 'labels_below', color: 'lime' });
paint(myBearMarks, { name: 'Bear Harami', style: 'labels_above', color: 'red' });

register_signal(myBullSignal, 'Bull Harami Reversal');
register_signal(myBearSignal, 'Bear Harami Reversal');