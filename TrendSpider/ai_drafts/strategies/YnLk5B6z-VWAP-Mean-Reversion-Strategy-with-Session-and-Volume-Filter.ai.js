describe_indicator('VWAP Mean Reversion Session Filter', 'price');

// ── INPUTS ─────────────────────────────────────────────
const myEntryTab = input.tab('Entry');
const myAtrLen = myEntryTab.number('ATR Length', 14, { min: 1, max: 200 });
const myVwapDist = myEntryTab.number('VWAP Distance (ATR mult)', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myVolLen = myEntryTab.number('Volume MA Length', 20, { min: 1, max: 200 });

const myRiskTab = input.tab('Risk');
const mySlMult = myRiskTab.number('Stop ATR Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });

const mySessionTab = input.tab('Session');
const mySessionRow1 = mySessionTab.row();
const myStartHour = mySessionRow1.number('Session Start Hour (ET)', 9, { min: 0, max: 23 });
const myStartMin = mySessionRow1.number('Session Start Min (ET)', 45, { min: 0, max: 59 });
const mySessionRow2 = mySessionTab.row();
const myEndHour = mySessionRow2.number('Session End Hour (ET)', 15, { min: 0, max: 23 });
const myEndMin = mySessionRow2.number('Session End Min (ET)', 15, { min: 0, max: 59 });

// ── SESSION DAY VWAP (resets every trading day) ─────────
// Pine's ta.vwap(hlc3) resets at the start of each session day.
// We reproduce this by accumulating typical_price*volume and volume
// since the first candle of each day, using the exchange session id.
const mySessionAtCandle = time.map(_t => bar_at(_t).session);
const myVwapVal = series_of(null);
let myCumPV = 0;
let myCumV = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewDay = myIndex === 0 || mySessionAtCandle[myIndex] !== mySessionAtCandle[myIndex - 1];
	if (myNewDay) {
		myCumPV = 0;
		myCumV = 0;
	}
	myCumPV += hlc3[myIndex] * volume[myIndex];
	myCumV += volume[myIndex];
	myVwapVal[myIndex] = myCumV !== 0 ? myCumPV / myCumV : hlc3[myIndex];
}

// ── INDICATORS ──────────────────────────────────────────
const myAtrVal = atr(high, low, close, myAtrLen);
const myVolAvg = sma(volume, myVolLen);
const myVolWeak = for_every(volume, myVolAvg, (_v, _va) => _v < _va);

// ── DISTANCE FROM VWAP ──────────────────────────────────
const myUpperThreshold = add(myVwapVal, mult(myAtrVal, myVwapDist));
const myLowerThreshold = sub(myVwapVal, mult(myAtrVal, myVwapDist));
const myAboveVwap = for_every(close, myUpperThreshold, (_c, _u) => _c > _u);
const myBelowVwap = for_every(close, myLowerThreshold, (_c, _l) => _c < _l);

// ── SESSION FILTER ───────────────────────────────────────
// Uses exchange timezone (assumed to match America/New_York per the
// original Pine script's explicit timestamp() calls).
const myInSession = time.map(_t => {
	const myParts = time_of(_t);
	const myMinutesOfDay = myParts.hours * 60 + myParts.minutes;
	const myStartMinutesOfDay = myStartHour * 60 + myStartMin;
	const myEndMinutesOfDay = myEndHour * 60 + myEndMin;
	return myMinutesOfDay >= myStartMinutesOfDay && myMinutesOfDay < myEndMinutesOfDay;
});

// ── ENTRY CONDITIONS ────────────────────────────────────
// NOTE: Pine's "strategy.position_size == 0" and "barstate.isconfirmed"
// have no equivalent in this engine (no built-in position/strategy
// state tracking and no notion of "unconfirmed realtime bar" math
// here), so those two filters are omitted. Signals below mark EVERY
// bar meeting the price/volume/session conditions, not just "flat"
// entries, which can produce more frequent signals than the Pine
// strategy backtest.
const myLongCond = series_of(null);
const myShortCond = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myLongCond[myIndex] = myBelowVwap[myIndex] && myVolWeak[myIndex] && myInSession[myIndex];
	myShortCond[myIndex] = myAboveVwap[myIndex] && myVolWeak[myIndex] && myInSession[myIndex];
}

// ── VISUALS ─────────────────────────────────────────────
paint(myVwapVal, { name: 'VWAP', color: '#2962ff', thickness: 2 });
paint(myUpperThreshold, { name: 'Upper Threshold', color: '#ef5350', style: 'dotted' });
paint(myLowerThreshold, { name: 'Lower Threshold', color: '#26a69a', style: 'dotted' });

const myLongMarks = for_every(myLongCond, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCond, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'Mean Reversion Long', style: 'labels_below', color: '#26a69a' });
paint(myShortMarks, { name: 'Mean Reversion Short', style: 'labels_above', color: '#ef5350' });

// ── SCANNER / ALERT / STRATEGY SIGNALS ──────────────────
register_signal(myLongCond, 'VWAP Mean Reversion Long');
register_signal(myShortCond, 'VWAP Mean Reversion Short');

// Stop/limit reference levels, exposed for strategy backtest/alert use
register_signal(for_every(close, myAtrVal, (_c, _a) => _c - _a * mySlMult), 'Long Stop Level');
register_signal(myVwapVal, 'Long Target Level (VWAP)');
register_signal(for_every(close, myAtrVal, (_c, _a) => _c + _a * mySlMult), 'Short Stop Level');