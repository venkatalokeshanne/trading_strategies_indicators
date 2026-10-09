describe_indicator('BB vs EMA 9 Gap Signals', 'price');

// ───── Inputs ─────
const myEmaLength = input.number('EMA Length', 9, { min: 1, max: 500 });
const myBbLength = input.number('BB Length', 20, { min: 1, max: 500 });
const myBbMult = input.number('BB Std Dev', 2.0, { min: 0.1, max: 10 });

// ───── EMA ─────
const myEma9 = ema(close, myEmaLength);

// ───── Bollinger Bands ─────
const myBbBasis = sma(close, myBbLength);
const myBbDev = mult(stdev(close, myBbLength), myBbMult);

const myUpperBB = add(myBbBasis, myBbDev);
const myLowerBB = sub(myBbBasis, myBbDev);

// ───── Distance Calculations ─────
// X = distance between Upper BB and EMA
const myX = sub(myUpperBB, myEma9);
// Y = distance between EMA and Lower BB
const myY = sub(myEma9, myLowerBB);

// ───── BB Touch / Cross ─────
const myTouchedLowerBB = for_every(low, myLowerBB, (_l, _lb) => _l <= _lb);
const myTouchedUpperBB = for_every(high, myUpperBB, (_h, _ub) => _h >= _ub);

// ───── BUY / SELL conditions ─────
const myBuySignal = for_every(myY, myX, myTouchedLowerBB, (_y, _x, _touch) => _y > _x && _touch);
const mySellSignal = for_every(myX, myY, myTouchedUpperBB, (_x, _y, _touch) => _x > _y && _touch);

// ───── Plot EMA and Bollinger Bands ─────
paint(myEma9, { name: 'EMA9', color: 'orange', thickness: 2 });

const myUpperPlot = paint(myUpperBB, { name: 'UpperBB', color: 'blue' });
const myLowerPlot = paint(myLowerBB, { name: 'LowerBB', color: 'blue' });
paint(myBbBasis, { name: 'BBBasis', color: 'gray' });

fill(myUpperPlot, myLowerPlot, 'blue', 0.1);

// ───── Buy / Sell markers ─────
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'BUY', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'SELL', style: 'labels_above', color: 'red' });

// ───── Signals for scanner/alerts/strategy ─────
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');