describe_indicator('09:29 NY Limit Reversal', 'price');

// This indicator reproduces the Pine Script "09:29 NY Limit Reversal"
// strategy logic. Since TrendSpider does not support true limit/stop
// order simulation inside a custom indicator, order fills are
// approximated bar-by-bar: a "Long" is considered filled if a bar's
// Low touches/crosses the buy limit while an order is active, and a
// "Short" is considered filled if a bar's High touches/crosses the
// sell limit. Exits (TP/SL) are approximated the same way, checking
// High/Low against the computed stop and target levels on each bar.
// NY session time is computed using the moment-timezone library,
// since the Custom JS API does not expose arbitrary timezone
// conversions natively.

const myOffset = input.number('Offset', 20, { min: 0, max: 1000 });
const mySlPoints = input.number('SL Points', 10, { min: 0.1, max: 1000 });
const myRrRatio = input.number('RR Ratio', 2, { min: 0.1, max: 50 });

const myMoment = library('moment-timezone');

const myN = close.length;

const myBuyLimitLine = series_of(null);
const mySellLimitLine = series_of(null);
const myMarker = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myRefClose = null;
let myBuyLimit = null;
let mySellLimit = null;
let myHasOrderedToday = false;
let myPrevDay = null;

// 0 = flat, 1 = long, -1 = short
let myPositionSize = 0;
let myBuyTP = null;
let myBuySL = null;
let mySellTP = null;
let mySellSL = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myNyMoment = myMoment.tz(time[myIndex] * 1000, 'America/New_York');
	const myDayKey = myNyMoment.format('YYYY-MM-DD');
	const myNyTime = myNyMoment.hours() * 100 + myNyMoment.minutes();

	// day change reset
	if (myPrevDay !== null && myDayKey !== myPrevDay) {
		myRefClose = null;
		myBuyLimit = null;
		mySellLimit = null;
		myHasOrderedToday = false;
		myPositionSize = 0;
		myBuyTP = null;
		myBuySL = null;
		mySellTP = null;
		mySellSL = null;
	}
	myPrevDay = myDayKey;

	const myIs0929 = myNyTime === 929;
	const myIs0935Up = myNyTime >= 935;

	if (myIs0929) {
		myRefClose = close[myIndex];
		myBuyLimit = myRefClose - myOffset;
		mySellLimit = myRefClose + myOffset;
	}

	// 09:35 auto-cancel if still flat
	if (myIs0935Up && myPositionSize === 0 && myHasOrderedToday === true) {
		myHasOrderedToday = true;
	}

	const myCanExecute = myRefClose !== null && myHasOrderedToday === false && myNyTime < 935 && myPositionSize === 0;

	if (myCanExecute) {
		myHasOrderedToday = true;
		myBuyTP = myBuyLimit + (mySlPoints * myRrRatio);
		myBuySL = myBuyLimit - mySlPoints;
		mySellTP = mySellLimit - (mySlPoints * myRrRatio);
		mySellSL = mySellLimit + mySlPoints;
	}

	// try fill the limit orders (approximation, OCO: long checked first)
	if (myHasOrderedToday && myPositionSize === 0 && myRefClose !== null && myNyTime < 935) {
		if (low[myIndex] <= myBuyLimit) {
			myPositionSize = 1;
			myLongEntrySignal[myIndex] = true;
		}
		else if (high[myIndex] >= mySellLimit) {
			myPositionSize = -1;
			myShortEntrySignal[myIndex] = true;
		}
	}

	// exits
	if (myPositionSize === 1) {
		if (low[myIndex] <= myBuySL || high[myIndex] >= myBuyTP) {
			myLongExitSignal[myIndex] = true;
			myPositionSize = 0;
		}
	}
	else if (myPositionSize === -1) {
		if (high[myIndex] >= mySellSL || low[myIndex] <= mySellTP) {
			myShortExitSignal[myIndex] = true;
			myPositionSize = 0;
		}
	}

	const myShowLine = !myHasOrderedToday && myRefClose !== null && myNyTime < 935;

	myBuyLimitLine[myIndex] = myShowLine ? myBuyLimit : null;
	mySellLimitLine[myIndex] = myShowLine ? mySellLimit : null;
	myMarker[myIndex] = myIs0929 ? constants.icons.triangle_up : null;
}

paint(myBuyLimitLine, { name: 'LongLimit', color: '#2ca599', thickness: 2, style: 'line' });
paint(mySellLimitLine, { name: 'ShortLimit', color: '#ee5451', thickness: 2, style: 'line' });
paint(myMarker, { name: 'RefMark', color: 'blue', style: 'labels_below' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');