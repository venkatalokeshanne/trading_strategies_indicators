describe_indicator('EURUSD Sniper v8.7 (Pine Conversion)', 'price', { decimals: 5 });

// --- This is a best effort line-by-line port of a Pine Script v5 strategy ---
// A few things cannot be reproduced identically in TrendSpider Custom JS:
//  - strategy.entry / strategy.exit / strategy.close_all are a backtest
//    engine construct. There is no equivalent order/position management
//    engine here. We instead simulate position state in a plain loop and
//    expose the same decision points as signals (register_signal), which
//    is the closest equivalent usable in Scanners/Alerts/Strategy Tester.
//  - syminfo.mintick is not exposed by the API, so pip size is assumed to
//    be 0.0001 (standard 5-decimal FX quoting for EURUSD).
//  - time(timeframe.period, session, timezone) session matching and the
//    Asia/Kolkata timezone conversion are approximated using moment-timezone.
//  - bgcolor() / line.new() visual-only elements from Pine are dropped;
//    they have no bearing on signals and are not representable the same way.

const myMoment = library('moment-timezone');

// --- Inputs ---
const tabBacktest = input.tab('Backtest Settings');
const myLookbackDays = tabBacktest.number('Backtest Lookback (Days)', 90, { min: 1, max: 3650 });

const tabStrategy = input.tab('Strategy Parameters');
const myTpPips = tabStrategy.number('Take Profit (Pips)', 35, { min: 1, max: 1000 });
const mySlPips = tabStrategy.number('Stop Loss (Pips)', 18, { min: 1, max: 1000 });
const myBeTriggerPips = tabStrategy.number('Breakeven Trigger (Pips)', 12, { min: 1, max: 1000 });

const tabTime = input.tab('Time Settings');
const mySessionStart = tabTime.text('Session Start (HHMM)', '1130');
const mySessionEnd = tabTime.text('Session End (HHMM)', '2200');

// Timezone is hardcoded exactly as in the Pine script.
const myTimezone = 'Asia/Kolkata';

// --- Indicators ---
const myBasis = sma(close, 20);
const myDev = mult(stdev(close, 20), 2.0);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);
const myEma200 = ema(close, 200);
const myRsi = rsi(close, 14);

// Assumed pip size for EURUSD (5-decimal quoting).
const myPip = 0.0001;
const myTpDist = myTpPips * myPip;
const mySlDist = mySlPips * myPip;
const myBeDist = myBeTriggerPips * myPip;

// --- Backtest range filter ---
const myLastBarTime = time[time.length - 1];
const myStartTime = myLastBarTime - (myLookbackDays * 24 * 60 * 60);

// --- Helper: parse HHMM strings ---
function myParseHHMM(_text) {
	const myNum = parseInt(_text, 10);
	return { hours: Math.floor(myNum / 100), minutes: myNum % 100 };
}
const mySessionStartParsed = myParseHHMM(mySessionStart);
const mySessionEndParsed = myParseHHMM(mySessionEnd);

// --- Build per-candle session/day/time info using moment-timezone ---
const myCandleCount = close.length;
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myExitSignal = series_of(false);
const myPositionDirection = series_of(0); // 0 flat, 1 long, -1 short
const myStopLevel = series_of(null);
const myTpLevel = series_of(null);

let myCurrentDirection = 0;
let myEntryPrice = null;
let myStopPrice = null;
let myTradesToday = 0;
let myPrevDayKey = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTimestampSec = time[myIndex];
	const myLocalMoment = myMoment.tz(myTimestampSec * 1000, myTimezone);

	const myDayKey = myLocalMoment.format('YYYY-MM-DD');
	if (myDayKey !== myPrevDayKey) {
		myTradesToday = 0;
		myPrevDayKey = myDayKey;
	}

	const myMinutesOfDay = myLocalMoment.hours() * 60 + myLocalMoment.minutes();
	const mySessionStartMinutes = mySessionStartParsed.hours * 60 + mySessionStartParsed.minutes;
	const mySessionEndMinutes = mySessionEndParsed.hours * 60 + mySessionEndParsed.minutes;

	const myIsInSession = mySessionEndMinutes >= mySessionStartMinutes
		? (myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay <= mySessionEndMinutes)
		: (myMinutesOfDay >= mySessionStartMinutes || myMinutesOfDay <= mySessionEndMinutes);

	const myIsEOD = myLocalMoment.hours() === 21 && myLocalMoment.minutes() >= 45;
	const myIsWithinTime = myTimestampSec >= myStartTime;

	const myRsiValue = myRsi[myIndex];
	const myEma200Value = myEma200[myIndex];
	const myLowerValue = myLower[myIndex];
	const myUpperValue = myUpper[myIndex];

	const myLongCondition = myIsWithinTime && myIsInSession && myTradesToday < 1
		&& low[myIndex] <= myLowerValue && close[myIndex] > myEma200Value && myRsiValue < 45;

	const myShortCondition = myIsWithinTime && myIsInSession && myTradesToday < 1
		&& high[myIndex] >= myUpperValue && close[myIndex] < myEma200Value && myRsiValue > 55;

	// Entries, only when flat
	if (myCurrentDirection === 0 && myLongCondition) {
		myCurrentDirection = 1;
		myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice - mySlDist;
		myTradesToday = 1;
		myLongSignal[myIndex] = true;
	}
	else if (myCurrentDirection === 0 && myShortCondition) {
		myCurrentDirection = -1;
		myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice + mySlDist;
		myTradesToday = 1;
		myShortSignal[myIndex] = true;
	}

	// Exit management (breakeven + tp/sl + EOD) when in a position
	if (myCurrentDirection === 1) {
		const myReachBE = (high[myIndex] - myEntryPrice) >= myBeDist;
		myStopPrice = myReachBE ? myEntryPrice : (myEntryPrice - mySlDist);
		const myTpPrice = myEntryPrice + myTpDist;

		const myHitStop = low[myIndex] <= myStopPrice;
		const myHitTp = high[myIndex] >= myTpPrice;

		if (myHitStop || myHitTp || myIsEOD) {
			myExitSignal[myIndex] = true;
			myCurrentDirection = 0;
			myEntryPrice = null;
			myStopPrice = null;
		}
	}
	else if (myCurrentDirection === -1) {
		const myReachBE = (myEntryPrice - low[myIndex]) >= myBeDist;
		myStopPrice = myReachBE ? myEntryPrice : (myEntryPrice + mySlDist);
		const myTpPrice = myEntryPrice - myTpDist;

		const myHitStop = high[myIndex] >= myStopPrice;
		const myHitTp = low[myIndex] <= myTpPrice;

		if (myHitStop || myHitTp || myIsEOD) {
			myExitSignal[myIndex] = true;
			myCurrentDirection = 0;
			myEntryPrice = null;
			myStopPrice = null;
		}
	}

	myPositionDirection[myIndex] = myCurrentDirection;
	myStopLevel[myIndex] = myStopPrice;
	myTpLevel[myIndex] = myCurrentDirection === 1
		? (myEntryPrice + myTpDist)
		: (myCurrentDirection === -1 ? (myEntryPrice - myTpDist) : null);
}

// --- Visuals ---
paint(myUpper, { name: 'BB Upper', color: '#ff5252', thickness: 1 });
paint(myLower, { name: 'BB Lower', color: '#26a69a', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: '#ffffff', thickness: 2 });
paint(myStopLevel, { name: 'Stop Level', color: '#ef5350', style: 'dotted', thickness: 1 });
paint(myTpLevel, { name: 'Take Profit Level', color: '#26a69a', style: 'dotted', thickness: 1 });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(myLongSignal, 'Sniper Buy');
register_signal(myShortSignal, 'Sniper Sell');
register_signal(myExitSignal, 'Sniper Exit');