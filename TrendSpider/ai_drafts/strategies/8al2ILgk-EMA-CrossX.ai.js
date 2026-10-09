describe_indicator('EMA CrossX (Pine Conversion)', 'price');

// This indicator reproduces the EMA cross + delayed entry logic
// of the original Pine strategy. TrendSpider Custom JS indicators
// cannot place orders, track strategy equity, or run a real
// strategy.exit() engine (trailing/fixed stop/limit orders) --
// only TrendSpider's native Strategy Tester component can do that.
// Below, we replicate the entry/exit LOGIC using a bar-by-bar
// simulation (positions tracked manually in a loop) so you get the
// exact same signal bars, and we expose them via register_signal()
// so they can be used in Scanners / Alerts.

const myFastLen = input.number('Fast EMA Length', 9, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 19, { min: 1, max: 500 });
const myWaitBars = input.number('Entry Delay (Candles)', 2, { min: 0, max: 100 });

const myTakeProfitPoints = input.number('Take Profit (Points)', 4.0, { min: 0, max: 10000 });
const myStopLossPoints = input.number('Stop Loss (Points)', 2.5, { min: 0, max: 10000 });

const myUseTrailing = input.boolean('Enable Trailing Stop (Overrides Fixed TP)', true);
const myTrailingDistPts = input.number('Trailing Distance (Points)', 1.0, { min: 0, max: 10000 });

// --- Calculations ---
const myEmaFast = ema(close, myFastLen);
const myEmaSlow = ema(close, mySlowLen);

paint(myEmaFast, { name: 'EMA Fast', color: '#2962FF', thickness: 1 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#FF9800', thickness: 1 });

// ta.crossover(emaFast, emaSlow): fast crosses above slow this bar
const myCrossHappened = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myEmaFast[_index - 1];
	const myPrevSlow = myEmaSlow[_index - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

// crossHappened[waitBars]: value from waitBars candles ago
const myEnterLong = shift(myCrossHappened, myWaitBars);

// --- Manual bar-by-bar position/exit simulation (approximation of strategy.exit) ---
// State: 0 = flat, 1 = long. We track entry price, SL and TP/trail levels.
let myPositionState = 0;
let myEntryPrice = null;
let mySlLevel = null;
let myTpLevel = null;
let myTrailHigh = null;

const myExitSignal = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPositionState === 0) {
		if (myEnterLong[myIndex]) {
			myPositionState = 1;
			myEntryPrice = close[myIndex];
			mySlLevel = myEntryPrice - myStopLossPoints;
			myTpLevel = myEntryPrice + myTakeProfitPoints;
			myTrailHigh = high[myIndex];
		}
	}
	else if (myPositionState === 1) {
		let myExitNow = false;

		if (myUseTrailing) {
			myTrailHigh = Math.max(myTrailHigh, high[myIndex]);
			const myTrailStopLevel = myTrailHigh - myTrailingDistPts;
			// strict stop (fixed SL) OR trailing stop breach
			if (low[myIndex] <= mySlLevel || low[myIndex] <= myTrailStopLevel) {
				myExitNow = true;
			}
		}
		else {
			if (low[myIndex] <= mySlLevel || high[myIndex] >= myTpLevel) {
				myExitNow = true;
			}
		}

		if (myExitNow) {
			myExitSignal[myIndex] = true;
			myPositionState = 0;
			myEntryPrice = null;
			mySlLevel = null;
			myTpLevel = null;
			myTrailHigh = null;
		}
	}
}

// --- Visual confirmation (shapes below bars) ---
const myCrossShapes = for_every(myCrossHappened, _c => _c ? constants.icons.circle : null);
const myBuyShapes = for_every(myEnterLong, _e => _e ? constants.icons.triangle_up : null);

paint(myCrossShapes, { name: 'Cross', style: 'labels_below', color: 'gray' });
paint(myBuyShapes, { name: 'Buy', style: 'labels_below', color: 'green' });

// --- Signals for Scanners / Alerts / Strategy Tester ---
register_signal(myCrossHappened, 'EMA Cross');
register_signal(myEnterLong, 'Enter Long (Delayed)');
register_signal(myExitSignal, 'Exit Long (Simulated)');