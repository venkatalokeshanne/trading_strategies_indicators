describe_indicator('Institutional MACD Zone Crossover Strategy', 'price');

// Inputs mirroring the Pine Script macro configuration
const myFastLength = input.number('MACD Fast Length (EMA)', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow Length (EMA)', 26, { min: 1, max: 500 });
const mySignalLength = input.number('MACD Signal Length (EMA)', 9, { min: 1, max: 200 });

// MACD calculation: macdLine = EMA(fast) - EMA(slow), signalLine = EMA(macdLine, signalLength)
const myMacdLine = sub(ema(close, myFastLength), ema(close, mySlowLength));
const mySignalLine = ema(myMacdLine, mySignalLength);

// Volume support filter
const myVolSMA = sma(volume, 20);
const myVolumeSupporting = for_every(volume, myVolSMA, (_vol, _volSma) => _vol > _volSma);

// Crossover / crossunder detection (replicates ta.crossover / ta.crossunder)
const myPositiveCrossover = for_every(myMacdLine, mySignalLine, shift(myMacdLine, 1), shift(mySignalLine, 1), (_macd, _signal, _prevMacd, _prevSignal) => {
	const myCrossedOver = _prevMacd <= _prevSignal && _macd > _signal;
	return myCrossedOver && _macd > 0;
});

const myNegativeCrossunder = for_every(myMacdLine, mySignalLine, shift(myMacdLine, 1), shift(mySignalLine, 1), (_macd, _signal, _prevMacd, _prevSignal) => {
	const myCrossedUnder = _prevMacd >= _prevSignal && _macd < _signal;
	return myCrossedUnder && _macd < 0;
});

// Categorize into Volume-Supported vs Regular signals
const myIsVolumeBuy = for_every(myPositiveCrossover, myVolumeSupporting, (_cross, _volSupport) => _cross && _volSupport);
const myIsRegularBuy = for_every(myPositiveCrossover, myVolumeSupporting, (_cross, _volSupport) => _cross && !_volSupport);

const myIsVolumeSell = for_every(myNegativeCrossunder, myVolumeSupporting, (_cross, _volSupport) => _cross && _volSupport);
const myIsRegularSell = for_every(myNegativeCrossunder, myVolumeSupporting, (_cross, _volSupport) => _cross && !_volSupport);

// Build label markers below/above bars (null when no signal, so labels only land on true points)
const myVolumeBuyMarks = for_every(myIsVolumeBuy, low, (_signal, _low) => _signal ? _low : null);
const myRegularBuyMarks = for_every(myIsRegularBuy, low, (_signal, _low) => _signal ? _low : null);
const myVolumeSellMarks = for_every(myIsVolumeSell, high, (_signal, _high) => _signal ? _high : null);
const myRegularSellMarks = for_every(myIsRegularSell, high, (_signal, _high) => _signal ? _high : null);

// Paint signals (colors chosen as closest sharp equivalents of the Pine palette)
paint(myVolumeBuyMarks, { name: 'Volume Buy', style: 'labels_below', color: '#2ecc71' });
paint(myRegularBuyMarks, { name: 'Regular Buy', style: 'labels_below', color: '#90ee90' });
paint(myVolumeSellMarks, { name: 'Volume Sell', style: 'labels_above', color: '#800000' });
paint(myRegularSellMarks, { name: 'Regular Sell', style: 'labels_above', color: '#ff4136' });

// Register signals for scanners, alerts and strategy testing
register_signal(myIsVolumeBuy, 'Volume BUY (VB)');
register_signal(myIsRegularBuy, 'BUY (B)');
register_signal(myIsVolumeSell, 'Volume SELL (VS)');
register_signal(myIsRegularSell, 'SELL (S)');