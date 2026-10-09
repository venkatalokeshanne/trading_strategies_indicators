describe_indicator('NY AM Range Sweep', 'price');

// This is a complex session/state based conversion from Pine Script.
// The TrendSpider Custom JS API has no equivalent of Pine's
// box/line drawing objects, var persistence across days tied to a
// specific time zone session string, or time(timeframe, session, tz)
// function. I rebuilt the logic using bar_at()/time_of() to detect
// New York session days and the AM range window, tracking the range
// high/low, detecting a liquidity sweep of that range, and waiting
// for a confirmation close back inside the range before firing a
// buy/sell signal. This is my best-effort equivalent of the Pine
// logic; exact bar-for-bar parity with Pine Script cannot be fully
// guaranteed since internal engines differ.

const myStartHour = input.number('Range Start Hour (NY)', 5, { min: 0, max: 23 });
const myEndHour = input.number('Range End Hour (NY)', 9, { min: 0, max: 23 });

const myRangeHighSeries = series_of(null);
const myRangeLowSeries = series_of(null);
const mySweepUpSignal = series_of(false);
const mySweepDownSignal = series_of(false);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

let myCurrentDayKey = null;
let myRangeHigh = null;
let myRangeLow = null;
let myRangeReady = false;
let mySweepDir = 0;
let myWaitingConfirm = false;
let myTradeTakenToday = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;
	const myHour = myTimeInfo.hours;

	// New NY day detected: reset all persistent state
	if (myDayKey !== myCurrentDayKey) {
		myCurrentDayKey = myDayKey;
		myRangeHigh = null;
		myRangeLow = null;
		myRangeReady = false;
		mySweepDir = 0;
		myWaitingConfirm = false;
		myTradeTakenToday = false;
	}

	const myInRangeSession = myHour >= myStartHour && myHour < myEndHour;

	if (myInRangeSession) {
		myRangeHigh = myRangeHigh === null ? high[myIndex] : Math.max(myRangeHigh, high[myIndex]);
		myRangeLow = myRangeLow === null ? low[myIndex] : Math.min(myRangeLow, low[myIndex]);
		myRangeReady = false;
	}
	else if (myRangeHigh !== null && myRangeLow !== null) {
		myRangeReady = true;
	}

	myRangeHighSeries[myIndex] = myRangeReady ? myRangeHigh : null;
	myRangeLowSeries[myIndex] = myRangeReady ? myRangeLow : null;

	let mySweepUp = false;
	let mySweepDown = false;
	let myBuy = false;
	let mySell = false;

	if (myRangeReady && !myTradeTakenToday) {
		// Detect sweep of range high (sell bias) or range low (buy bias)
		if (!myWaitingConfirm) {
			if (high[myIndex] > myRangeHigh) {
				mySweepDir = -1;
				myWaitingConfirm = true;
				mySweepUp = true;
			}
			else if (low[myIndex] < myRangeLow) {
				mySweepDir = 1;
				myWaitingConfirm = true;
				mySweepDown = true;
			}
		}
		else {
			// Confirmation: close back inside the range triggers signal
			if (mySweepDir === -1 && close[myIndex] < myRangeHigh) {
				mySell = true;
				myWaitingConfirm = false;
				myTradeTakenToday = true;
			}
			else if (mySweepDir === 1 && close[myIndex] > myRangeLow) {
				myBuy = true;
				myWaitingConfirm = false;
				myTradeTakenToday = true;
			}
		}
	}

	mySweepUpSignal[myIndex] = mySweepUp;
	mySweepDownSignal[myIndex] = mySweepDown;
	myBuySignal[myIndex] = myBuy;
	mySellSignal[myIndex] = mySell;
}

const myRangeHighLine = paint(myRangeHighSeries, { name: 'RangeHigh', color: '#4DA3FF', style: 'ladder', thickness: 2 });
const myRangeLowLine = paint(myRangeLowSeries, { name: 'RangeLow', color: '#FF9800', style: 'ladder', thickness: 2 });
fill(myRangeHighLine, myRangeLowLine, '#4DA3FF', 0.08);

const myBuyMarks = for_every(myBuySignal, low, (_buy, _low) => _buy ? _low : null);
const mySellMarks = for_every(mySellSignal, high, (_sell, _high) => _sell ? _high : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350', thickness: 3 });

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(mySweepUpSignal, 'Range High Swept');
register_signal(mySweepDownSignal, 'Range Low Swept');