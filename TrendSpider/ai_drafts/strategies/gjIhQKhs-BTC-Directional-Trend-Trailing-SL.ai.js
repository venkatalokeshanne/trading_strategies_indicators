describe_indicator('BTC Directional Trend and Trailing SL', 'price');

// Trend/entry EMA lengths, ATR length and trailing multiplier are
// exposed as inputs, matching the original Pine Script parameters.
const myTrendTab = input.tab('Settings');
const myTrendRow = myTrendTab.row();
const myEmaTrendLen = myTrendRow.number('Trend EMA', 200, { min: 1, max: 1000 });
const myEmaEntryLen = myTrendRow.number('Entry EMA', 20, { min: 1, max: 1000 });

const myAtrRow = myTrendTab.row();
const myAtrLen = myAtrRow.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMultiplier = myAtrRow.number('ATR Trailing Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });

// Core indicators
const myEmaTrend = ema(close, myEmaTrendLen);
const myEmaEntry = ema(close, myEmaEntryLen);
const myAtr = atr(high, low, close, myAtrLen);

// Trend direction
const myUptrend = for_every(close, myEmaTrend, (_c, _e) => _c > _e);
const myDowntrend = for_every(close, myEmaTrend, (_c, _e) => _c < _e);

// Crossover / Crossunder of close vs entry EMA, computed manually
// (equivalent to ta.crossover / ta.crossunder in Pine).
const myCloseAboveEntry = for_every(close, myEmaEntry, (_c, _e) => _c > _e);
const myCloseBelowEntry = for_every(close, myEmaEntry, (_c, _e) => _c < _e);

const myLongCondition = series_of(false);
const myShortCondition = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myCrossOver = myCloseAboveEntry[myIndex] && !myCloseAboveEntry[myIndex - 1];
	const myCrossUnder = myCloseBelowEntry[myIndex] && !myCloseBelowEntry[myIndex - 1];
	myLongCondition[myIndex] = myUptrend[myIndex] && myCrossOver;
	myShortCondition[myIndex] = myDowntrend[myIndex] && myCrossUnder;
}

// Trailing stop simulation. Pine's strategy.exit with trail_points /
// trail_offset ratchets a stop level once price moves favorably by
// at least "trail_points", then trails behind price by "trail_offset".
// We approximate this bar-by-bar since there is no native strategy
// trailing-stop engine available in this scripting API.
const myLongExit = series_of(false);
const myShortExit = series_of(false);

let myPositionDirection = 0; // 0 = flat, 1 = long, -1 = short
let myEntryPrice = null;
let myTrailActive = false;
let myTrailStop = null;
let myExtremePrice = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myCurrentAtr = myAtr[myIndex] || 0;
	const myTrailPoints = myCurrentAtr * myAtrMultiplier;
	const myTrailOffset = myCurrentAtr;

	if (myPositionDirection === 0) {
		if (myLongCondition[myIndex]) {
			myPositionDirection = 1;
			myEntryPrice = close[myIndex];
			myTrailActive = false;
			myTrailStop = null;
			myExtremePrice = close[myIndex];
		}
		else if (myShortCondition[myIndex]) {
			myPositionDirection = -1;
			myEntryPrice = close[myIndex];
			myTrailActive = false;
			myTrailStop = null;
			myExtremePrice = close[myIndex];
		}
	}
	else if (myPositionDirection === 1) {
		myExtremePrice = Math.max(myExtremePrice, close[myIndex]);

		if (!myTrailActive && (close[myIndex] - myEntryPrice) >= myTrailPoints) {
			myTrailActive = true;
			myTrailStop = close[myIndex] - myTrailOffset;
		}
		else if (myTrailActive) {
			myTrailStop = Math.max(myTrailStop, myExtremePrice - myTrailOffset);
		}

		if (myTrailActive && close[myIndex] <= myTrailStop) {
			myLongExit[myIndex] = true;
			myPositionDirection = 0;
			myEntryPrice = null;
			myTrailActive = false;
			myTrailStop = null;
		}
		else if (myShortCondition[myIndex]) {
			// Pine allows flipping into opposite entry
			myPositionDirection = -1;
			myEntryPrice = close[myIndex];
			myTrailActive = false;
			myTrailStop = null;
			myExtremePrice = close[myIndex];
		}
	}
	else if (myPositionDirection === -1) {
		myExtremePrice = Math.min(myExtremePrice, close[myIndex]);

		if (!myTrailActive && (myEntryPrice - close[myIndex]) >= myTrailPoints) {
			myTrailActive = true;
			myTrailStop = close[myIndex] + myTrailOffset;
		}
		else if (myTrailActive) {
			myTrailStop = Math.min(myTrailStop, myExtremePrice + myTrailOffset);
		}

		if (myTrailActive && close[myIndex] >= myTrailStop) {
			myShortExit[myIndex] = true;
			myPositionDirection = 0;
			myEntryPrice = null;
			myTrailActive = false;
			myTrailStop = null;
		}
		else if (myLongCondition[myIndex]) {
			myPositionDirection = 1;
			myEntryPrice = close[myIndex];
			myTrailActive = false;
			myTrailStop = null;
			myExtremePrice = close[myIndex];
		}
	}
}

// Plot the two EMAs, matching the original Pine plots
paint(myEmaTrend, { name: 'EMA Trend', color: '#2962FF', thickness: 2 });
paint(myEmaEntry, { name: 'EMA Entry', color: '#FF9800', thickness: 2 });

// Register signals for use in Scanners, Alerts and Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myShortExit, 'Short Exit');