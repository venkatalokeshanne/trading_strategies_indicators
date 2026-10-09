describe_indicator('Custom Cumulative Volume Delta (CVD) - Upstox Style', 'lower', { decimals: 2 });

// ==========================================
// INPUTS
// ==========================================
const myResetSession = input.select('CVD Reset Anchor', 'Daily', ['Daily', 'Session', 'Never']);
const myMaLength = input.number('Signal MA Length', 21, { min: 1, max: 500 });
const myMaType = input.select('Signal MA Type', 'EMA', ['EMA', 'SMA', 'WMA']);
const myShowDiv = input.boolean('Show Price-CVD Divergences?', true);

const myCandleCount = close.length;

// ==========================================
// RESET TRIGGER DETECTION
// Daily reset uses the exchange's daily session boundary (bar_at .session).
// "Session" reset in Pine uses a 120-minute higher-timeframe change, which has
// no direct equivalent here; we approximate it with fixed 2-hour UTC blocks.
// ==========================================
const myDailySessionId = time.map(_t => bar_at(_t).session);
const mySessionBlockId = time.map(_t => Math.floor(_t / 7200));

const myIsReset = series_of(false);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myResetSession === 'Never') {
		myIsReset[myIndex] = false;
	}
	else if (myResetSession === 'Daily') {
		myIsReset[myIndex] = myIndex > 0 && myDailySessionId[myIndex] !== myDailySessionId[myIndex - 1];
	}
	else {
		myIsReset[myIndex] = myIndex > 0 && mySessionBlockId[myIndex] !== mySessionBlockId[myIndex - 1];
	}
}

// ==========================================
// DELTA & ACCUMULATION ENGINE
// ==========================================
const myHlRange = sub(high, low);
const myCandleEfficiency = for_every(close, open, high, low, (_c, _o, _h, _l) => {
	const myRange = _h - _l;
	return myRange === 0 ? 0 : ((_c - _o) / myRange);
});
const myVolumeWeight = mult(volume, for_every(myCandleEfficiency, _e => Math.abs(_e)));

const myCurrentDelta = series_of(0);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myOpenV = open[myIndex];
	const myCloseV = close[myIndex];
	const myHighV = high[myIndex];
	const myLowV = low[myIndex];
	const myVolV = volume[myIndex];
	const myRange = myHighV - myLowV;
	const myVW = myVolumeWeight[myIndex];

	if (myCloseV > myOpenV) {
		myCurrentDelta[myIndex] = myVW + (myVolV * 0.1);
	}
	else if (myCloseV < myOpenV) {
		myCurrentDelta[myIndex] = -myVW - (myVolV * 0.1);
	}
	else {
		myCurrentDelta[myIndex] = myRange === 0 ? 0 : myVolV * (((myCloseV - myLowV) / myRange) - 0.5);
	}
}

// Persistent tracking (cvd pseudo-candle OHLC)
const myCvdOpen = series_of(0);
const myCvdHigh = series_of(0);
const myCvdLow = series_of(0);
const myCvdClose = series_of(0);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myDelta = myCurrentDelta[myIndex];

	if (myIsReset[myIndex]) {
		myCvdOpen[myIndex] = 0;
		myCvdClose[myIndex] = myDelta;
		myCvdHigh[myIndex] = Math.max(0, myDelta);
		myCvdLow[myIndex] = Math.min(0, myDelta);
	}
	else {
		const myPrevClose = myIndex > 0 ? myCvdClose[myIndex - 1] : 0;
		myCvdOpen[myIndex] = myPrevClose;
		myCvdClose[myIndex] = myPrevClose + myDelta;
		myCvdHigh[myIndex] = Math.max(myCvdOpen[myIndex], myCvdClose[myIndex]);
		myCvdLow[myIndex] = Math.min(myCvdOpen[myIndex], myCvdClose[myIndex]);
	}
}

// ==========================================
// VISUALIZATION (CVD pseudo-candles)
// There is no native candle-plot primitive in a lower panel, so we approximate
// the candle body with a color-coded cloud (open vs close) and the wicks with
// thin ladder lines (high / low), colored the same way per bar.
// ==========================================
const myCandleColor = for_every(myCvdClose, myCvdOpen, (_c, _o) => _c >= _o ? '#26A69A' : '#EF5350');

color_cloud(myCvdClose, myCvdOpen, '#26A69A', '#EF5350', 'CVD Up Body', 'CVD Down Body', 0.6);

paint(myCvdHigh, { name: 'CVD High Wick', style: 'ladder', color: myCandleColor, thickness: 1 });
paint(myCvdLow, { name: 'CVD Low Wick', style: 'ladder', color: myCandleColor, thickness: 1 });
paint(myCvdClose, { name: 'CVD Close', style: 'line', color: '#999999', thickness: 1 });

paint(horizontal_line(0), { name: 'Zero Baseline', style: 'dotted', color: 'gray' });

// ==========================================
// TREND CONFIRMATION (ADAPTIVE MA)
// ==========================================
const mySignalMA = myMaType === 'EMA' ? ema(myCvdClose, myMaLength)
	: myMaType === 'WMA' ? wma(myCvdClose, myMaLength)
	: sma(myCvdClose, myMaLength);

paint(mySignalMA, { name: 'Signal MA Line', color: 'orange', thickness: 2 });

// ==========================================
// DIVERGENCE DETECTION SYSTEM
// ==========================================
const myLbL = 5;
const myLbR = 5;

const myPriceHighPivot = pivot_high(high, myLbL, myLbR);
const myPriceLowPivot = pivot_low(low, myLbL, myLbR);

// Replicates ta.barssince(not na(x[1])): bars since the previous bar had a
// confirmed pivot one bar back.
function myComputeBarsSince(_pivotSeries) {
	const myResult = series_of(null);
	let myLastTrueIndex = -1;
	for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
		const myCondition = myIndex >= 1 && _pivotSeries[myIndex - 1] !== null && _pivotSeries[myIndex - 1] !== undefined;
		if (myCondition) {
			myResult[myIndex] = 0;
			myLastTrueIndex = myIndex;
		}
		else {
			myResult[myIndex] = myLastTrueIndex >= 0 ? (myIndex - myLastTrueIndex) : null;
		}
	}
	return myResult;
}

const myBarsSinceHighPivot = myComputeBarsSince(myPriceHighPivot);
const myBarsSinceLowPivot = myComputeBarsSince(myPriceLowPivot);

const myBearDiv = series_of(false);
const myBullDiv = series_of(false);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	// Bearish divergence
	if (myPriceHighPivot[myIndex] !== null && myShowDiv && myBarsSinceHighPivot[myIndex] !== null) {
		const myPhIndex = myBarsSinceHighPivot[myIndex] + 1;
		const myCurAt = myIndex - myLbR;
		const myRefAt = myIndex - myPhIndex - myLbR;
		if (myCurAt >= 0 && myRefAt >= 0) {
			if (high[myCurAt] > high[myRefAt] && myCvdClose[myCurAt] < myCvdClose[myRefAt]) {
				myBearDiv[myIndex] = true;
			}
		}
	}

	// Bullish divergence
	if (myPriceLowPivot[myIndex] !== null && myShowDiv && myBarsSinceLowPivot[myIndex] !== null) {
		const myPlIndex = myBarsSinceLowPivot[myIndex] + 1;
		const myCurAt = myIndex - myLbR;
		const myRefAt = myIndex - myPlIndex - myLbR;
		if (myCurAt >= 0 && myRefAt >= 0) {
			if (low[myCurAt] < low[myRefAt] && myCvdClose[myCurAt] > myCvdClose[myRefAt]) {
				myBullDiv[myIndex] = true;
			}
		}
	}
}

// Markers are plotted at offset -lbR in Pine (i.e. placed lbR bars back,
// aligned with the pivot bar itself). We shift the markers the same way.
const myBullDivMarker = series_of(null);
const myBearDivMarker = series_of(null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTargetIndex = myIndex - myLbR;
	if (myTargetIndex < 0) continue;
	if (myBullDiv[myIndex]) {
		myBullDivMarker[myTargetIndex] = myCvdLow[myTargetIndex];
	}
	if (myBearDiv[myIndex]) {
		myBearDivMarker[myTargetIndex] = myCvdHigh[myTargetIndex];
	}
}

paint(myBullDivMarker, { name: 'Bullish Divergence Circle', style: 'labels_below', color: 'green', thickness: 6 });
paint(myBearDivMarker, { name: 'Bearish Divergence Circle', style: 'labels_above', color: 'red', thickness: 6 });

// ==========================================
// SIGNALS FOR SCANNER / ALERTS / STRATEGY TESTER
// ==========================================
register_signal(myBullDiv, 'Bullish CVD Divergence');
register_signal(myBearDiv, 'Bearish CVD Divergence');
register_signal(for_every(myCvdClose, myCvdOpen, (_c, _o) => _c >= _o), 'CVD Candle Bullish');
register_signal(for_every(myCvdClose, mySignalMA, (_c, _m) => _c > _m), 'CVD Above Signal MA');