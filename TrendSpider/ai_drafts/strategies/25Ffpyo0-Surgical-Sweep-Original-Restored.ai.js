describe_indicator('Surgical Sweep (restored)', 'overlay');

// NOTE: this indicator is a best-effort translation of a Pine Script v6
// "strategy" into a TrendSpider indicator. TrendSpider custom scripts do
// not support strategy.entry()/strategy.position_size, so trade position
// state is simulated manually in a loop. Also, pivot_high()/pivot_low()
// place their value AT the pivot candle, while Pine's ta.pivothigh/low
// (as used here) effectively gets assigned to the CONFIRMATION bar
// (lookback bars later). This script keeps values at the pivot candle
// and forward-fills them, which is the closest equivalent achievable
// with the available built-ins; exact bar-by-bar signal timing can
// differ slightly from the original Pine script because of this.

const myLookback = input.number('Pivot Sensitivity', 5, { min: 1, max: 50 });
const myVolMult = input.number('Volume Spike Filter', 1.2, { min: 0.1, max: 10 });
const myLineLen = input.number('Line Length', 15, { min: 1, max: 200 });

// --- volume spike filter ---
const myAvgVol = sma(volume, 20);
const myIsHighVol = for_every(volume, myAvgVol, (_vol, _avg) => _vol > (_avg * myVolMult));

// --- weekday filter ---
const myIsWeekday = time.map(_t => {
	const _dow = time_of(_t).dayOfWeek; // 1=Mon ... 7=Sun
	return _dow !== 6 && _dow !== 7;
});

// --- pivots ---
const myHi = pivot_high(high, myLookback, myLookback);
const myLo = pivot_low(low, myLookback, myLookback);

// forward-fill levels (approximation of Pine's "var float" persistence)
const myResLevel = interpolate_sparse_series(myHi, 'constant');
const mySupLevel = interpolate_sparse_series(myLo, 'constant');

const myHighShift1 = shift(high, 1);
const myCloseShift1 = shift(close, 1);

// --- signals ---
const mySellSignal = series_of(false);
const myBuySignal = series_of(false);
const myPurpleTrigger = series_of(false);
const myEnteredLong = series_of(false);
const myEnteredShort = series_of(false);
const myExitedTrade = series_of(false);

const myCandleCount = close.length;

let myBlueCount = 0;
let myLastBluePrice = null;
let myRedCount = 0;
let myLastRedPrice = null;
let myPositionSize = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myRes = myResLevel[myIndex];
	const mySup = mySupLevel[myIndex];
	const myHighVol = myIsHighVol[myIndex];

	const mySell = (myRes != null) &&
		myHighVol &&
		myHighShift1[myIndex] > myRes &&
		myCloseShift1[myIndex] > myRes &&
		close[myIndex] < myRes;

	const myBuy = (mySup != null) &&
		myHighVol &&
		low[myIndex] < mySup && // placeholder replaced below
		myCloseShift1[myIndex] < mySup &&
		close[myIndex] > mySup;

	// correct buy_signal uses low[1], not current low
	const myLowShift1 = low[myIndex - 1];
	const myBuyFinal = (mySup != null) &&
		myHighVol &&
		(myIndex > 0 && myLowShift1 < mySup) &&
		(myIndex > 0 && myCloseShift1[myIndex] < mySup) &&
		close[myIndex] > mySup;

	mySellSignal[myIndex] = mySell;
	myBuySignal[myIndex] = myBuyFinal;

	// purple step logic
	if (myBuyFinal) {
		myBlueCount = (myLastBluePrice == null || mySup < myLastBluePrice) ? (myBlueCount + 1) : 1;
		myLastBluePrice = mySup;
		myRedCount = 0;
	}
	else if (mySell) {
		myBlueCount = 0;
	}

	if (mySell) {
		myRedCount = (myLastRedPrice == null || myRes > myLastRedPrice) ? (myRedCount + 1) : 1;
		myLastRedPrice = myRes;
		myBlueCount = 0;
	}
	else if (myBuyFinal) {
		myRedCount = 0;
	}

	myPurpleTrigger[myIndex] = (myBlueCount === 2 && myBuyFinal) || (myRedCount === 2 && mySell);

	// simulated strategy position state
	const myPrevPosition = myPositionSize;

	if (myBuyFinal && myIsWeekday[myIndex]) {
		myPositionSize = 1;
	}
	else if (mySell && myIsWeekday[myIndex]) {
		myPositionSize = -1;
	}

	const myPositionChange = myPositionSize - myPrevPosition;

	myEnteredLong[myIndex] = (myPositionChange > 0) && (myPrevPosition <= 0);
	myEnteredShort[myIndex] = (myPositionChange < 0) && (myPrevPosition >= 0);
	myExitedTrade[myIndex] = (myPositionChange !== 0) && (myPositionSize === 0);
}

// --- paint levels (approximation of the original segmented pivot lines) ---
paint(myResLevel, { name: 'ResistanceLevel', color: '#ff5252', style: 'ladder', thickness: 2 });
paint(mySupLevel, { name: 'SupportLevel', color: '#2195f3', style: 'ladder', thickness: 2 });

// --- paint signal markers ---
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const myPurpleMarks = for_every(myPurpleTrigger, high, (_p, _h) => _p ? _h : null);
const myEnteredLongMarks = for_every(myEnteredLong, low, (_e, _l) => _e ? _l : null);
const myEnteredShortMarks = for_every(myEnteredShort, high, (_e, _h) => _e ? _h : null);
const myExitedMarks = for_every(myExitedTrade, high, (_e, _h) => _e ? _h : null);

paint(mySellMarks, { name: 'SellMarker', color: 'red', style: 'labels_above' });
paint(myBuyMarks, { name: 'BuyMarker', color: 'blue', style: 'labels_below' });
paint(myPurpleMarks, { name: 'PurpleSweepMarker', color: 'purple', style: 'labels_above' });
paint(myEnteredLongMarks, { name: 'EnteredLongMarker', color: 'green', style: 'labels_below' });
paint(myEnteredShortMarks, { name: 'EnteredShortMarker', color: 'red', style: 'labels_above' });
paint(myExitedMarks, { name: 'ExitedTradeMarker', color: 'gray', style: 'labels_above' });

// --- signals for scanner/alerts/strategy tester ---
register_signal(mySellSignal, 'Sell Signal');
register_signal(myBuySignal, 'Buy Signal');
register_signal(myPurpleTrigger, 'Purple Sweep Trigger');
register_signal(myEnteredLong, 'Entered Long');
register_signal(myEnteredShort, 'Entered Short');
register_signal(myExitedTrade, 'Exited Trade');