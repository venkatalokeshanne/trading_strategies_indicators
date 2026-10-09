describe_indicator('XAUUSD EMA Cross Strategy Signals', 'price');

// Inputs
const myTab = input.tab('Settings');

const myRiskGroup = myTab.group('Risk Management');
const myRiskPercent = myRiskGroup.number('Risk Percent per Trade', 1.0, { min: 0.1, max: 100, step: 0.1 });
const myEquity = myRiskGroup.number('Account Equity (approx)', 10000, { min: 1, max: 100000000 });

const myAtrGroup = myTab.group('ATR Multipliers');
const myAtrSLMult = myAtrGroup.number('SL ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myAtrTPMult = myAtrGroup.number('TP ATR Multiplier', 4.0, { min: 0.1, max: 20, step: 0.1 });

const myEmaGroup = myTab.group('EMA Lengths');
const myFastLength = myEmaGroup.number('Fast EMA Length', 20, { min: 1, max: 500 });
const mySlowLength = myEmaGroup.number('Slow EMA Length', 50, { min: 1, max: 500 });
const myAtrLength = myEmaGroup.number('ATR Length', 14, { min: 1, max: 200 });

// Core indicators
const myFastEMA = ema(close, myFastLength);
const mySlowEMA = ema(close, mySlowLength);
const myAtrValue = atr(high, low, close, myAtrLength);

// Trend conditions
const myBull = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f > _s);
const myBear = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f < _s);

// Crossover / crossunder of close vs fast EMA (manual, since no built-in crossover function)
const myCrossOver = for_every(close, myFastEMA, (_c, _f, _p, _i) => {
	if (_i === 0) return false;
	return _c > _f && close[_i - 1] <= myFastEMA[_i - 1];
});
const myCrossUnder = for_every(close, myFastEMA, (_c, _f, _p, _i) => {
	if (_i === 0) return false;
	return _c < _f && close[_i - 1] >= myFastEMA[_i - 1];
});

// Buy / Sell signals
const myBuySignal = for_every(myBull, myCrossOver, (_b, _co) => _b && _co);
const mySellSignal = for_every(myBear, myCrossUnder, (_b, _cu) => _b && _cu);

// SL / TP levels (approximate equity-based lot sizing, no live equity tracking available)
const myLongSL = sub(close, mult(myAtrValue, myAtrSLMult));
const myLongTP = add(close, mult(myAtrValue, myAtrTPMult));
const myShortSL = add(close, mult(myAtrValue, myAtrSLMult));
const myShortTP = sub(close, mult(myAtrValue, myAtrTPMult));

// Lot sizing: assumes a static account equity input, since the engine has
// no access to live strategy equity / open position tracking
const mySlDist = mult(myAtrValue, myAtrSLMult);
const myRiskAmount = myEquity * (myRiskPercent / 100);
const myLotRaw = for_every(mySlDist, _d => _d > 0 ? myRiskAmount / _d : 0.01);
const myLot = for_every(myLotRaw, _l => Math.round(_l * 100) / 100);

// Paint EMAs
const myFastEMALine = paint(myFastEMA, { name: 'Fast EMA', color: '#26A69A', thickness: 2 });
const mySlowEMALine = paint(mySlowEMA, { name: 'Slow EMA', color: '#EF5350', thickness: 2 });

// Buy / Sell markers
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy Signal Mark', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(mySellMarks, { name: 'Sell Signal Mark', style: 'labels_above', color: '#EF5350', thickness: 3 });

// Register signals for scanners, alerts and strategy tester.
// register_signal() must be called exactly once per unique name, and
// never inside a conditional block, so these two calls below are the
// only registration points for Buy/Sell signals in this script.
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');

// Labels showing that SL/TP/Lot were computed for the latest signal.
// paint_label_at_line() itself is fine inside an if, since it is not a
// paint()/register_signal() call, but we guard with the last index only.
const myLastIndex = close.length - 1;
if (myBuySignal[myLastIndex]) {
	paint_label_at_line(myFastEMALine, myLastIndex, 'Buy SLTPLot computed', { color: '#26A69A' });
}
if (mySellSignal[myLastIndex]) {
	paint_label_at_line(mySlowEMALine, myLastIndex, 'Sell SLTPLot computed', { color: '#EF5350' });
}