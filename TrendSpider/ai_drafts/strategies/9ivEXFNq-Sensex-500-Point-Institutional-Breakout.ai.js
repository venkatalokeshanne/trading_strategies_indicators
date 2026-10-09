describe_indicator('Sensex 945 3 Trade Limit Breakout', 'price');

// This is a best-effort translation of a Pine Script strategy into
// TrendSpider's indicator model. TrendSpider custom scripts have no
// built-in position/order engine (no strategy.entry/exit equivalent),
// so position state, SL/TP tracking and trade counting are all
// simulated manually inside a single sequential loop over the candles.
// This only works correctly on an intraday timeframe where each candle
// has a real hour/minute (the Pine script assumes the same).

const myIncrement = input.number('Round Number Increment', 500, { min: 1, max: 100000 });
const mySlPoints = input.number('Initial SL', 100, { min: 0, max: 100000 });
const myBeTrigger = input.number('Move to BE Trigger', 200, { min: 0, max: 100000 });
const myMaxTrades = input.number('Max Trades Per Day', 3, { min: 1, max: 50 });
const myStartHour = input.number('Start Hour', 9, { min: 0, max: 23 });
const myStartMinute = input.number('Start Minute', 45, { min: 0, max: 59 });

const myUpperLevel = series_of(null);
const myLowerLevel = series_of(null);
const mySlLine = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myExitSignal = series_of(false);

let myUpper = null;
let myLower = null;
let myTpUpper = null;
let myTpLower = null;
let myActiveSl = null;
let myTrailActivated = false;
let myTradeCount = 0;
let myPositionSize = 0; // 0 none, 1 long, -1 short
let myAvgPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myIsStartTime = myTimeInfo.hours === myStartHour && myTimeInfo.minutes === myStartMinute;

	// trading window 09:45 to 15:15 (inclusive-ish, matching Pine's time() range)
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const mySessionStartMinutes = myStartHour * 60 + myStartMinute;
	const mySessionEndMinutes = 15 * 60 + 15;
	const myCanTrade = myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay <= mySessionEndMinutes;

	// EOD close window 15:25 to 15:30
	const myIsEodWindow = myMinutesOfDay >= (15 * 60 + 25) && myMinutesOfDay <= (15 * 60 + 30);

	if (myIsStartTime) {
		const myCurrentPrice = open[myIndex];
		myLower = Math.floor(myCurrentPrice / myIncrement) * myIncrement;
		myUpper = Math.ceil(myCurrentPrice / myIncrement) * myIncrement;
		myTpUpper = myUpper + myIncrement;
		myTpLower = myLower - myIncrement;
		myTrailActivated = false;
		myTradeCount = 0;
	}

	const myLongCondition = !myIsStartTime && myUpper !== null && close[myIndex] >= myUpper && myCanTrade && myPositionSize === 0 && myTradeCount < myMaxTrades;
	const myShortCondition = !myIsStartTime && myLower !== null && close[myIndex] <= myLower && myCanTrade && myPositionSize === 0 && myTradeCount < myMaxTrades;

	if (myLongCondition) {
		myPositionSize = 1;
		myAvgPrice = close[myIndex];
		myActiveSl = close[myIndex] - mySlPoints;
		myTrailActivated = false;
		myTradeCount += 1;
		myLongSignal[myIndex] = true;
	}
	else if (myShortCondition) {
		myPositionSize = -1;
		myAvgPrice = close[myIndex];
		myActiveSl = close[myIndex] + mySlPoints;
		myTrailActivated = false;
		myTradeCount += 1;
		myShortSignal[myIndex] = true;
	}

	if (myPositionSize > 0 && !myTrailActivated && high[myIndex] >= myAvgPrice + myBeTrigger) {
		myActiveSl = myAvgPrice;
		myTrailActivated = true;
	}
	if (myPositionSize < 0 && !myTrailActivated && low[myIndex] <= myAvgPrice - myBeTrigger) {
		myActiveSl = myAvgPrice;
		myTrailActivated = true;
	}

	// Exit checks (stop or limit hit), evaluated using current candle's range
	let myExitedThisBar = false;
	if (myPositionSize > 0) {
		if (low[myIndex] <= myActiveSl || high[myIndex] >= myTpUpper) {
			myExitedThisBar = true;
		}
	}
	else if (myPositionSize < 0) {
		if (high[myIndex] >= myActiveSl || low[myIndex] <= myTpLower) {
			myExitedThisBar = true;
		}
	}

	// EOD forced close
	if (myPositionSize !== 0 && myIsEodWindow) {
		myExitedThisBar = true;
	}

	if (myExitedThisBar && myPositionSize !== 0) {
		myExitSignal[myIndex] = true;
		myPositionSize = 0;
		myAvgPrice = null;
		myActiveSl = null;
	}

	myUpperLevel[myIndex] = myUpper;
	myLowerLevel[myIndex] = myLower;
	mySlLine[myIndex] = myPositionSize !== 0 ? myActiveSl : null;
}

paint(myUpperLevel, { name: 'Entry High', color: '#2ca599', thickness: 2, style: 'line' });
paint(myLowerLevel, { name: 'Entry Low', color: '#ee5451', thickness: 2, style: 'line' });
paint(mySlLine, { name: 'Stop Loss', color: 'red', thickness: 2, style: 'dotted' });

register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myExitSignal, 'Trade Exit');