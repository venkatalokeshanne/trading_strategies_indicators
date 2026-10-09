describe_indicator('MACD plus EMA18 Signal Strategy', 'lower');

// Core indicators, computed once (never inside loops)
const myEma18 = ema(close, 18);
const mySmaHigh = sma(high, 10);
const mySmaLow = sma(low, 10);

const myFastEma = ema(close, 12);
const mySlowEma = ema(close, 26);
const myMacdLine = sub(myFastEma, mySlowEma);
const mySignalLine = ema(myMacdLine, 9);

// Crossover / crossunder helper series computed with for_every (no loops over indicator calls)
const myCrossover = for_every(myMacdLine, mySignalLine, (_macd, _signal, _prev, _index) => {
	if (_index === 0) return false;
	return _macd > _signal && myMacdLine[_index - 1] <= mySignalLine[_index - 1];
});

const myCrossunder = for_every(myMacdLine, mySignalLine, (_macd, _signal, _prev, _index) => {
	if (_index === 0) return false;
	return _macd < _signal && myMacdLine[_index - 1] >= mySignalLine[_index - 1];
});

// Buy / Sell raw conditions (ignoring position state)
const myBuyCondition = for_every(myCrossover, close, myEma18, (_cross, _close, _ema) => _cross && _close > _ema);
const mySellCondition = for_every(myCrossunder, close, myEma18, (_cross, _close, _ema) => _cross && _close < _ema);

// Simulate the "one trade at a time" state machine from the Pine strategy.
// This requires sequential state (position_size), so a plain loop is used here
// (no indicator functions are called inside this loop, only array reads).
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myBuyExit = series_of(false);
const mySellExit = series_of(false);

let myPositionState = 0; // 0 = flat, 1 = long, -1 = short

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNoPosition = myPositionState === 0;

	if (myBuyCondition[myIndex] && myNoPosition) {
		myBuySignal[myIndex] = true;
		myPositionState = 1;
	}
	else if (mySellCondition[myIndex] && myNoPosition) {
		mySellSignal[myIndex] = true;
		myPositionState = -1;
	}

	if (myPositionState > 0 && (close[myIndex] < mySmaLow[myIndex] || myCrossunder[myIndex])) {
		myBuyExit[myIndex] = true;
		myPositionState = 0;
	}
	else if (myPositionState < 0 && (close[myIndex] > mySmaHigh[myIndex] || myCrossover[myIndex])) {
		mySellExit[myIndex] = true;
		myPositionState = 0;
	}
}

// Visual markers for BUY/SELL entries, placed below/above the bars like plotshape
const myBuyMarks = for_every(close, (_c, _p, _index) => myBuySignal[_index] ? constants.icons.triangle_up : null);
const mySellMarks = for_every(close, (_c, _p, _index) => mySellSignal[_index] ? constants.icons.triangle_down : null);

paint(myMacdLine, { name: 'MACD Line', color: '#4DA3FF', thickness: 2 });
paint(mySignalLine, { name: 'Signal Line', color: '#EF5350', thickness: 1 });
paint(myBuyMarks, { name: 'Buy Marks', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell Marks', style: 'labels_above', color: 'red' });

// Signals available for scanners, alerts and strategy tester
register_signal(myBuySignal, 'Buy Entry');
register_signal(mySellSignal, 'Sell Entry');
register_signal(myBuyExit, 'Buy Exit');
register_signal(mySellExit, 'Sell Exit');