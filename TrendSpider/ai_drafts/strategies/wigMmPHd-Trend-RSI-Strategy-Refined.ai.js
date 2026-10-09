describe_indicator('Trend Plus RSI Strategy Enhanced', 'price');

// === Inputs ===
const myFastLength = input.number('Fast EMA', 9, { min: 1, max: 500 });
const mySlowLength = input.number('Slow EMA', 21, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 500 });
const myRsiThreshold = input.number('RSI Threshold', 50, { min: 1, max: 99 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMultiplier = input.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 10 });

// === Indicators ===
const myFastEMA = ema(close, myFastLength);
const mySlowEMA = ema(close, mySlowLength);
const myRsi = rsi(close, myRsiLength);
const myAtr = atr(high, low, close, myAtrLength);

// === Conditions ===
const myTrendUp = for_every(myFastEMA, mySlowEMA, (_fast, _slow) => _fast > _slow);
const myTrendDown = for_every(myFastEMA, mySlowEMA, (_fast, _slow) => _fast < _slow);

const myLongCondition = for_every(myTrendUp, myRsi, (_up, _r) => _up && _r > myRsiThreshold);
const myShortCondition = for_every(myTrendDown, myRsi, (_down, _r) => _down && _r < myRsiThreshold);

// === Position state simulation (to replicate strategy.position_size == 0 check) ===
// Note: this reproduces Pine's "flat position" gating logic using a running
// state machine, since there is no native position tracking in this engine.
const myPositionState = for_every(myLongCondition, myShortCondition, (_long, _short, _prev, _index) => {
	const myPrevState = _index === 0 ? 0 : _prev;
	if (myPrevState === 0) {
		if (_long) return 1;
		if (_short) return -1;
		return 0;
	}
	return myPrevState;
});

const myLongEntry = for_every(myLongCondition, myPositionState, (_long, _state, _prev, _index) => {
	const myPrevStateVal = _index === 0 ? 0 : (_prev === undefined ? 0 : null);
	return _long && _state === 1 && (_index === 0 ? true : myPositionState[_index - 1] !== 1);
});

const myShortEntry = for_every(myShortCondition, myPositionState, (_short, _state, _prev, _index) => {
	return _short && _state === -1 && (_index === 0 ? true : myPositionState[_index - 1] !== -1);
});

// === Stops and Targets (for reference / scanning use) ===
const myLongStop = sub(close, mult(myAtr, myAtrMultiplier));
const myShortStop = add(close, mult(myAtr, myAtrMultiplier));
const myLongTarget = add(close, mult(myAtr, myAtrMultiplier * 2));
const myShortTarget = sub(close, mult(myAtr, myAtrMultiplier * 2));

// === Plots ===
paint(myFastEMA, { name: 'Fast EMA', color: '#2962FF', thickness: 2 });
paint(mySlowEMA, { name: 'Slow EMA', color: '#EF5350', thickness: 2 });

// === Signals for Scanner, Alerts and Strategy Tester ===
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myLongCondition, 'Long Condition');
register_signal(myShortCondition, 'Short Condition');