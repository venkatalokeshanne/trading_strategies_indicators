describe_indicator('EMA Cross Plus Triple VWAP Reclaim', 'price');

// --- Inputs ---
const myEma9Len = input.number('Fast EMA (M5)', 9, { min: 1, max: 200 });
const myEma20Len = input.number('Slow EMA (M5)', 20, { min: 1, max: 200 });
const myH1EmaLen = input.number('H1 EMA Filter', 20, { min: 1, max: 200 });
const myAtrLen = input.number('ATR Length (H1)', 14, { min: 1, max: 200 });
const mySlMultiplier = input.number('H1 ATR Multiplier', 0.5, { min: 0.1, max: 10 });
const myRrRatio = input.number('Risk Reward Ratio', 1.0, { min: 0.1, max: 10 });
const myLookback = input.number('VWAP Touch Lookback', 10, { min: 1, max: 200 });

// Helper: computes a session (daily) resetting VWAP using cumulative sums.
// This mirrors Pine's ta.vwap(close), which resets at the start of each
// trading day. The current JS API vwap() function does not auto-reset per
// session, so a manual cumulative implementation is used here instead.
// NOTE: fixed the "new Array(...)" usage below, since the "new" keyword
// is not allowed by the execution engine. Array(n).fill(null) (called
// without "new") achieves the exact same result.
function myComputeSessionVwap(myTimeSeries, myPriceSeries, myVolumeSeries) {
	const myResult = Array(myTimeSeries.length).fill(null);
	let myCumPV = 0;
	let myCumVol = 0;
	let myPrevSession = null;

	for (let myIndex = 0; myIndex < myTimeSeries.length; myIndex += 1) {
		const mySessionId = bar_at(myTimeSeries[myIndex]).session;

		if (mySessionId !== myPrevSession) {
			myCumPV = 0;
			myCumVol = 0;
			myPrevSession = mySessionId;
		}

		myCumPV += myPriceSeries[myIndex] * myVolumeSeries[myIndex];
		myCumVol += myVolumeSeries[myIndex];
		myResult[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : myPriceSeries[myIndex];
	}

	return myResult;
}

// --- M5 (current chart) indicators ---
const myEma9 = ema(close, myEma9Len);
const myEma20 = ema(close, myEma20Len);
const myM5Vwap = myComputeSessionVwap(time, close, volume);

// --- H1 data fetch ---
const myH1Data = await request.history(current.ticker, '60');
assert(!myH1Data.error, 'Error fetching H1 data: ' + myH1Data.error);

const myH1Ema20Raw = ema(myH1Data.close, myH1EmaLen);
const myH1VwapRaw = myComputeSessionVwap(myH1Data.time, myH1Data.close, myH1Data.volume);
const myH1AtrRaw = atr(myH1Data.high, myH1Data.low, myH1Data.close, myAtrLen);

// Land H1 series onto the M5 time axis using 'le' (last H1 bar at or
// before this M5 candle), then fill gaps with constant interpolation
// (prevents forward-looking / repainting behavior, matching request.security
// semantics on a confirmed bar basis).
const myH1CloseLanded = interpolate_sparse_series(
	land_points_onto_series(myH1Data.time, myH1Data.close, time, 'le'),
	'constant'
);
const myH1Ema20Landed = interpolate_sparse_series(
	land_points_onto_series(myH1Data.time, myH1Ema20Raw, time, 'le'),
	'constant'
);
const myH1VwapLanded = interpolate_sparse_series(
	land_points_onto_series(myH1Data.time, myH1VwapRaw, time, 'le'),
	'constant'
);
const myH1AtrLanded = interpolate_sparse_series(
	land_points_onto_series(myH1Data.time, myH1AtrRaw, time, 'le'),
	'constant'
);

// --- VWAP reclaim logic (M5) ---
const myLowestLow = lowest(low, myLookback);
const myHighestHigh = highest(high, myLookback);

const myWasBelowVwap = for_every(myLowestLow, myM5Vwap, (_l, _v) => _l < _v);
const myReclaimedVwapLong = for_every(myWasBelowVwap, close, myM5Vwap, (_wasBelow, _c, _v) => _wasBelow && _c > _v);

const myWasAboveVwap = for_every(myHighestHigh, myM5Vwap, (_h, _v) => _h > _v);
const myReclaimedVwapShort = for_every(myWasAboveVwap, close, myM5Vwap, (_wasAbove, _c, _v) => _wasAbove && _c < _v);

// --- H1 trend filter ---
const myH1BuyOk = for_every(myH1CloseLanded, myH1Ema20Landed, myH1VwapLanded, (_c, _e, _v) => _c > _e && _c > _v);
const myH1SellOk = for_every(myH1CloseLanded, myH1Ema20Landed, myH1VwapLanded, (_c, _e, _v) => _c < _e && _c < _v);

// --- Entry triggers (EMA cross on M5) ---
const myLongTrigger = for_every(myEma9, myEma20, (_fast, _slow, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return _fast > _slow && myEma9[_index - 1] <= myEma20[_index - 1];
});

const myShortTrigger = for_every(myEma9, myEma20, (_fast, _slow, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return _fast < _slow && myEma9[_index - 1] >= myEma20[_index - 1];
});

// --- Final signals ---
const myLongSignal = for_every(myLongTrigger, myH1BuyOk, myReclaimedVwapLong, (_t, _ok, _r) => _t && _ok && _r);
const myShortSignal = for_every(myShortTrigger, myH1SellOk, myReclaimedVwapShort, (_t, _ok, _r) => _t && _ok && _r);

// --- Stop / target distances (for reference, derived from H1 ATR) ---
const mySlDist = mult(myH1AtrLanded, mySlMultiplier);
const myTpDist = mult(mySlDist, myRrRatio);

const myLongStop = for_every(myLongSignal, close, mySlDist, (_s, _c, _d) => _s ? _c - _d : null);
const myLongTarget = for_every(myLongSignal, close, myTpDist, (_s, _c, _d) => _s ? _c + _d : null);
const myShortStop = for_every(myShortSignal, close, mySlDist, (_s, _c, _d) => _s ? _c + _d : null);
const myShortTarget = for_every(myShortSignal, close, myTpDist, (_s, _c, _d) => _s ? _c - _d : null);

// --- Register signals for scanners, alerts and strategy tester ---
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myH1BuyOk, 'H1 Buy Filter OK');
register_signal(myH1SellOk, 'H1 Sell Filter OK');

// --- Visuals ---
paint(myEma9, { name: 'M5 EMA 9', color: '#2962FF', thickness: 2 });
paint(myEma20, { name: 'M5 EMA 20', color: '#FF9800', thickness: 2 });
paint(myM5Vwap, { name: 'M5 VWAP', color: '#9E9E9E', thickness: 2 });
paint(myH1VwapLanded, { name: 'H1 VWAP', color: '#AB47BC', thickness: 1, style: 'dotted' });

// Approximate background highlight zones (bgcolor equivalent) by tinting
// candles instead, since bgcolor() is not available in this API.
const myCandleColors = for_every(myH1BuyOk, myH1SellOk, (_buy, _sell) => {
	if (_buy) {
		return 'rgba(0,200,83,0.25)';
	}
	if (_sell) {
		return 'rgba(255,23,68,0.25)';
	}
	return null;
});
color_candles(myCandleColors);

// Markers for entries (visual reference for signal bars)
const myLongMarks = for_every(myLongSignal, low, (_s, _l) => _s ? _l : null);
const myShortMarks = for_every(myShortSignal, high, (_s, _h) => _s ? _h : null);

paint(myLongMarks, { name: 'Long Entry Marker', style: 'labels_below', color: '#00C853', thickness: 3 });
paint(myShortMarks, { name: 'Short Entry Marker', style: 'labels_above', color: '#FF1744', thickness: 3 });