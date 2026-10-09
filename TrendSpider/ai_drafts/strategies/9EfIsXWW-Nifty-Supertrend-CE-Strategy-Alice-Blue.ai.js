describe_indicator('NIFTY Supertrend CE Strategy', 'price');

// Inputs matching the original Pine Script
const myAtrPeriod = input.number('ATR Period', 10, { min: 1, max: 100 });
const myFactor = input.number('Supertrend Factor', 3.0, { min: 0.1, max: 20, step: 0.1 });
const mySlPercent = input.number('Stop Loss %', 15.0, { min: 0.1, max: 100, step: 0.1 });
const myTpPercent = input.number('Target %', 30.0, { min: 0.1, max: 100, step: 0.1 });

// Built-in Supertrend only returns the Supertrend line itself (no direction
// output like Pine's ta.supertrend does). We reconstruct direction the same
// way Pine does internally: price above the line = bullish (dir < 0),
// price below the line = bearish (dir > 0).
const mySupertrendLine = supertrend(myAtrPeriod, myFactor, false);
const myDir = for_every(close, mySupertrendLine, (_c, _st) => (_c > _st ? -1 : 1));
const myPrevDir = shift(myDir, 1);

// buySignal = dir < 0 and dir[1] > 0 (bullish flip)
const myBuySignal = for_every(myDir, myPrevDir, (_d, _pd) => (_d < 0 && _pd > 0));

// exitSignal = dir > 0 and dir[1] < 0 (bearish flip)
const myExitSignal = for_every(myDir, myPrevDir, (_d, _pd) => (_d > 0 && _pd < 0));

// Stop loss / target price levels, calculated off the entry close price,
// for reference only (visual guide, not an actual position tracker).
const myStopPrice = for_every(myBuySignal, close, (_b, _c, _prev, _i) => {
	return _b ? _c * (1 - mySlPercent / 100) : (_prev == null ? null : _prev);
});
const myTargetPrice = for_every(myBuySignal, close, (_b, _c, _prev, _i) => {
	return _b ? _c * (1 + myTpPercent / 100) : (_prev == null ? null : _prev);
});

// Reset stop/target lines once an exit signal fires, so they do not persist
// visually after a position would have been closed.
const myStopPriceClipped = for_every(myStopPrice, myExitSignal, (_s, _e, _prev) => (_e ? null : _s));
const myTargetPriceClipped = for_every(myTargetPrice, myExitSignal, (_s, _e, _prev) => (_e ? null : _s));

const myLineColor = for_every(myDir, _d => (_d < 0 ? '#26A69A' : '#EF5350'));

const mySupertrendPainted = paint(mySupertrendLine, { name: 'Supertrend', color: myLineColor, thickness: 2 });

const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => (_b ? _l : null));
const myExitMarks = for_every(myExitSignal, high, (_e, _h) => (_e ? _h : null));

paint(myBuyMarks, { name: 'BUY', style: 'labels_below', color: '#26A69A' });
paint(myExitMarks, { name: 'EXIT', style: 'labels_above', color: '#EF5350' });

paint(myStopPriceClipped, { name: 'StopLoss', color: '#EF5350', style: 'dotted', forceUsePriceAxis: true });
paint(myTargetPriceClipped, { name: 'Target', color: '#26A69A', style: 'dotted', forceUsePriceAxis: true });

// Signals usable in Scanners, Alerts and Strategy Tester
register_signal(myBuySignal, 'Entry Signal');
register_signal(myExitSignal, 'Exit Signal');