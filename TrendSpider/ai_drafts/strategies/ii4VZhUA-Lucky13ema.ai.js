describe_indicator('Lucky13ema Filtered v2', 'price');

// Inputs
const myUseFilters = input.boolean('Use Filters', true);
const myVolMult = input.number('Volume Multiplier', 1.2, { min: 0.1, max: 10, step: 0.1 });
const myEmaLength = input.number('EMA Length', 13, { min: 1, max: 500 });
const myUseVwapCross = input.boolean('Require VWAP Cross for Entries', false);

// Indicators
const myEma13 = ema(close, myEmaLength);
const myVwapValue = vwap();

paint(myEma13, { name: 'EMA13', color: '#2962FF', thickness: 2 });
paint(myVwapValue, { name: 'VWAP', color: '#9C27B0', thickness: 1, forceUsePriceAxis: true });

// Base conditions
const myIsGreen = for_every(close, open, (_c, _o) => _c > _o);
const myIsRed = for_every(close, open, (_c, _o) => _c < _o);

const myPrevBelow = for_every(close, myEma13, (_c, _e, _p, _i) => _i > 0 ? close[_i - 1] <= myEma13[_i - 1] : false);
const myPrevAbove = for_every(close, myEma13, (_c, _e, _p, _i) => _i > 0 ? close[_i - 1] >= myEma13[_i - 1] : false);

const myBuyCondition = for_every(myIsGreen, close, myEma13, myPrevBelow, (_g, _c, _e, _pb) => _g && _c > _e && _pb);
const mySellCondition = for_every(myIsRed, close, myEma13, myPrevAbove, (_r, _c, _e, _pa) => _r && _c < _e && _pa);

// Filters
const myVolSma = sma(volume, 20);
const myVolOk = for_every(volume, myVolSma, (_v, _s) => _v > _s * myVolMult);

const myVwapLongOk = for_every(close, myVwapValue, (_c, _vw) => !myUseFilters || _c > _vw);
const myVwapShortOk = for_every(close, myVwapValue, (_c, _vw) => !myUseFilters || _c < _vw);

// crossover / crossunder of close vs vwap
const myLongVwapCross = for_every(close, myVwapValue, (_c, _vw, _p, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevVwap = myVwapValue[_i - 1];
	return myPrevClose <= myPrevVwap && _c > _vw;
});

const myShortVwapCross = for_every(close, myVwapValue, (_c, _vw, _p, _i) => {
	if (_i === 0) return false;
	const myPrevClose = close[_i - 1];
	const myPrevVwap = myVwapValue[_i - 1];
	return myPrevClose >= myPrevVwap && _c < _vw;
});

// Final signals
const myBuySignal = for_every(myBuyCondition, myVolOk, myUseVwapCross ? myLongVwapCross : myVwapLongOk, (_bc, _vo, _vc) => _bc && _vo && _vc);
const mySellSignal = for_every(mySellCondition, myVolOk, myUseVwapCross ? myShortVwapCross : myVwapShortOk, (_sc, _vo, _vc) => _sc && _vo && _vc);

const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// Signals for scanners/alerts/strategy tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');