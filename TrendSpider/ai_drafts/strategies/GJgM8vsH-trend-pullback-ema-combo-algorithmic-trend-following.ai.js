describe_indicator('Trend Pullback EMA50 EMA200', 'price');

// EMA 50 and EMA 200, standard trend filter lines
const myEma50 = ema(close, 50);
const myEma200 = ema(close, 200);

paint(myEma50, { name: 'EMA50', color: '#2962ff', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#ef5350', thickness: 2 });

// WaveTrend (VuManChu-style) calculation
const myWtLength = 9;
const myWtAvg = 12;

const myEsa = ema(close, myWtLength);
const myAbsDiff = for_every(close, myEsa, (_c, _e) => Math.abs(_c - _e));
const myD = ema(myAbsDiff, myWtLength);
const myCi = for_every(close, myEsa, myD, (_c, _e, _d) => (_c - _e) / (0.015 * _d));
const myWt1 = ema(myCi, myWtAvg);
const myWt2 = sma(myWt1, 3);

// Crossover: wt1 crosses above wt2
const myCrossover = for_every(myWt1, myWt2, (_wt1, _wt2, _prev, _index) => {
	if (_index === 0) return false;
	return myWt1[_index - 1] <= myWt2[_index - 1] && _wt1 > _wt2;
});

// Crossunder: wt1 crosses below wt2
const myCrossunder = for_every(myWt1, myWt2, (_wt1, _wt2, _prev, _index) => {
	if (_index === 0) return false;
	return myWt1[_index - 1] >= myWt2[_index - 1] && _wt1 < _wt2;
});

// Pullback conditions from the Pine strategy
const myLongCondition = for_every(close, myEma50, myEma200, myCrossover, (_c, _e50, _e200, _cross) => {
	return _c > _e200 && _c < _e50 && _cross;
});

const myShortCondition = for_every(close, myEma50, myEma200, myCrossunder, (_c, _e50, _e200, _cross) => {
	return _c < _e200 && _c > _e50 && _cross;
});

// Signals usable in Scanners, Alerts and Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');