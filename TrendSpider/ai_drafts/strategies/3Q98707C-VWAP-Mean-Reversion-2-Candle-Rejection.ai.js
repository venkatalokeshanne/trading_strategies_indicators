describe_indicator('VWAP Mean Reversion (2 Candle Rejection)', 'price');

const myMoment = library('moment-timezone');

// --- Session-anchored VWAP (resets every new NY trading day) ---
const mySessionIds = time.map(_t => bar_at(_t).session);

const myCumPV = for_every(close, volume, (_c, _v, _prev, _idx) => {
	const myIsNewSession = _idx === 0 || mySessionIds[_idx] !== mySessionIds[_idx - 1];
	return myIsNewSession ? (_c * _v) : (_prev || 0) + (_c * _v);
});

const myCumV = for_every(volume, (_v, _prev, _idx) => {
	const myIsNewSession = _idx === 0 || mySessionIds[_idx] !== mySessionIds[_idx - 1];
	return myIsNewSession ? _v : (_prev || 0) + _v;
});

const myVwap = div(myCumPV, myCumV);

// --- ATR / EMA ---
const myAtr = atr(high, low, close, 14);
const myEma20 = ema(close, 20);

const myEmaSlope = for_every(myEma20, shift(myEma20, 10), (_e, _ePrev10) => Math.abs(_e - (_ePrev10 ?? _e)));
const myFlatEMA = for_every(myEmaSlope, myAtr, (_slope, _atrVal) => _slope < _atrVal * 0.4);

// --- Session filter (America/New_York, 18:00-02:00) ---
const myHourNYArr = time.map(_t => myMoment.unix(_t).tz('America/New_York').hour());
const mySessionFilterArr = myHourNYArr.map(_h => _h >= 18 || _h <= 2);

// --- Bands and stops ---
const myUpperBand = add(myVwap, mult(myAtr, 2.5));
const myLowerBand = sub(myVwap, mult(myAtr, 2.5));
const myUpperStop = add(myVwap, mult(myAtr, 4));
const myLowerStop = sub(myVwap, mult(myAtr, 4));

// --- 2-candle rejection signals ---
const myPrevLow = shift(low, 1);
const myPrevHigh = shift(high, 1);
const myPrevLowerBand = shift(myLowerBand, 1);
const myPrevUpperBand = shift(myUpperBand, 1);

const myLongReject = for_every(myPrevLow, myPrevLowerBand, low, myLowerBand,
	(_pl, _plb, _l, _lb) => (_pl < _plb) || (_l < _lb));

const myShortReject = for_every(myPrevHigh, myPrevUpperBand, high, myUpperBand,
	(_ph, _pub, _h, _ub) => (_ph > _pub) || (_h > _ub));

const myLongSignalRaw = for_every(myLongReject, close, myLowerBand, (_lr, _c, _lb) => _lr && (_c > _lb));
const myShortSignalRaw = for_every(myShortReject, close, myUpperBand, (_sr, _c, _ub) => _sr && (_c < _ub));

// --- Risk/Reward validation ---
const myRiskLong = sub(close, myLowerStop);
const myRewardLong = sub(myVwap, close);
const myValidLongRR = for_every(myRewardLong, myRiskLong, (_rw, _rk) => _rw >= _rk * 1.5);

const myRiskShort = sub(myUpperStop, close);
const myRewardShort = sub(close, myVwap);
const myValidShortRR = for_every(myRewardShort, myRiskShort, (_rw, _rk) => _rw >= _rk * 1.5);

// --- Final signals ---
const myLongSignal = for_every(myLongSignalRaw, myValidLongRR, myFlatEMA, (_ls, _vr, _flat, _prev, _idx) =>
	Boolean(_ls && _vr && mySessionFilterArr[_idx] && _flat));

const myShortSignal = for_every(myShortSignalRaw, myValidShortRR, myFlatEMA, (_ss, _vr, _flat, _prev, _idx) =>
	Boolean(_ss && _vr && mySessionFilterArr[_idx] && _flat));

register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');

// --- Plot lines ---
paint(myVwap, { name: 'VWAP', color: '#FF9800', thickness: 2 });
paint(myUpperBand, { name: 'Upper Band', color: '#EF5350' });
paint(myLowerBand, { name: 'Lower Band', color: '#26A69A' });
paint(myUpperStop, { name: 'Upper Stop', color: '#9C27B0' });
paint(myLowerStop, { name: 'Lower Stop', color: '#9C27B0' });

// --- Signal markers ---
const myLongMarks = for_every(myLongSignal, low, (_sig, _l) => _sig ? _l : null);
const myShortMarks = for_every(myShortSignal, high, (_sig, _h) => _sig ? _h : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'Short Entry', style: 'labels_above', color: '#EF5350' });