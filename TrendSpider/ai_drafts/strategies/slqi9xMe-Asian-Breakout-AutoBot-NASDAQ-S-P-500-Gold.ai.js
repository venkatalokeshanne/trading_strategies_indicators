describe_indicator('Asian Breakout AutoBot', 'price');

// NOTE: TrendSpider has no box.new()/line.new() objects and no bar-by-bar
// strategy engine like Pine. This script reproduces the Asian Breakout
// logic (session high/low tracking, breakout entries, SL/TP exits,
// EOD close) using plain series math and a manual sequential simulation.
// Session windows are matched against time_of() hours/minutes, which use
// the exchange's own timezone, not literal UTC like the Pine script did.

const myTab = input.tab('Timings (Exchange TZ hours)');
const myAsiaRow = myTab.row();
const myAsiaStartH = myAsiaRow.number('Asia Start Hour', 0, { min: 0, max: 23 });
const myAsiaEndH = myAsiaRow.number('Asia End Hour', 8, { min: 0, max: 23 });

const myUkRow = myTab.row();
const myUkStartH = myUkRow.number('UK Start Hour', 8, { min: 0, max: 23 });
const myUkEndH = myUkRow.number('UK End Hour', 13, { min: 0, max: 23 });

const myUsRow = myTab.row();
const myUsStartH = myUsRow.number('US Start Hour', 13, { min: 0, max: 23 });
const myUsEndH = myUsRow.number('US End Hour', 20, { min: 0, max: 23 });

const myRulesTab = input.tab('Strategy Rules');
const myRrTarget = myRulesTab.number('Risk/Reward Target', 2.0, { min: 0.1, max: 20, step: 0.5 });

const myCandleCount = close.length;

// Helper: is a given hour (0..24, with minute fraction) inside [startH, endH)
function myInSession(_hour, _minute, _startH, _endH) {
	const myFractionalHour = _hour + (_minute / 60);
	if (_startH < _endH) {
		return myFractionalHour >= _startH && myFractionalHour < _endH;
	}
	// handles sessions that wrap past midnight
	return myFractionalHour >= _startH || myFractionalHour < _endH;
}

const myInAsia = [];
const myInUk = [];
const myInUs = [];

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	myInAsia.push(myInSession(myTimeInfo.hours, myTimeInfo.minutes, myAsiaStartH, myAsiaEndH));
	myInUk.push(myInSession(myTimeInfo.hours, myTimeInfo.minutes, myUkStartH, myUkEndH));
	myInUs.push(myInSession(myTimeInfo.hours, myTimeInfo.minutes, myUsStartH, myUsEndH));
}

// Track Asian session rolling high/low, persisting (like Pine's `var`)
// across non-session candles until the next Asia session starts.
const myAsiaHigh = [];
const myAsiaLow = [];
let myRunningAsiaHigh = null;
let myRunningAsiaLow = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myWasInAsia = myIndex > 0 ? myInAsia[myIndex - 1] : false;
	const myIsNewAsia = myInAsia[myIndex] && !myWasInAsia;

	if (myIsNewAsia) {
		myRunningAsiaHigh = high[myIndex];
		myRunningAsiaLow = low[myIndex];
	}
	else if (myInAsia[myIndex]) {
		myRunningAsiaHigh = Math.max(myRunningAsiaHigh, high[myIndex]);
		myRunningAsiaLow = Math.min(myRunningAsiaLow, low[myIndex]);
	}

	myAsiaHigh.push(myRunningAsiaHigh);
	myAsiaLow.push(myRunningAsiaLow);
}

// Manual sequential simulation of the strategy (single position at a time)
const myLongSignal = series_of(null);
const mySellSignal = series_of(null);
const mySlLine = series_of(null);
const myTpLine = series_of(null);
const myEntryLine = series_of(null);

const myLongFlag = series_of(false);
const myShortFlag = series_of(false);

let myPositionSide = 0; // 0 = flat, 1 = long, -1 = short
let myEntryPrice = null;
let mySlPrice = null;
let myTpPrice = null;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myTradeWindow = myInUk[myIndex] || myInUs[myIndex];
	const myAHigh = myAsiaHigh[myIndex];
	const myALow = myAsiaLow[myIndex];
	const myPrevAHigh = myAsiaHigh[myIndex - 1];
	const myPrevALow = myAsiaLow[myIndex - 1];

	// Exit handling first (so a flat position may open on the same candle,
	// mirroring Pine's bar-close execution order closely enough)
	if (myPositionSide !== 0) {
		let myExited = false;

		if (myPositionSide === 1) {
			if (low[myIndex] <= mySlPrice) {
				myExited = true;
			}
			else if (high[myIndex] >= myTpPrice) {
				myExited = true;
			}
		}
		else if (myPositionSide === -1) {
			if (high[myIndex] >= mySlPrice) {
				myExited = true;
			}
			else if (low[myIndex] <= myTpPrice) {
				myExited = true;
			}
		}

		// EOD failsafe: close everything right when US session ends
		const myUsEnded = myInUs[myIndex - 1] && !myInUs[myIndex];
		if (myUsEnded) {
			myExited = true;
		}

		if (myExited) {
			myPositionSide = 0;
			myEntryPrice = null;
			mySlPrice = null;
			myTpPrice = null;
		}
	}

	if (myPositionSide === 0 && myAHigh !== null && myALow !== null && myPrevAHigh !== null && myPrevALow !== null) {
		const myAsiaRangeSize = myAHigh - myALow;

		const myCrossoverUp = close[myIndex] > myAHigh && close[myIndex - 1] <= myPrevAHigh;
		const myCrossoverDown = close[myIndex] < myALow && close[myIndex - 1] >= myPrevALow;

		const myLongCond = myTradeWindow && myCrossoverUp;
		const myShortCond = myTradeWindow && myCrossoverDown;

		if (myLongCond) {
			myPositionSide = 1;
			myEntryPrice = close[myIndex];
			mySlPrice = myALow;
			myTpPrice = myAHigh + (myAsiaRangeSize * myRrTarget);
			myLongFlag[myIndex] = true;
		}
		else if (myShortCond) {
			myPositionSide = -1;
			myEntryPrice = close[myIndex];
			mySlPrice = myAHigh;
			myTpPrice = myALow - (myAsiaRangeSize * myRrTarget);
			myShortFlag[myIndex] = true;
		}
	}

	if (myPositionSide !== 0) {
		myEntryLine[myIndex] = myEntryPrice;
		mySlLine[myIndex] = mySlPrice;
		myTpLine[myIndex] = myTpPrice;
	}

	if (myLongFlag[myIndex]) {
		myLongSignal[myIndex] = low[myIndex];
	}
	if (myShortFlag[myIndex]) {
		mySellSignal[myIndex] = high[myIndex];
	}
}

// Asia session high/low reference lines
paint(series_of(null).map((_v, _i) => myAsiaHigh[_i]), { name: 'Asia High', color: '#4DA3FF', style: 'ladder', thickness: 1 });
paint(series_of(null).map((_v, _i) => myAsiaLow[_i]), { name: 'Asia Low', color: '#4DA3FF', style: 'ladder', thickness: 1 });

// Active trade visuals
paint(myEntryLine, { name: 'Entry', color: 'gray', style: 'ladder', thickness: 2 });
paint(mySlLine, { name: 'Stop Loss', color: 'red', style: 'ladder', thickness: 2 });
paint(myTpLine, { name: 'Take Profit', color: 'green', style: 'ladder', thickness: 2 });

// Buy and Sell markers
paint(myLongSignal, { name: 'Buy Signal', style: 'labels_below', color: 'green' });
paint(mySellSignal, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// Scanner/alert/strategy-friendly signals
register_signal(myLongFlag, 'Long Breakout Entry');
register_signal(myShortFlag, 'Short Breakout Entry');