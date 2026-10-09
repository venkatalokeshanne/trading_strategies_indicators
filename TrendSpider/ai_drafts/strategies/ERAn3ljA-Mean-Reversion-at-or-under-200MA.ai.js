describe_indicator('MES 30m EMA9 SMA200 Retest Dynamic Cap', 'price');

// NOTE: TrendSpider Custom JS does not have a strategy engine
// (no strategy.entry/strategy.exit/position sizing/order management).
// This script reproduces the Pine Script's INDICATOR logic (EMA/SMA/ATR,
// slope flips, armed/retest zone, entry condition) exactly, and
// APPROXIMATES the position management/exit logic with a simplified
// state machine so that entry/exit signals can be scanned/alerted on.
// Real position sizing, partial exits (TP1/TP2/TP3), break-even stop
// and trailing stop are not actually simulated as separate orders -
// they are approximated into a single simplified exit signal.

// NOTE: the hard assert() that previously blocked execution on any
// timeframe other than 30min has been removed, because it made the
// indicator throw a fatal error whenever applied to a non-30m chart
// (which happens easily, e.g. default chart timeframe, MTFA, or just
// browsing). The logic itself is still designed and tuned for the
// 30-minute timeframe; we now just flag that visually/via a signal
// instead of crashing, so the indicator stays usable everywhere.
const myIsCorrectTimeframe = current.resolution == '30';

const myEma9 = ema(close, 9);
const mySma200 = sma(close, 200);
const myAtr = atr(high, low, close, 14);
const myCandleCount = close.length;

// Output series (stateful, computed via a single forward loop because
// of the dependency on previous candle's armed/trackedLow/trackedHigh state)
const myTrackedLow = series_of(null);
const myTrackedHigh = series_of(null);
const myArmed = series_of(false);
const myLongSetup = series_of(false);
const myUpperCap = series_of(null);
const myRetestPrice = series_of(null);
const myInRetestZone = series_of(false);
const myReclaimMomentum = series_of(false);
const myLongEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myDefensiveSignal = series_of(false);
const myPositionActive = series_of(false);
let myPositionSize = 0;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myPrevArmed = myIndex > 0 ? myArmed[myIndex - 1] : false;
	const myPrevTrackedLow = myIndex > 0 ? myTrackedLow[myIndex - 1] : null;
	const myPrevTrackedHigh = myIndex > 0 ? myTrackedHigh[myIndex - 1] : null;
	const myEmaSlope = myIndex > 0 ? (myEma9[myIndex] - myEma9[myIndex - 1]) : null;
	const myEmaSlopePrev = myIndex > 1 ? (myEma9[myIndex - 1] - myEma9[myIndex - 2]) : null;
	const mySlopeUp = (myEmaSlope != null && myEmaSlopePrev != null) ? (myEmaSlope > 0 && myEmaSlopePrev <= 0) : false;
	const mySlopeDown = (myEmaSlope != null && myEmaSlopePrev != null) ? (myEmaSlope < 0 && myEmaSlopePrev >= 0) : false;
	const myIsLocalLow = myIndex > 0 ? (close[myIndex] > open[myIndex] && close[myIndex - 1] < open[myIndex - 1]) : false;
	const myIsLocalHigh = myIndex > 0 ? (close[myIndex] < open[myIndex] && close[myIndex - 1] > open[myIndex - 1]) : false;

	let myCurrentTrackedLow = myPrevTrackedLow;
	let myCurrentTrackedHigh = myPrevTrackedHigh;

	if (myIsLocalLow && myIndex > 0) {
		myCurrentTrackedLow = Math.min(low[myIndex], low[myIndex - 1]);
	}
	if (myIsLocalHigh && myIndex > 0) {
		myCurrentTrackedHigh = Math.max(high[myIndex], high[myIndex - 1]);
	}

	myTrackedLow[myIndex] = myCurrentTrackedLow;
	myTrackedHigh[myIndex] = myCurrentTrackedHigh;

	const myTouchEvent = (myEma9[myIndex] <= mySma200[myIndex]) || (close[myIndex] <= mySma200[myIndex]);
	let myCurrentArmed = myPrevArmed;

	if (myTouchEvent) {
		myCurrentArmed = true;
	}

	const myCurrentLongSetup = myCurrentArmed && mySlopeUp;

	if (myCurrentLongSetup) {
		myCurrentArmed = false;
	}

	myArmed[myIndex] = myCurrentArmed;
	myLongSetup[myIndex] = myCurrentLongSetup;

	const myCurrentUpperCap = (myEma9[myIndex] < mySma200[myIndex])
		? (myCurrentTrackedHigh != null ? Math.min(myCurrentTrackedHigh, mySma200[myIndex]) : mySma200[myIndex])
		: mySma200[myIndex];

	myUpperCap[myIndex] = myCurrentUpperCap;

	const myCurrentRetestPrice = (myCurrentTrackedLow != null && myCurrentUpperCap != null)
		? (myCurrentTrackedLow + (myCurrentUpperCap - myCurrentTrackedLow) * 0.30)
		: null;

	myRetestPrice[myIndex] = myCurrentRetestPrice;

	const myCurrentInRetestZone = (myCurrentRetestPrice != null)
		&& (low[myIndex] <= myCurrentUpperCap)
		&& (high[myIndex] >= myCurrentRetestPrice);

	myInRetestZone[myIndex] = myCurrentInRetestZone;

	const myPrevHigh = myIndex > 0 ? high[myIndex - 1] : null;
	const myCurrentReclaimMomentum = (close[myIndex] > myEma9[myIndex]) || (myPrevHigh != null && close[myIndex] > myPrevHigh);
	myReclaimMomentum[myIndex] = myCurrentReclaimMomentum;

	// ===== Simplified position/entry/exit state machine =====
	// Entry/exit signals are only allowed to fire on the intended
	// 30-minute timeframe; on any other timeframe they stay false,
	// but all lines/signals are still painted/registered consistently.
	let myEntrySignal = false;
	let myExitSignal = false;
	let myDefensiveFlag = false;

	if (myIsCorrectTimeframe) {
		if (myCurrentLongSetup && myPositionSize === 0) {
			if (myCurrentInRetestZone && myCurrentReclaimMomentum) {
				myEntrySignal = true;
			}
			else if (close[myIndex] > mySma200[myIndex] && myCurrentReclaimMomentum) {
				myEntrySignal = true;
			}
		}

		if (myEntrySignal) {
			myPositionSize = 10;
			myEntryPrice = close[myIndex];
		}

		if (myPositionSize > 0) {
			if (mySlopeDown) {
				myDefensiveFlag = true;
				// Approximated defensive exit: stop at trackedLow - 0.5*ATR, target trackedHigh
				const myDefStop = myCurrentTrackedLow != null ? (myCurrentTrackedLow - myAtr[myIndex] * 0.5) : null;
				const myDefTarget = myCurrentTrackedHigh;

				if ((myDefStop != null && low[myIndex] <= myDefStop) || (myDefTarget != null && high[myIndex] >= myDefTarget)) {
					myExitSignal = true;
					myPositionSize = 0;
					myEntryPrice = null;
				}
			}
			else if (myEntryPrice != null) {
				// Approximated full exit once price reaches furthest target (TP3 @ +20)
				if (high[myIndex] >= myEntryPrice + 20) {
					myExitSignal = true;
					myPositionSize = 0;
					myEntryPrice = null;
				}
			}
		}
	}

	myLongEntrySignal[myIndex] = myEntrySignal;
	myLongExitSignal[myIndex] = myExitSignal;
	myDefensiveSignal[myIndex] = myDefensiveFlag;
	myPositionActive[myIndex] = myPositionSize > 0;
}

paint(myEma9, { name: 'EMA9', color: '#2962FF', thickness: 2 });
paint(mySma200, { name: 'SMA200', color: '#FF9800', thickness: 2 });
paint(myRetestPrice, { name: 'RetestPrice', color: '#9C27B0', thickness: 1, style: 'dotted' });
paint(myUpperCap, { name: 'UpperCap', color: '#F44336', thickness: 1, style: 'dotted' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myDefensiveSignal, 'Defensive Mode Active');
register_signal(myPositionActive, 'Position Active');
register_signal(myLongSetup, 'Long Setup');
register_signal(myInRetestZone, 'In Retest Zone');