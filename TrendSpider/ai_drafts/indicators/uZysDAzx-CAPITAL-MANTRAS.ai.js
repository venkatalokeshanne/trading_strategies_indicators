describe_indicator('Institutional MACD Zone Crossover Strategy', 'lower');

// ==========================================
// INPUT PARAMETERS
// ==========================================
const myFastLength = input.number('MACD Fast Length (EMA)', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow Length (EMA)', 26, { min: 1, max: 200 });
const mySignalLength = input.number('MACD Signal Length (EMA)', 9, { min: 1, max: 200 });
const myVolumeSmaLength = input.number('Volume SMA Length', 20, { min: 1, max: 500 });

// ==========================================
// MACD CALCULATION
// ==========================================
const myFastEma = ema(close, myFastLength);
const mySlowEma = ema(close, mySlowLength);
const myMacdLine = sub(myFastEma, mySlowEma);
const mySignalLine = ema(myMacdLine, mySignalLength);

// ==========================================
// VOLUME SUPPORT FILTER
// ==========================================
const myVolSma = sma(volume, myVolumeSmaLength);
const myVolumeSupporting = for_every(volume, myVolSma, (_v, _vs) => _v > _vs);

// ==========================================
// ZONE & CROSSOVER CONDITIONS
// ==========================================
// crossover: macd crosses above signal; crossunder: macd crosses below signal
const myCrossover = for_every(myMacdLine, mySignalLine, (_m, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _m > _s && myMacdLine[_i - 1] <= mySignalLine[_i - 1];
});

const myCrossunder = for_every(myMacdLine, mySignalLine, (_m, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _m < _s && myMacdLine[_i - 1] >= mySignalLine[_i - 1];
});

const myPositiveCrossover = for_every(myCrossover, myMacdLine, (_c, _m) => _c && _m > 0);
const myNegativeCrossunder = for_every(myCrossunder, myMacdLine, (_c, _m) => _c && _m < 0);

const myIsVolumeBuy = for_every(myPositiveCrossover, myVolumeSupporting, (_c, _v) => _c && _v);
const myIsRegularBuy = for_every(myPositiveCrossover, myVolumeSupporting, (_c, _v) => _c && !_v);

const myIsVolumeSell = for_every(myNegativeCrossunder, myVolumeSupporting, (_c, _v) => _c && _v);
const myIsRegularSell = for_every(myNegativeCrossunder, myVolumeSupporting, (_c, _v) => _c && !_v);

// ==========================================
// PLOTTING
// ==========================================
const myMacdLinePainted = paint(myMacdLine, { name: 'MACD Line', color: '#2962FF', thickness: 2 });
const mySignalLinePainted = paint(mySignalLine, { name: 'Signal Line', color: '#FF9800', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray', style: 'dotted' });

// Signal markers plotted below the MACD line (labels_below) and above (labels_above)
const myVolumeBuyMarks = for_every(myIsVolumeBuy, myMacdLine, (_c, _m) => _c ? _m : null);
const myRegularBuyMarks = for_every(myIsRegularBuy, myMacdLine, (_c, _m) => _c ? _m : null);
const myVolumeSellMarks = for_every(myIsVolumeSell, myMacdLine, (_c, _m) => _c ? _m : null);
const myRegularSellMarks = for_every(myIsRegularSell, myMacdLine, (_c, _m) => _c ? _m : null);

paint(myVolumeBuyMarks, { name: 'Volume Buy Signal', style: 'labels_below', color: 'green', thickness: 3 });
paint(myRegularBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: 'lime', thickness: 3 });
paint(myVolumeSellMarks, { name: 'Volume Sell Signal', style: 'labels_above', color: 'maroon', thickness: 3 });
paint(myRegularSellMarks, { name: 'Sell Signal', style: 'labels_above', color: 'red', thickness: 3 });

// ==========================================
// SCANNER / ALERT SIGNALS
// ==========================================
register_signal(myIsVolumeBuy, 'Volume BUY');
register_signal(myIsRegularBuy, 'BUY');
register_signal(myIsVolumeSell, 'Volume SELL');
register_signal(myIsRegularSell, 'SELL');