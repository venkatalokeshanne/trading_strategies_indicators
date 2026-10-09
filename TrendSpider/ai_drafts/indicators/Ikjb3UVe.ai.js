describe_indicator('CCI Mavi Sari Kesisim Tarama', 'lower');

// CCI length and signal MA length, matching Pine inputs (hardcoded in original script)
const myCciLength = input.number('CCI Length', 20, { min: 1, max: 200 });
const mySignalLength = input.number('Signal SMA Length', 9, { min: 1, max: 200 });

// NOTE: Pine's ta.cci(close, 20) uses "close" as its source series directly
// (not hlc3), so we replicate that exactly using the built-in cci() function
// with "close" as the price source.
const myCciValue = cci(close, myCciLength);
const mySignalLine = sma(myCciValue, mySignalLength);

// Crossover / Crossunder detection, replicating Pine's ta.crossover/ta.crossunder
const myPrevCci = shift(myCciValue, 1);
const myPrevSignal = shift(mySignalLine, 1);

const myBuySignal = for_every(myCciValue, mySignalLine, myPrevCci, myPrevSignal,
	(_cci, _signal, _prevCci, _prevSignal) => _prevCci <= _prevSignal && _cci > _signal
);

const mySellSignal = for_every(myCciValue, mySignalLine, myPrevCci, myPrevSignal,
	(_cci, _signal, _prevCci, _prevSignal) => _prevCci >= _prevSignal && _cci < _signal
);

// Reference levels
paint(horizontal_line(100), { name: 'Overbought', color: 'gray', style: 'dotted' });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray', style: 'dotted' });
paint(horizontal_line(-100), { name: 'Oversold', color: 'gray', style: 'dotted' });

// Main lines
paint(myCciValue, { name: 'CCI', color: '#2962FF', thickness: 2 });
paint(mySignalLine, { name: 'Signal', color: '#FFD600', thickness: 2 });

// Candle coloring to replicate bgcolor() behavior from Pine
const myCandleColors = for_every(myBuySignal, mySellSignal, (_buy, _sell) => {
	if (_buy) return 'rgba(0,200,83,0.25)';
	if (_sell) return 'rgba(255,23,68,0.25)';
	return null;
});
color_candles(myCandleColors);

// Signals for scanners, alerts and strategies
register_signal(myBuySignal, 'Buy Signal (CCI crosses above Signal)');
register_signal(mySellSignal, 'Sell Signal (CCI crosses below Signal)');