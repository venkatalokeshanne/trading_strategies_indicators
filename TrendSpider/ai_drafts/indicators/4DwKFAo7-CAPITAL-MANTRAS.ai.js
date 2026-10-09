describe_indicator('Institutional MACD Zone Crossover Strategy', 'lower');

// Input parameters, matching the Pine Script inputs
const myFastLength = input.number('MACD Fast Length (EMA)', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow Length (EMA)', 26, { min: 1, max: 200 });
const mySignalLength = input.number('MACD Signal Length (EMA)', 9, { min: 1, max: 200 });

// MACD calculation: ta.macd(close, fast, slow, signal) is EMA(fast) - EMA(slow),
// and signal line is EMA of that difference
const myMacdLine = sub(ema(close, myFastLength), ema(close, mySlowLength));
const mySignalLine = ema(myMacdLine, mySignalLength);
const myHistLine = sub(myMacdLine, mySignalLine);

// Volume support filter: volume > SMA(volume, 20)
const myVolSMA = sma(volume, 20);
const myVolumeSupporting = for_every(volume, myVolSMA, (_v, _vsma) => _v > _vsma);

// Crossover / crossunder detection, replicating ta.crossover / ta.crossunder
const myPrevMacd = shift(myMacdLine, 1);
const myPrevSignal = shift(mySignalLine, 1);

const myPositiveCrossover = for_every(
	myMacdLine, mySignalLine, myPrevMacd, myPrevSignal,
	(_macd, _signal, _prevMacd, _prevSignal) => {
		const myCrossover = _prevMacd <= _prevSignal && _macd > _signal;
		return myCrossover && _macd > 0;
	}
);

const myNegativeCrossunder = for_every(
	myMacdLine, mySignalLine, myPrevMacd, myPrevSignal,
	(_macd, _signal, _prevMacd, _prevSignal) => {
		const myCrossunder = _prevMacd >= _prevSignal && _macd < _signal;
		return myCrossunder && _macd < 0;
	}
);

// Categorize signals into Volume-Supported vs Regular
const myIsVolumeBuy = for_every(myPositiveCrossover, myVolumeSupporting, (_cross, _vol) => _cross && _vol);
const myIsRegularBuy = for_every(myPositiveCrossover, myVolumeSupporting, (_cross, _vol) => _cross && !_vol);

const myIsVolumeSell = for_every(myNegativeCrossunder, myVolumeSupporting, (_cross, _vol) => _cross && _vol);
const myIsRegularSell = for_every(myNegativeCrossunder, myVolumeSupporting, (_cross, _vol) => _cross && !_vol);

// Lines
paint(myMacdLine, { name: 'MACD Line', color: '#2962FF', thickness: 2 });
paint(mySignalLine, { name: 'Signal Line', color: '#FF9800', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray', style: 'dotted' });

// Signal markers, mapped onto the MACD line value for visibility in the lower panel
const myVolumeBuyMarks = for_every(myIsVolumeBuy, myMacdLine, (_sig, _macd) => _sig ? _macd : null);
const myRegularBuyMarks = for_every(myIsRegularBuy, myMacdLine, (_sig, _macd) => _sig ? _macd : null);
const myVolumeSellMarks = for_every(myIsVolumeSell, myMacdLine, (_sig, _macd) => _sig ? _macd : null);
const myRegularSellMarks = for_every(myIsRegularSell, myMacdLine, (_sig, _macd) => _sig ? _macd : null);

paint(myVolumeBuyMarks, { name: 'Volume Buy', style: 'labels_below', color: 'green', thickness: 6 });
paint(myRegularBuyMarks, { name: 'Regular Buy', style: 'labels_below', color: 'lime', thickness: 4 });
paint(myVolumeSellMarks, { name: 'Volume Sell', style: 'labels_above', color: 'maroon', thickness: 6 });
paint(myRegularSellMarks, { name: 'Regular Sell', style: 'labels_above', color: 'red', thickness: 4 });

// Signals for scanners, alerts and strategy tester
register_signal(myIsVolumeBuy, 'Volume Buy Signal');
register_signal(myIsRegularBuy, 'Regular Buy Signal');
register_signal(myIsVolumeSell, 'Volume Sell Signal');
register_signal(myIsRegularSell, 'Regular Sell Signal');