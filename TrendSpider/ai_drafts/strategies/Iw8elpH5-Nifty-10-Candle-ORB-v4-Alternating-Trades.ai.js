describe_indicator('Nifty 10 Candle ORB v4', 'price');

// This indicator reproduces the Pine Script "Nifty 10-Candle ORB v4"
// strategy logic as a chart indicator with scanning/strategy signals.
// Since TrendSpider Custom JS has no strategy/broker engine, position
// tracking (entry/exit, TP/SL, EOD close) is simulated bar-by-bar in
// JavaScript, mirroring Pine's intrabar high/low based stop/limit
// fills as closely as possible.

const myTpPercent = input.number('Profit Target (%)', 1.0, { min: 0.01, max: 100, step: 0.1 });
const mySlPercent = input.number('Stop Loss (%)', 0.5, { min: 0.01, max: 100, step: 0.1 });
const myNumCandles = input.number('Number of Opening Candles', 10, { min: 1, max: 500 });
const myExitHour = input.number('Exit Hour (24h)', 15, { min: 0, max: 23 });
const myExitMinute = input.number('Exit Minute', 0, { min: 0, max: 59 });
const myLastTradeHour = input.number('Last Entry Hour (24h)', 15, { min: 0, max: 23 });

const myLength = close.length;

const myOrbHigh = series_of(null);
const myOrbLow = series_of(null);

const myEntryLong = series_of(false);
const myEntryShort = series_of(false);
const myExitLong = series_of(false);
const myExitShort = series_of(false);
const myEodSquareOff = series_of(false);

let mySessionHigh = null;
let mySessionLow = null;
let myCandleIdx = 0;
let myLastTradeType = 0; // 0 none, 1 long, -1 short
let myPrevDayKey = null;

let myPositionSize = 0; // 0 flat, 1 long, -1 short
let myPositionAvgPrice = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = myTimeInfo.year * 1000 + myTimeInfo.dayOfYear;

	const myIsNewDay = myPrevDayKey !== null && myDayKey !== myPrevDayKey;
	myPrevDayKey = myDayKey;

	if (myIsNewDay) {
		mySessionHigh = null;
		mySessionLow = null;
		myCandleIdx = 0;
		myLastTradeType = 0;
	}

	// range building (opening N candles)
	if (myCandleIdx < myNumCandles) {
		myCandleIdx += 1;
		mySessionHigh = mySessionHigh === null ? high[myIndex] : Math.max(mySessionHigh, high[myIndex]);
		mySessionLow = mySessionLow === null ? low[myIndex] : Math.min(mySessionLow, low[myIndex]);
	}

	const myRangeReady = myCandleIdx >= myNumCandles;
	myOrbHigh[myIndex] = myRangeReady ? mySessionHigh : null;
	myOrbLow[myIndex] = myRangeReady ? mySessionLow : null;

	// time logic
	const myCurrentTime = myTimeInfo.hours * 100 + myTimeInfo.minutes;
	const myIsExitTime = myCurrentTime >= (myExitHour * 100 + myExitMinute);
	const myCanEnter = myCurrentTime < (myLastTradeHour * 100);

	// --- Exits are evaluated first (based on levels set when position opened) ---
	if (myPositionSize > 0 && myPositionAvgPrice !== null) {
		const myTpPrice = myPositionAvgPrice * (1 + myTpPercent / 100);
		const mySlPrice = myPositionAvgPrice * (1 - mySlPercent / 100);
		// approximate Pine broker emulator: check intrabar high/low touches
		if (high[myIndex] >= myTpPrice || low[myIndex] <= mySlPrice) {
			myExitLong[myIndex] = true;
			myPositionSize = 0;
			myPositionAvgPrice = null;
		}
	}
	else if (myPositionSize < 0 && myPositionAvgPrice !== null) {
		const myTpPrice = myPositionAvgPrice * (1 - myTpPercent / 100);
		const mySlPrice = myPositionAvgPrice * (1 + mySlPercent / 100);
		if (low[myIndex] <= myTpPrice || high[myIndex] >= mySlPrice) {
			myExitShort[myIndex] = true;
			myPositionSize = 0;
			myPositionAvgPrice = null;
		}
	}

	// forced EOD square off (overrides any still-open position)
	if (myIsExitTime && myPositionSize !== 0) {
		myEodSquareOff[myIndex] = true;
		myPositionSize = 0;
		myPositionAvgPrice = null;
	}

	// --- Entries ---
	const myCanTrade = myRangeReady && myPositionSize === 0 && myCanEnter && !myIsExitTime;

	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myPrevOrbHigh = myIndex > 0 ? myOrbHigh[myIndex - 1] : null;
	const myPrevOrbLow = myIndex > 0 ? myOrbLow[myIndex - 1] : null;

	const myCrossoverHigh = myRangeReady && myPrevClose !== null && myPrevOrbHigh !== null
		&& myPrevClose <= myPrevOrbHigh && close[myIndex] > mySessionHigh;

	const myCrossunderLow = myRangeReady && myPrevClose !== null && myPrevOrbLow !== null
		&& myPrevClose >= myPrevOrbLow && close[myIndex] < mySessionLow;

	const myLongCondition = myCanTrade && myCrossoverHigh && (myLastTradeType <= 0);
	const myShortCondition = myCanTrade && myCrossunderLow && (myLastTradeType >= 0);

	if (myLongCondition) {
		myEntryLong[myIndex] = true;
		myPositionSize = 1;
		myPositionAvgPrice = close[myIndex];
		myLastTradeType = 1;
	}
	else if (myShortCondition) {
		myEntryShort[myIndex] = true;
		myPositionSize = -1;
		myPositionAvgPrice = close[myIndex];
		myLastTradeType = -1;
	}
}

paint(myOrbHigh, { name: 'ORB High', color: '#2ecc71', thickness: 2 });
paint(myOrbLow, { name: 'ORB Low', color: '#e74c3c', thickness: 2 });

register_signal(myEntryLong, 'Long Entry');
register_signal(myEntryShort, 'Short Entry');
register_signal(myExitLong, 'Long Exit (TP or SL)');
register_signal(myExitShort, 'Short Exit (TP or SL)');
register_signal(myEodSquareOff, 'EOD Square Off');