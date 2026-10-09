describe_indicator('Wed to Thu 920 Nifty Strategy', 'price');

// This indicator reproduces the Pine Script strategy logic as closely
// as possible using TrendSpider Custom JS API. It assumes the chart's
// exchange time zone already corresponds to Asia/Kolkata (true for NSE
// Nifty data), since custom scripts can only use the exchange time zone
// exposed via time_of(), not an arbitrary IANA tz string.

const myStopLossPoints = input.number('Stop Loss (points)', 100, { min: 1, max: 10000 });
const myExitHour = input.number('Exit Hour', 15, { min: 0, max: 23 });
const myExitMinute = input.number('Exit Minute (>=)', 15, { min: 0, max: 59 });

const myRefPrice = series_of(null);
const mySlLine = series_of(null);
const myLongEntryFlag = series_of(false);
const myShortEntryFlag = series_of(false);
const myExitFlag = series_of(false);

let myPrevTuePrice = null;
let myPrevWedPrice = null;
let myCurrTuePrice = null;
let myCurrWedPrice = null;
let myActiveRefPrice = null;

// position: 0 = flat, 1 = long, -1 = short
let myPositionSize = 0;
let myPositionAvgPrice = null;

let myLastWeekKey = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	// ISO dayOfWeek: 1 = Monday ... 7 = Sunday (matches Pine dayofweek.tuesday=3, wednesday=4 roughly differs)
	// Pine dayofweek: Sunday=1 ... Saturday=7. We map accordingly below.
	// Our time_of dayOfWeek: Monday=1 ... Sunday=7, so Tuesday=2, Wednesday=3.
	const myIsTuesday = myTimeInfo.dayOfWeek === 2;
	const myIsWednesday = myTimeInfo.dayOfWeek === 3;
	const myIs920Time = myTimeInfo.hours === 9 && myTimeInfo.minutes === 15;

	const myWeekKey = `${myTimeInfo.year}-${myTimeInfo.weekOfYear}`;
	const myIsNewWeek = myLastWeekKey !== null && myWeekKey !== myLastWeekKey;
	myLastWeekKey = myWeekKey;

	if (myIsNewWeek) {
		myPrevTuePrice = myCurrTuePrice;
		myPrevWedPrice = myCurrWedPrice;
		myCurrTuePrice = null;
		myCurrWedPrice = null;
		myActiveRefPrice = null;
	}

	// Record Tuesday 9:20 close
	if (myIsTuesday && myIs920Time) {
		myCurrTuePrice = close[myIndex];
	}

	// Wednesday core logic
	if (myIsWednesday && myIs920Time) {
		myActiveRefPrice = (myPrevWedPrice === null || myPrevWedPrice === undefined) ? myPrevTuePrice : myPrevWedPrice;

		if (myActiveRefPrice !== null && myActiveRefPrice !== undefined && myPositionSize === 0) {
			if (close[myIndex] > myActiveRefPrice) {
				myPositionSize = 1;
				myPositionAvgPrice = close[myIndex];
				myLongEntryFlag[myIndex] = true;
			}
			else if (close[myIndex] < myActiveRefPrice) {
				myPositionSize = -1;
				myPositionAvgPrice = close[myIndex];
				myShortEntryFlag[myIndex] = true;
			}
		}

		myCurrWedPrice = close[myIndex];
	}

	// Stop loss exit
	if (myPositionSize > 0) {
		const mySlLevel = myPositionAvgPrice - myStopLossPoints;
		if (low[myIndex] <= mySlLevel) {
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myExitFlag[myIndex] = true;
		}
	}
	else if (myPositionSize < 0) {
		const mySlLevel = myPositionAvgPrice + myStopLossPoints;
		if (high[myIndex] >= mySlLevel) {
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myExitFlag[myIndex] = true;
		}
	}

	// Time based exit (next trading day 15:15+, skip Wednesday)
	if (myPositionSize !== 0 && !myIsWednesday && myTimeInfo.hours === myExitHour && myTimeInfo.minutes >= myExitMinute) {
		myPositionSize = 0;
		myPositionAvgPrice = null;
		myExitFlag[myIndex] = true;
	}

	myRefPrice[myIndex] = myActiveRefPrice;
	mySlLine[myIndex] = myPositionSize > 0 ? (myPositionAvgPrice - myStopLossPoints) : myPositionSize < 0 ? (myPositionAvgPrice + myStopLossPoints) : null;
}

paint(myRefPrice, { name: 'ReferencePrice', color: '#2962FF', thickness: 2, style: 'line' });
paint(mySlLine, { name: 'ActiveStopLoss', color: '#EF5350', thickness: 2, style: 'line' });

register_signal(myLongEntryFlag, 'Long Entry');
register_signal(myShortEntryFlag, 'Short Entry');
register_signal(myExitFlag, 'Position Exit');