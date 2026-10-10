describe_indicator('NY AM Range Sweep PRO', 'price');

// NOTE: Pine script explicitly works with "America/New_York" session hours.
// Custom JS API's time_of() only exposes hours in the EXCHANGE timezone,
// there is no way to force a custom timezone like "America/New_York" here.
// This is an approximation: if the chart's exchange timezone differs from
// NY, hour-of-day grouping (and thus the AM range window) will be off.
const myStartHour = input.number('Range Start Hour', 5, { min: 0, max: 23 });
const myEndHour = input.number('Range End Hour', 9, { min: 0, max: 23 });

const myData45 = await request.history(current.ticker, '45');
assert(!myData45.error, 'Error fetching 45m data: ' + myData45.error);

// direction of each 45m candle: 1 bullish, -1 bearish, 0 flat
const myDir45Raw = myData45.close.map((_c, _i) => {
	if (myData45.close[_i] > myData45.open[_i]) return 1;
	if (myData45.close[_i] < myData45.open[_i]) return -1;
	return 0;
});

// land the most recently closed 45m candle direction onto each chart candle
const myDir45Landed = land_points_onto_series(myData45.time, myDir45Raw, time, 'le');
const myDir45Filled = interpolate_sparse_series(myDir45Landed, 'constant');

const myDayStr = time.map(_t => {
	const myInfo = time_of(_t);
	return myInfo.year + '-' + myInfo.month + '-' + myInfo.dayOfMonth;
});
const myHourOf = time.map(_t => time_of(_t).hours);

// ---------- Output series ----------
const myRangeHighSeries = series_of(null);
const myRangeLowSeries = series_of(null);
const mySweepHighLabel = series_of(null);
const mySweepLowLabel = series_of(null);
const myBuyEntryLabel = series_of(null);
const mySellEntryLabel = series_of(null);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

// ---------- Persistent state (resets every new day) ----------
let myLastDateStr = '';
let myRangeHigh = null;
let myRangeLow = null;
let myRangeReady = false;
let myDayInvalid = false;
let mySweepDir = 0; // -1 = swept high (sell bias) | 1 = swept low (buy bias)
let mySweepWick = null;
let myWaitingConfirm5 = false;
let myWaitingConfirm45 = false;
let myTradeTakenToday = false;
let myLastBullLow = null;
let myLastBearHigh = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myIsNewDay = myDayStr[myIndex] !== myLastDateStr;
	myLastDateStr = myDayStr[myIndex];

	if (myIsNewDay) {
		myRangeHigh = null;
		myRangeLow = null;
		myRangeReady = false;
		myDayInvalid = false;
		mySweepDir = 0;
		mySweepWick = null;
		myWaitingConfirm5 = false;
		myWaitingConfirm45 = false;
		myTradeTakenToday = false;
		myLastBullLow = null;
		myLastBearHigh = null;
	}

	const myInRangeSession = myHourOf[myIndex] >= myStartHour && myHourOf[myIndex] < myEndHour;

	// ---------- Build the range ----------
	if (myInRangeSession) {
		myRangeHigh = (myRangeHigh === null) ? high[myIndex] : Math.max(myRangeHigh, high[myIndex]);
		myRangeLow = (myRangeLow === null) ? low[myIndex] : Math.min(myRangeLow, low[myIndex]);
	}

	if (!myInRangeSession && myRangeHigh !== null && !myRangeReady) {
		myRangeReady = true;
	}

	myRangeHighSeries[myIndex] = myRangeReady ? myRangeHigh : null;
	myRangeLowSeries[myIndex] = myRangeReady ? myRangeLow : null;

	// ---------- 5m confirmation (uses structure prior to this candle) ----------
	let myConfirm5 = false;
	if (myWaitingConfirm5 && !myDayInvalid) {
		if (mySweepDir === -1 && myLastBullLow !== null && close[myIndex] < myLastBullLow) {
			myConfirm5 = true;
		}
		if (mySweepDir === 1 && myLastBearHigh !== null && close[myIndex] > myLastBearHigh) {
			myConfirm5 = true;
		}
	}

	if (myConfirm5) {
		myWaitingConfirm5 = false;
		myWaitingConfirm45 = true;
	}

	// ---------- Sweep detection ----------
	if (myRangeReady && mySweepDir === 0 && !myDayInvalid && !myTradeTakenToday) {
		if (close[myIndex] > myRangeHigh) {
			mySweepDir = -1;
			mySweepWick = high[myIndex];
			myWaitingConfirm5 = true;
			mySweepHighLabel[myIndex] = high[myIndex];
		}
		else if (close[myIndex] < myRangeLow) {
			mySweepDir = 1;
			mySweepWick = low[myIndex];
			myWaitingConfirm5 = true;
			mySweepLowLabel[myIndex] = low[myIndex];
		}
	}

	// ---------- Invalidation (sweeps both sides same day) ----------
	if (myRangeReady && mySweepDir !== 0 && !myDayInvalid && !myTradeTakenToday) {
		if (mySweepDir === -1 && close[myIndex] < myRangeLow) {
			myDayInvalid = true;
			myWaitingConfirm5 = false;
			myWaitingConfirm45 = false;
		}
		if (mySweepDir === 1 && close[myIndex] > myRangeHigh) {
			myDayInvalid = true;
			myWaitingConfirm5 = false;
			myWaitingConfirm45 = false;
		}
	}

	// ---------- Track last bullish/bearish candle ----------
	if (close[myIndex] > open[myIndex]) {
		myLastBullLow = low[myIndex];
	}
	if (close[myIndex] < open[myIndex]) {
		myLastBearHigh = high[myIndex];
	}

	// ---------- 45m confirmation ----------
	const myDir45 = myDir45Filled[myIndex];
	if (myWaitingConfirm45 && !myTradeTakenToday && !myDayInvalid) {
		const myValidDir45 = (mySweepDir === -1 && myDir45 === -1) || (mySweepDir === 1 && myDir45 === 1);
		if (myValidDir45) {
			myTradeTakenToday = true;
			myWaitingConfirm45 = false;
			if (mySweepDir === -1) {
				mySellEntryLabel[myIndex] = close[myIndex];
				mySellSignal[myIndex] = true;
			}
			else {
				myBuyEntryLabel[myIndex] = close[myIndex];
				myBuySignal[myIndex] = true;
			}
		}
	}
}

paint(myRangeHighSeries, { name: 'RangeHigh', style: 'ladder', color: '#4DA3FF' });
paint(myRangeLowSeries, { name: 'RangeLow', style: 'ladder', color: '#4DA3FF' });
paint(mySweepHighLabel, { name: 'SweepHigh', style: 'labels_above', color: 'red' });
paint(mySweepLowLabel, { name: 'SweepLow', style: 'labels_below', color: 'green' });
paint(mySellEntryLabel, { name: 'SellEntry', style: 'labels_above', color: 'red' });
paint(myBuyEntryLabel, { name: 'BuyEntry', style: 'labels_below', color: 'green' });

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');