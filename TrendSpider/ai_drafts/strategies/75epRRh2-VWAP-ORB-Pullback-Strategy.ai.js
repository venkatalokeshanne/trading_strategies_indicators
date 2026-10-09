describe_indicator('VWAP ORB Pullback Strategy', 'price');

// === INPUTS ===
const myOrMinutes = input.number('Opening Range Minutes', 15, { min: 1, max: 120 });
const myRiskReward = input.number('Risk Reward Ratio', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myUseVwapFilter = input.boolean('Use VWAP Filter', true);

// === SESSION / DAY BOUNDARIES ===
// Identify which trading session (day) each candle belongs to
const mySessionIds = time.map(_t => bar_at(_t).session);
const myDayChanged = mySessionIds.map((_s, _i) => _i === 0 ? true : _s !== mySessionIds[_i - 1]);

// Session open time (hh:mm), used as the opening range anchor
const mySessionStartMinutes = current.session.start.hours * 60 + current.session.start.minutes;

// Minutes-since-midnight for every candle (exchange timezone)
const myMinutesOfDay = time.map(_t => {
	const myParsed = time_of(_t);
	return myParsed.hours * 60 + myParsed.minutes;
});

const myInOrWindow = myMinutesOfDay.map(_m => _m >= mySessionStartMinutes && _m <= mySessionStartMinutes + myOrMinutes);
const myAfterOrWindow = myMinutesOfDay.map(_m => _m > mySessionStartMinutes + myOrMinutes);

// === OPENING RANGE HIGH / LOW (reset every new day) ===
const myOrHigh = series_of(null);
const myOrLow = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myDayChanged[myIndex]) {
		myOrHigh[myIndex] = null;
		myOrLow[myIndex] = null;
	}
	else {
		myOrHigh[myIndex] = myOrHigh[myIndex - 1];
		myOrLow[myIndex] = myOrLow[myIndex - 1];
	}

	if (myInOrWindow[myIndex]) {
		myOrHigh[myIndex] = myOrHigh[myIndex] === null || myOrHigh[myIndex] === undefined ? high[myIndex] : Math.max(myOrHigh[myIndex], high[myIndex]);
		myOrLow[myIndex] = myOrLow[myIndex] === null || myOrLow[myIndex] === undefined ? low[myIndex] : Math.min(myOrLow[myIndex], low[myIndex]);
	}
}

// === SESSION ANCHORED VWAP (reset every new day) ===
const myDayChangedFlag = myDayChanged.map(_f => _f ? 1 : 0);
const myCumPV = for_every(hlc3, volume, myDayChangedFlag, (_tp, _v, _changed, _prev, _idx) => {
	const myPV = _tp * _v;
	return _changed === 1 ? myPV : _prev + myPV;
});
const myCumVol = for_every(volume, myDayChangedFlag, (_v, _changed, _prev) => _changed === 1 ? _v : _prev + _v);
const myVwap = div(myCumPV, myCumVol);

// === EMA (pullback confirmation) and ATR (risk management) ===
const myEma9 = ema(close, 9);
const myAtr14 = atr(high, low, close, 14);

// === CONDITIONS ===
const myBreakoutLong = for_every(close, myOrHigh, (_c, _oh) => _oh !== null && _oh !== undefined && _c > _oh);
const myPullbackLong = for_every(close, myVwap, myEma9, low, (_c, _vw, _ema, _lo) => {
	const myVwapOk = myUseVwapFilter ? (_c > _vw && _lo <= _vw) : true;
	return myVwapOk && _c > _ema;
});
const myLongCondition = for_every(myBreakoutLong, myPullbackLong, myAfterOrWindow.map(_v => _v ? 1 : 0), (_bo, _pb, _after) => _bo && _pb && _after === 1);

const myBreakoutShort = for_every(close, myOrLow, (_c, _ol) => _ol !== null && _ol !== undefined && _c < _ol);
const myPullbackShort = for_every(close, myVwap, myEma9, high, (_c, _vw, _ema, _hi) => {
	const myVwapOk = myUseVwapFilter ? (_c < _vw && _hi >= _vw) : true;
	return myVwapOk && _c < _ema;
});
const myShortCondition = for_every(myBreakoutShort, myPullbackShort, myAfterOrWindow.map(_v => _v ? 1 : 0), (_bo, _pb, _after) => _bo && _pb && _after === 1);

// === RISK LEVELS (stop/target, informational only) ===
const myLongStop = sub(close, myAtr14);
const myLongTarget = add(close, mult(myAtr14, myRiskReward));
const myShortStop = add(close, myAtr14);
const myShortTarget = sub(close, mult(myAtr14, myRiskReward));

// === PAINTING ===
paint(myOrHigh, { name: 'OR High', color: '#2ca599', style: 'ladder', thickness: 1 });
paint(myOrLow, { name: 'OR Low', color: '#ee5451', style: 'ladder', thickness: 1 });
paint(myVwap, { name: 'VWAP', color: '#ff9800', thickness: 1 });
paint(myEma9, { name: 'EMA9', color: '#8e44ad', thickness: 1 });

const myLongMarks = for_every(myLongCondition, low, (_l, _lo) => _l ? _lo : null);
const myShortMarks = for_every(myShortCondition, high, (_s, _hi) => _s ? _hi : null);

paint(myLongMarks, { name: 'LongSignal', style: 'labels_below', color: '#2ca599', thickness: 2 });
paint(myShortMarks, { name: 'ShortSignal', style: 'labels_above', color: '#ee5451', thickness: 2 });

// === SIGNALS (for scanners, alerts, strategy tester) ===
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');