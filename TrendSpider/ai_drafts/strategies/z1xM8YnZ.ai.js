describe_indicator('BB Mean Reversion Long', 'price');

// Inputs matching Pine script parameters
const myLength = input.number('Period SMA', 20, { min: 1, max: 500 });
const myMult = input.number('Std Dev Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });
const mySlPct = input.number('Stop Loss Percent', 1.5, { min: 0.1, max: 50, step: 0.1 });

// Bollinger Bands computation (ta.bb equivalent)
const myMiddle = sma(close, myLength);
const myDeviation = mult(stdev(close, myLength), myMult);
const myUpper = add(myMiddle, myDeviation);
const myLower = sub(myMiddle, myDeviation);

// Crossunder(close, lower): close was >= lower previous bar, now close < lower
const myPrevClose = shift(close, 1);
const myPrevLower = shift(myLower, 1);

const myLongEntry = for_every(close, myLower, myPrevClose, myPrevLower, (_c, _l, _pc, _pl) => {
	return _pc >= _pl && _c < _l;
});

// Theoretical stop loss and take profit (limit at middle band) levels,
// computed only for reference; this script cannot place actual orders
const myStopLossLevel = for_every(close, myLongEntry, (_c, _e) => _e ? _c * (1 - mySlPct / 100) : null);
const myTakeProfitLevel = for_every(myMiddle, myLongEntry, (_m, _e) => _e ? _m : null);

// Plot the bands
paint(myMiddle, { name: 'Moyenne', color: 'gray', thickness: 1 });
paint(myUpper, { name: 'BandeHaute', color: 'red', thickness: 1 });
paint(myLower, { name: 'BandeBasse', color: 'green', thickness: 1 });

// Buy signal shape below bar
const myBuyMarks = for_every(low, myLongEntry, (_l, _e) => _e ? _l : null);
paint(myBuyMarks, { name: 'BUY', style: 'labels_below', color: 'green', thickness: 3 });

// Reference stop loss / take profit levels (visual only)
paint(myStopLossLevel, { name: 'StopLossLevel', color: 'orange', style: 'dotted', thickness: 1 });
paint(myTakeProfitLevel, { name: 'TakeProfitLevel', color: 'blue', style: 'dotted', thickness: 1 });

// Signal for scanners, alerts and strategy tester
register_signal(myLongEntry, 'Long Entry');