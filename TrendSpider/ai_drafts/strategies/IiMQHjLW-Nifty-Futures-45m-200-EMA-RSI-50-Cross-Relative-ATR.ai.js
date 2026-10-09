describe_indicator('Nifty Futures 45m EMA200 RSI50 Cross ATR', 'price');

// ===== Inputs =====
const myTab = input.tab('Settings');
const myEmaTrendLen = myTab.number('Trend EMA Length', 200, { min: 1, max: 1000 });
const myEmaExitLen = myTab.number('Exit EMA Length', 50, { min: 1, max: 1000 });
const myRsiLen = myTab.number('RSI Length', 14, { min: 1, max: 500 });
const myAtrLen = myTab.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMaLen = myTab.number('ATR SMA Length', 20, { min: 1, max: 500 });
const myAtrMultiplier = myTab.number('ATR Multiplier', 1.0, { min: 0, max: 10, step: 0.1 });

// ===== Calculations =====
const myEma200 = ema(close, myEmaTrendLen);
const myEma50 = ema(close, myEmaExitLen);
const myRsiVal = rsi(close, myRsiLen);
const myAtrVal = atr(high, low, close, myAtrLen);
const myAtrSma = sma(myAtrVal, myAtrMaLen);

// Relative ATR filter: ATR above its own average * multiplier
const myAtrFilter = for_every(myAtrVal, myAtrSma, (_atr, _atrSma) => _atr > _atrSma * myAtrMultiplier);

// ta.crossover(rsiVal, 50): rsi crosses above 50 this bar
// ta.crossunder(rsiVal, 50): rsi crosses below 50 this bar
const myRsiCrossOver = for_every(myRsiVal, (_rsi, _prev, _index) => {
	if (_index === 0) return false;
	return _rsi > 50 && myRsiVal[_index - 1] <= 50;
});

const myRsiCrossUnder = for_every(myRsiVal, (_rsi, _prev, _index) => {
	if (_index === 0) return false;
	return _rsi < 50 && myRsiVal[_index - 1] >= 50;
});

// ===== Entry Conditions =====
const myLongCondition = for_every(close, myEma200, myRsiCrossOver, myAtrFilter, (_close, _ema200, _crossOver, _filter) => {
	return _close > _ema200 && _crossOver && _filter;
});

const myShortCondition = for_every(close, myEma200, myRsiCrossUnder, myAtrFilter, (_close, _ema200, _crossUnder, _filter) => {
	return _close < _ema200 && _crossUnder && _filter;
});

// ===== Position state simulation (to emulate strategy.position_size logic) =====
// We track a simulated position state: 1 = long, -1 = short, 0 = flat
// so that strategy.entry() guard conditions (position_size <= 0 / >= 0)
// and strategy.close() exit conditions are reproduced exactly.
const myPositionState = series_of(0);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevState = myIndex === 0 ? 0 : myPositionState[myIndex - 1];
	let myState = myPrevState;

	if (myLongCondition[myIndex] && myPrevState <= 0) {
		myState = 1;
	}
	else if (myShortCondition[myIndex] && myPrevState >= 0) {
		myState = -1;
	}
	else if (myPrevState > 0 && close[myIndex] < myEma50[myIndex]) {
		myState = 0;
	}
	else if (myPrevState < 0 && close[myIndex] > myEma50[myIndex]) {
		myState = 0;
	}

	myPositionState[myIndex] = myState;
}

// Entry signals (only fire on the actual entry bar, same as strategy.entry)
const myLongEntrySignal = for_every(myLongCondition, myPositionState, (_long, _state, _prevState, _index) => {
	const myPrevState = _index === 0 ? 0 : myPositionState[_index - 1];
	return _long && myPrevState <= 0;
});

const myShortEntrySignal = for_every(myShortCondition, myPositionState, (_short, _state, _prevState, _index) => {
	const myPrevState = _index === 0 ? 0 : myPositionState[_index - 1];
	return _short && myPrevState >= 0;
});

// Exit signals (only fire on the actual exit bar, same as strategy.close)
const myLongExitSignal = for_every(close, myEma50, myPositionState, (_close, _ema50, _state, _prevValue, _index) => {
	const myPrevState = _index === 0 ? 0 : myPositionState[_index - 1];
	return myPrevState > 0 && _close < _ema50;
});

const myShortExitSignal = for_every(close, myEma50, myPositionState, (_close, _ema50, _state, _prevValue, _index) => {
	const myPrevState = _index === 0 ? 0 : myPositionState[_index - 1];
	return myPrevState < 0 && _close > _ema50;
});

// ===== Plots =====
paint(myEma200, { name: 'EMA200', color: '#ef5350', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#4da3ff', thickness: 2 });

const myBuyMarks = for_every(myLongEntrySignal, low, (_signal, _low) => _signal ? _low : null);
const mySellMarks = for_every(myShortEntrySignal, high, (_signal, _high) => _signal ? _high : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// ===== Signals for scanner/alerts/strategy tester =====
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');
register_signal(myLongCondition, 'Long Condition Raw');
register_signal(myShortCondition, 'Short Condition Raw');