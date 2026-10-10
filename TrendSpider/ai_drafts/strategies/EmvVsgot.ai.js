describe_indicator('MACD Crossover Strategy Long Short', 'lower');

// ── MACD Settings ──
const macdTab = input.tab('MACD');
const myPriceSource = macdTab.select('Price source', 'close', constants.price_source_options);
const myFastLen = macdTab.number('Fast Length', 12, { min: 1, max: 500 });
const mySlowLen = macdTab.number('Slow Length', 26, { min: 1, max: 500 });
const mySigLen = macdTab.number('Signal Length', 9, { min: 1, max: 500 });
const myOscType = macdTab.select('Oscillator MA Type', 'EMA', ['EMA', 'SMA']);
const mySigType = macdTab.select('Signal MA Type', 'EMA', ['EMA', 'SMA']);

// ── Strategy Settings ──
// NOTE: Custom JS indicators cannot place real orders, manage positions,
// apply commission/slippage or run a backtest engine like Pine's
// strategy() does. This script reproduces the MACD math and signal
// logic exactly, and exposes the Long/Short signals via register_signal()
// so they can be used in TrendSpider Scanners, Alerts and Strategy Tester.
const strategyTab = input.tab('Strategy');
const myEntryCondition = strategyTab.select('Entry Condition', 'MACDxSignal', ['MACDxSignal', 'HistCross0']);
const myEnableLong = strategyTab.boolean('Enable Long', true);
const myEnableShort = strategyTab.boolean('Enable Short', true);

const myPrice = market[myPriceSource];

function myComputeMA(mySeries, myLength, myType) {
	return myType === 'EMA' ? ema(mySeries, myLength) : sma(mySeries, myLength);
}

const myMaFast = myComputeMA(myPrice, myFastLen, myOscType);
const myMaSlow = myComputeMA(myPrice, mySlowLen, myOscType);
const myMacd = sub(myMaFast, myMaSlow);
const mySignal = myComputeMA(myMacd, mySigLen, mySigType);
const myHist = sub(myMacd, mySignal);

// ── Histogram coloring: rising/falling, above/below zero ──
const myHistColor = for_every(myHist, (_hist, _prev, _index) => {
	const myPrevHist = _index > 0 ? myHist[_index - 1] : _hist;
	if (_hist >= 0) {
		return _hist > myPrevHist ? '#26a69a' : '#b2dfdb';
	}
	else {
		return _hist > myPrevHist ? '#ffcdd2' : '#ff5252';
	}
});

// ── Crossover / Crossunder helpers ──
function myCrossover(mySeriesA, mySeriesB) {
	return for_every(mySeriesA, mySeriesB, (_a, _b, _prev, _index) => {
		if (_index === 0) return false;
		const myPrevA = mySeriesA[_index - 1];
		const myPrevB = mySeriesB[_index - 1];
		return myPrevA <= myPrevB && _a > _b;
	});
}

function myCrossunder(mySeriesA, mySeriesB) {
	return for_every(mySeriesA, mySeriesB, (_a, _b, _prev, _index) => {
		if (_index === 0) return false;
		const myPrevA = mySeriesA[_index - 1];
		const myPrevB = mySeriesB[_index - 1];
		return myPrevA >= myPrevB && _a < _b;
	});
}

const myZeroLine = series_of(0);

const myLongSignalRaw = myEntryCondition === 'MACDxSignal' ? myCrossover(myMacd, mySignal) : myCrossover(myHist, myZeroLine);
const myShortSignalRaw = myEntryCondition === 'MACDxSignal' ? myCrossunder(myMacd, mySignal) : myCrossunder(myHist, myZeroLine);

const myLongSignal = for_every(myLongSignalRaw, _s => myEnableLong && _s);
const myShortSignal = for_every(myShortSignalRaw, _s => myEnableShort && _s);

// ── Plots ──
paint(horizontal_line(0), { name: 'Zero', color: '#787b86', style: 'dotted' });
paint(myHist, { name: 'Histogram', color: myHistColor, style: 'column' });
paint(myMacd, { name: 'MACD', color: 'blue' });
paint(mySignal, { name: 'SignalLine', color: '#ff6d00' });

// ── Signal markers ──
const myLongMarks = for_every(myLongSignal, _s => _s ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'LongSignal', color: 'green', style: 'labels_below' });
paint(myShortMarks, { name: 'ShortSignal', color: 'red', style: 'labels_above' });

// ── Signals for Scanners / Alerts / Strategy Tester ──
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');

const myHistFalling = for_every(myHist, (_hist, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevHist = myHist[_index - 1];
	return myPrevHist >= 0 && _hist < 0;
});

const myHistRising = for_every(myHist, (_hist, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevHist = myHist[_index - 1];
	return myPrevHist <= 0 && _hist > 0;
});

register_signal(myHistFalling, 'Hist Falling');
register_signal(myHistRising, 'Hist Rising');