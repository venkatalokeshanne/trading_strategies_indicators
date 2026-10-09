describe_indicator('DMI Dynamic (Pine Port)', 'lower', { decimals: 4 });

// --- Inputs ---
const myAdxLen = input.number('ADX Smoothing', 14, { min: 1 });
const myDiLen = input.number('DI Length', 28, { min: 1 });

// --- True Range (atr with length 1 gives raw TR, since wildma(tr,1) == tr) ---
const myTrueRange = atr(high, low, close, 1);

// --- Directional movement ---
const myUp = sub(high, shift(high, 1));
const myDown = sub(shift(low, 1), low);

const myPlusDM = for_every(myUp, myDown, (_u, _d) => {
	if (_u === null || _d === null) return null;
	return (_u > _d && _u > 0) ? _u : 0;
});

const myMinusDM = for_every(myUp, myDown, (_u, _d) => {
	if (_u === null || _d === null) return null;
	return (_d > _u && _d > 0) ? _d : 0;
});

const myTrur = wildma(myTrueRange, myDiLen);
const myPlusRaw = div(mult(wildma(myPlusDM, myDiLen), 100), myTrur);
const myMinusRaw = div(mult(wildma(myMinusDM, myDiLen), 100), myTrur);

// fixnan: carry forward last valid (non null/NaN) value
const myPlus = for_every(myPlusRaw, (_v, _prev, _i) => {
	const myIsInvalid = _v === null || isNaN(_v);
	if (!myIsInvalid) return _v;
	return _prev === null || _prev === undefined ? 0 : _prev;
});

const myMinus = for_every(myMinusRaw, (_v, _prev, _i) => {
	const myIsInvalid = _v === null || isNaN(_v);
	if (!myIsInvalid) return _v;
	return _prev === null || _prev === undefined ? 0 : _prev;
});

const mySum = add(myPlus, myMinus);
const myDxInput = for_every(myPlus, myMinus, mySum, (_p, _m, _s) => {
	const myDenom = _s === 0 ? 1 : _s;
	return Math.abs(_p - _m) / myDenom;
});

const myAdx = mult(wildma(myDxInput, myAdxLen), 100);

// --- Dynamic colors (current vs previous bar) ---
const myColorPlus = for_every(myPlus, (_v, _prev, _i) => {
	const myPrevVal = _i > 0 ? myPlus[_i - 1] : null;
	return (myPrevVal !== null && _v > myPrevVal) ? '#00ff00' : '#006400';
});

const myColorMinus = for_every(myMinus, (_v, _prev, _i) => {
	const myPrevVal = _i > 0 ? myMinus[_i - 1] : null;
	return (myPrevVal !== null && _v > myPrevVal) ? '#ff0000' : '#800000';
});

const myColorAdx = for_every(myAdx, (_v, _prev, _i) => {
	const myPrevVal = _i > 0 ? myAdx[_i - 1] : null;
	return (myPrevVal !== null && _v > myPrevVal) ? '#ffff00' : 'rgba(255,170,0,0.5)';
});

// --- Plotting ---
paint(myAdx, { name: 'ADXDynamic', color: myColorAdx, thickness: 3, style: 'line' });
paint(myPlus, { name: 'PlusDIDynamic', color: myColorPlus, thickness: 2, style: 'line' });
paint(myMinus, { name: 'MinusDIDynamic', color: myColorMinus, thickness: 2, style: 'line' });

// --- Reference lines ---
paint(horizontal_line(10), { name: 'Threshold10', color: '#00ff2f', style: 'dotted' });
paint(horizontal_line(20), { name: 'Threshold20', color: '#f2fa00', style: 'dotted' });
paint(horizontal_line(30), { name: 'Threshold30', color: '#ffffff', style: 'line' });

// --- Signals for scanners, alerts and strategies ---
const mySignalBullishCross = for_every(myPlus, myMinus, (_p, _m, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevPlus = myPlus[_i - 1];
	const myPrevMinus = myMinus[_i - 1];
	return _p > _m && myPrevPlus <= myPrevMinus;
});

const mySignalBearishCross = for_every(myPlus, myMinus, (_p, _m, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevPlus = myPlus[_i - 1];
	const myPrevMinus = myMinus[_i - 1];
	return _p < _m && myPrevPlus >= myPrevMinus;
});

const mySignalAdxRising = for_every(myAdx, (_v, _prev, _i) => {
	if (_i === 0) return false;
	return _v > myAdx[_i - 1];
});

register_signal(mySignalBullishCross, 'DMI Bullish Cross');
register_signal(mySignalBearishCross, 'DMI Bearish Cross');
register_signal(mySignalAdxRising, 'ADX Rising');