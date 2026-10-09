describe_indicator('Nifty 10 Candle ORB v4 Alternating Trades', 'overlay');

// NOTE: This indicator approximates the original Pine Script strategy.
// TrendSpider Custom JS does not have a built-in strategy/broker engine
// with intrabar order fills, so position/TP/SL simulation below is done
// manually, bar by bar, using close/high/low of each candle. When both
// a Stop Loss and a Take Profit are touched within the same candle, we
// conservatively assume the Stop Loss fills first (Pine's intrabar fill
// order is not deterministic/reproducible outside of its own engine).

const myTab = input.tab('ORB Settings');

const myTpPercent = myTab.number('Profit Target Percent', 1.0, { min: 0.1, max: 50, step: 0.1 });
const mySlPercent = myTab.number('Stop Loss Percent', 0.5, { min: 0.1, max: 50, step: 0.1 });
const myNumCandles = myTab.number('Number Of Opening Candles', 10, { min: 1, max: 100 });

const myTimeRow = myTab.row();
const myExitHour = myTimeRow.number('Exit Hour', 15, { min: 0, max: 23 });
const myExitMinute = myTimeRow.number('Exit Minute', 15, { min: 0, max: 59 });
const myLastTradeHour = myTimeRow.number('Last Entry Hour', 15, { min: 0, max: 23 });

const myLen = close.length;

const myOrbHigh = series_of(null);
const myOrbLow = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myExitLongSignal = series_of(false);
const myExitShortSignal = series_of(false);

let mySessionHigh = null;
let mySessionLow = null;
let myCandleIdx = 0;
let myLastTradeType = 0;
let myPositionSize = 0;
let myEntryPrice = null;
let myLongTP = null;
let myLongSL = null;
let myShortTP = null;
let myShortSL = null;
let myPrevDaySession = null;

for (let myIndex = 0; myIndex < myLen; myIndex += 1) {
	const myDayInfo = bar_at(time[myIndex]);
	const myIsNewDay = myPrevDaySession !== null && myDayInfo.session !== myPrevDaySession;
	myPrevDaySession = myDayInfo.session;

	if (myIsNewDay) {
		mySessionHigh = null;
		mySessionLow = null;
		myCandleIdx = 0;
		myLastTradeType = 0;
		myPositionSize = 0;
		myEntryPrice = null;
	}

	if (myCandleIdx < myNumCandles) {
		myCandleIdx += 1;
		mySessionHigh = (mySessionHigh === null) ? high[myIndex] : Math.max(mySessionHigh, high[myIndex]);
		mySessionLow = (mySessionLow === null) ? low[myIndex] : Math.min(mySessionLow, low[myIndex]);
	}

	const myRangeLocked = myCandleIdx >= myNumCandles;
	myOrbHigh[myIndex] = myRangeLocked ? mySessionHigh : null;
	myOrbLow[myIndex] = myRangeLocked ? mySessionLow : null;

	const myTimeInfo = time_of(time[myIndex]);
	const myCurrentTime = (myTimeInfo.hours * 100) + myTimeInfo.minutes;
	const myIsExitTime = myCurrentTime >= ((myExitHour * 100) + myExitMinute);
	const myCanEnter = myCurrentTime < (myLastTradeHour * 100);

	// Process open position: exits (TP / SL) first, then forced EOD close
	if (myPositionSize > 0) {
		const myHitSL = low[myIndex] <= myLongSL;
		const myHitTP = high[myIndex] >= myLongTP;
		if (myHitSL || myHitTP) {
			myExitLongSignal[myIndex] = true;
			myPositionSize = 0;
			myEntryPrice = null;
		}
	}
	else if (myPositionSize < 0) {
		const myHitSL = high[myIndex] >= myShortSL;
		const myHitTP = low[myIndex] <= myShortTP;
		if (myHitSL || myHitTP) {
			myExitShortSignal[myIndex] = true;
			myPositionSize = 0;
			myEntryPrice = null;
		}
	}

	if (myIsExitTime && myPositionSize !== 0) {
		if (myPositionSize > 0) {
			myExitLongSignal[myIndex] = true;
		}
		else {
			myExitShortSignal[myIndex] = true;
		}
		myPositionSize = 0;
		myEntryPrice = null;
	}

	const myCanTrade = myRangeLocked && (myPositionSize === 0) && myCanEnter && !myIsExitTime;
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;

	const myLongCondition = myCanTrade
		&& myPrevClose !== null
		&& close[myIndex] > mySessionHigh
		&& myPrevClose <= mySessionHigh
		&& myLastTradeType <= 0;

	const myShortCondition = myCanTrade
		&& myPrevClose !== null
		&& close[myIndex] < mySessionLow
		&& myPrevClose >= mySessionLow
		&& myLastTradeType >= 0;

	if (myLongCondition) {
		myPositionSize = 1;
		myEntryPrice = close[myIndex];
		myLongTP = myEntryPrice * (1 + (myTpPercent / 100));
		myLongSL = myEntryPrice * (1 - (mySlPercent / 100));
		myLastTradeType = 1;
		myLongEntrySignal[myIndex] = true;
	}
	else if (myShortCondition) {
		myPositionSize = -1;
		myEntryPrice = close[myIndex];
		myShortTP = myEntryPrice * (1 - (myTpPercent / 100));
		myShortSL = myEntryPrice * (1 + (mySlPercent / 100));
		myLastTradeType = -1;
		myShortEntrySignal[myIndex] = true;
	}
}

paint(myOrbHigh, { name: 'ORB High', color: '#26A69A', thickness: 2, style: 'line' });
paint(myOrbLow, { name: 'ORB Low', color: '#EF5350', thickness: 2, style: 'line' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myExitLongSignal, 'Exit Long');
register_signal(myExitShortSignal, 'Exit Short');