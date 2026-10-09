describe_indicator('MACD Pro Relational Contrast', 'lower', { decimals: 2 });

// --- Inputs ---
const myFastLength = input.number('Fast Length', 12, { min: 1, max: 500 });
const mySlowLength = input.number('Slow Length', 26, { min: 1, max: 500 });
const mySource = input.select('Source', 'close', constants.price_source_options);
const mySignalLength = input.number('Signal Smoothing', 9, { min: 1, max: 500 });
const myOscType = input.select('Oscillator Type', 'EMA', ['EMA', 'SMA']);
const mySignalType = input.select('Signal Line Type', 'EMA', ['EMA', 'SMA']);

const myPrice = market[mySource];

// --- Calculations ---
const myFastMA = myOscType === 'EMA' ? ema(myPrice, myFastLength) : sma(myPrice, myFastLength);
const mySlowMA = myOscType === 'EMA' ? ema(myPrice, mySlowLength) : sma(myPrice, mySlowLength);
const myMacdLine = sub(myFastMA, mySlowMA);
const mySignalLine = mySignalType === 'EMA' ? ema(myMacdLine, mySignalLength) : sma(myMacdLine, mySignalLength);
const myHistogram = sub(myMacdLine, mySignalLine);

// --- Histogram 4-color palette (rising/falling vs sign) ---
const myHistColor = for_every(myHistogram, (_hist, _prev, _index) => {
	const myPrevHist = _index > 0 ? myHistogram[_index - 1] : _hist;
	if (_hist >= 0) {
		return _hist > myPrevHist ? '#26A69A' : '#B2DFDB';
	}
	else {
		return _hist < myPrevHist ? '#EF5350' : '#FFCDD2';
	}
});

// --- MACD line relational color (above/below signal) ---
const myMacdColor = for_every(myMacdLine, mySignalLine, (_macd, _signal) => _macd > _signal ? '#0055FF' : '#FFFFFF');

// --- Signal line color (rising vs falling) ---
const mySignalColor = for_every(mySignalLine, (_signal, _prev, _index) => {
	const myPrevSignal = _index > 0 ? mySignalLine[_index - 1] : _signal;
	return _signal > myPrevSignal ? '#00FF66' : '#FF1744';
});

// Zero line reference
paint(horizontal_line(0), { name: 'Zero Line', color: '#FFD700', style: 'line', thickness: 1 });

// Histogram
paint(myHistogram, { name: 'Histogram', color: myHistColor, style: 'column', thickness: 1 });

// MACD main line
paint(myMacdLine, { name: 'MACD Main Line', color: myMacdColor, thickness: 2 });

// Signal line
paint(mySignalLine, { name: 'Signal Line', color: mySignalColor, thickness: 3 });

// --- Signals for scanner, alerts and strategy tester ---
const myMacdAboveSignal = for_every(myMacdLine, mySignalLine, (_macd, _signal) => _macd > _signal);
register_signal(myMacdAboveSignal, 'MACD Above Signal');

const myMacdCrossUp = for_every(myMacdLine, mySignalLine, (_macd, _signal, _prev, _index) => {
	if (_index === 0) return false;
	return _macd > _signal && myMacdLine[_index - 1] <= mySignalLine[_index - 1];
});
register_signal(myMacdCrossUp, 'MACD Cross Up Signal');

const myMacdCrossDown = for_every(myMacdLine, mySignalLine, (_macd, _signal, _prev, _index) => {
	if (_index === 0) return false;
	return _macd < _signal && myMacdLine[_index - 1] >= mySignalLine[_index - 1];
});
register_signal(myMacdCrossDown, 'MACD Cross Down Signal');

const myHistogramPositive = for_every(myHistogram, _hist => _hist >= 0);
register_signal(myHistogramPositive, 'Histogram Positive');

const mySignalRising = for_every(mySignalLine, (_signal, _prev, _index) => {
	if (_index === 0) return false;
	return _signal > mySignalLine[_index - 1];
});
register_signal(mySignalRising, 'Signal Line Rising');