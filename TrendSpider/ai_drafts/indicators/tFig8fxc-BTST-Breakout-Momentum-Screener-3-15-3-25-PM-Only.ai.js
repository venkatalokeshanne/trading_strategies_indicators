describe_indicator('BTST Breakout and Momentum Screener', 'price');

// NOTE: this is a line by line port of the Pine Script logic. A few pieces
// of Pine's engine (ta.vwap anchored per session, time() with explicit
// timezone, table.new/table.cell) do not exist in TrendSpider's Custom JS
// API, so they are reproduced manually below. See the flags at the end.

const myTab = input.tab('BTST Settings');
const myRsiPeriod = myTab.number('RSI Period', 14, { min: 1, max: 200 });
const myRsiThreshold = myTab.number('Min RSI Level', 60, { min: 0, max: 100 });
const myVolMult = myTab.number('Volume Multiplier (vs 20 SMA)', 1.5, { min: 0.1, max: 10 });
const myHodBuffer = myTab.number('Near Day High Buffer', 0.992, { min: 0.5, max: 1, step: 0.001 });

// --- Core indicators ---
const myRsiVal = rsi(close, myRsiPeriod);
const myEma20 = ema(close, 20);
const myVolSma = sma(volume, 20);

// --- Day boundary detection (used for session high and session VWAP) ---
// Assumes the chart timezone equals the exchange timezone (Asia/Kolkata for
// Indian tickers), since time_of() always uses the exchange timezone.
const myDayInfo = time.map(_t => {
	const myInfo = time_of(_t);
	return myInfo.dayOfYear + '-' + myInfo.year;
});

const myNewDayFlag = myDayInfo.map((_d, _i) => _i === 0 ? true : _d !== myDayInfo[_i - 1]);

// --- Session High (resets every new trading day) ---
const mySessionHigh = series_of(null);
for (let myI = 0; myI < high.length; myI += 1) {
	if (myNewDayFlag[myI]) {
		mySessionHigh[myI] = high[myI];
	}
	else {
		mySessionHigh[myI] = Math.max(mySessionHigh[myI - 1], high[myI]);
	}
}

// --- Session VWAP (anchored at the start of each day, using HLC3 as Pine's ta.vwap does) ---
const myVwapVal = series_of(null);
let myCumPV = 0;
let myCumV = 0;
for (let myI = 0; myI < close.length; myI += 1) {
	const myTypicalPrice = hlc3[myI];
	if (myNewDayFlag[myI]) {
		myCumPV = myTypicalPrice * volume[myI];
		myCumV = volume[myI];
	}
	else {
		myCumPV += myTypicalPrice * volume[myI];
		myCumV += volume[myI];
	}
	myVwapVal[myI] = myCumV !== 0 ? myCumPV / myCumV : myTypicalPrice;
}

// --- Time window restriction (15:15 - 15:25, exchange timezone) ---
const myInBtstWindow = time.map(_t => {
	const myInfo = time_of(_t);
	const myMinutesOfDay = myInfo.hours * 60 + myInfo.minutes;
	return myMinutesOfDay >= (15 * 60 + 15) && myMinutesOfDay <= (15 * 60 + 25);
});

// --- BTST logic conditions ---
const myIsNearHOD = for_every(close, mySessionHigh, (_c, _sh) => _c >= (_sh * myHodBuffer));
const myIsVolumeSpike = for_every(volume, myVolSma, (_v, _vs) => _v > (_vs * myVolMult));
const myIsAboveVwap = for_every(close, myVwapVal, (_c, _v) => _c > _v);
const myIsAboveEma = for_every(close, myEma20, (_c, _e) => _c > _e);
const myIsRsiBull = for_every(myRsiVal, _r => _r >= myRsiThreshold);

const myBtstSignal = myInBtstWindow.map((_w, _i) => (
	_w &&
	myIsNearHOD[_i] &&
	myIsVolumeSpike[_i] &&
	myIsAboveVwap[_i] &&
	myIsAboveEma[_i] &&
	myIsRsiBull[_i]
));

// --- Visuals ---
paint(myEma20, { name: 'EMA20', color: 'orange', thickness: 1 });

const myBuySignalLabels = myBtstSignal.map(_sig => _sig ? constants.icons.triangle_up : null);
paint(myBuySignalLabels, { style: 'labels_below', color: 'green', name: 'BTST Buy' });

// --- Signals for scanners, alerts and strategy tester ---
register_signal(myBtstSignal, 'BTST Buy Signal');
register_signal(myInBtstWindow, 'In BTST Time Window');
register_signal(myIsNearHOD, 'Near Day High');
register_signal(myIsVolumeSpike, 'Volume Surge');
register_signal(for_every(myIsAboveVwap, myIsAboveEma, (_a, _b) => _a && _b), 'Above VWAP and EMA20');
register_signal(myIsRsiBull, 'RSI Bullish');

// --- Status dashboard overlay (replaces Pine's table.new/table.cell) ---
const myLastIndex = close.length - 1;
const myStatusRows = [
	{ cells: [{ text: 'BTST Condition', color: 'white' }, { text: 'Status', color: 'white' }] },
	{ cells: [{ text: 'Time Window 1515-1525', color: 'white' }, { text: myInBtstWindow[myLastIndex] ? 'ACTIVE' : 'INACTIVE', color: 'white' }] },
	{ cells: [{ text: 'Near Day High', color: 'white' }, { text: myIsNearHOD[myLastIndex] ? 'YES' : 'NO', color: 'white' }] },
	{ cells: [{ text: 'Volume Surge', color: 'white' }, { text: myIsVolumeSpike[myLastIndex] ? 'YES' : 'NO', color: 'white' }] },
	{ cells: [{ text: 'Above VWAP and EMA20', color: 'white' }, { text: (myIsAboveVwap[myLastIndex] && myIsAboveEma[myLastIndex]) ? 'YES' : 'NO', color: 'white' }] },
	{ cells: [{ text: 'RSI Above Threshold', color: 'white' }, { text: myIsRsiBull[myLastIndex] ? 'YES' : 'NO', color: 'white' }] }
];

paint_overlay('BtstDashboard', { position: 'top_right' }, { rows: myStatusRows });