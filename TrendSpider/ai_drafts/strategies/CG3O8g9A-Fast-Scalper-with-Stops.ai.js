describe_indicator('VWAP Mean Reversion Scalper', 'price');

// ─── Inputs ──────────────────────────────────────────────────────
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAdxLength = input.number('ADX DI Length', 14, { min: 1, max: 200 });
const myAdxThresh = input.number('ADX Ranging Threshold', 25, { min: 1, max: 100 });
const myRsiLongTh = input.number('RSI Long Threshold', 40, { min: 1, max: 99 });
const myRsiShortTh = input.number('RSI Short Threshold', 60, { min: 1, max: 99 });
const myStopMult = input.number('Stop x ATR', 1.0, { min: 0.1, max: 20 });
const myTargetMult = input.number('Target x ATR', 3.0, { min: 0.1, max: 20 });
const myTrailActMult = input.number('Trail Activation x ATR', 2.0, { min: 0.1, max: 20 });
const myTrailOffMult = input.number('Trail Offset x ATR', 1.2, { min: 0.1, max: 20 });

// ─── Manual session-anchored VWAP (resets every new trading day) ───
// Built-in vwap() can't be called inside a loop with varying anchor
// points, so the running sums are computed manually instead.
const mySessionIds = time.map(_t => bar_at(_t).session);
const myVwap = series_of(null);
let myCumPV = 0;
let myCumVol = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myIsNewSession = myIndex === 0 || mySessionIds[myIndex] !== mySessionIds[myIndex - 1];
	if (myIsNewSession) {
		myCumPV = 0;
		myCumVol = 0;
	}
	const myTypicalPrice = ohlc4[myIndex];
	myCumPV += myTypicalPrice * volume[myIndex];
	myCumVol += volume[myIndex];
	myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : null;
}

// ─── Core indicators ─────────────────────────────────────────────
const myRsi = rsi(close, myRsiLength);
const myAtr = atr(high, low, close, myAtrLength);

// NOTE: Pine's ta.dmi() lets DI length and ADX smoothing length differ.
// The built-in indicators.adx() only accepts a single period, used for
// both, so ADX smoothing is approximated using the DI length.
const myAdxObject = indicators.adx(myAdxLength);
const myAdx = myAdxObject.adx;

const myIsRanging = for_every(myAdx, _a => _a < myAdxThresh);

const myLongSetup = for_every(close, myVwap, myRsi, myIsRanging, (_c, _v, _r, _ranging) =>
	_c < _v && _r < myRsiLongTh && _ranging
);

const myShortSetup = for_every(close, myVwap, myRsi, myIsRanging, (_c, _v, _r, _ranging) =>
	_c > _v && _r > myRsiShortTh && _ranging
);

// Only fire a signal when there's no open position (flat-to-entry
// transition), mimicking strategy.position_size == 0 in Pine.
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
let myPositionState = 0; // 0 flat, 1 long, -1 short

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPositionState === 0 && myLongSetup[myIndex]) {
		myLongSignal[myIndex] = true;
		myPositionState = 1;
	}
	else if (myPositionState === 0 && myShortSetup[myIndex]) {
		myShortSignal[myIndex] = true;
		myPositionState = -1;
	}
	else {
		// Position management (stop / target / trailing exit) can't be
		// simulated here: Custom JS indicators have no trade/position
		// engine like strategy.*. Position is reset every bar so new
		// setups keep being detected (approximation only).
		myPositionState = 0;
	}
}

// ─── Painting ────────────────────────────────────────────────────
paint(myVwap, { name: 'VWAP', color: 'orange', thickness: 2 });

const myLongMarks = for_every(myLongSignal, low, (_sig, _l) => _sig ? _l : null);
const myShortMarks = for_every(myShortSignal, high, (_sig, _h) => _sig ? _h : null);

paint(myLongMarks, { name: 'LongSetup', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'ShortSetup', style: 'labels_above', color: '#EF5350' });

// ─── Signals for scanner, alerts, strategy tester ──────────────────
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myIsRanging, 'Is Ranging ADX');