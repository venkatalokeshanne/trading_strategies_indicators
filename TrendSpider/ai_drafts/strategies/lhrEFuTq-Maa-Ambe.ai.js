describe_indicator('SENSEX Disciplined Sniper V4', 'price');

// This indicator is a port of a Pine Script STRATEGY, not an indicator.
// Custom JS API does not support strategy.entry/strategy.exit (actual
// order management, qty, limit/stop exits). We approximate the trade
// state machine (tradesToday counter, "flat" state before next signal,
// target/stop) using only candle close prices (no intrabar fills).
// Signals (buyCE / buyPE) and exit conditions are exposed via
// register_signal() so they can be used in Scanners / Alerts / Strategy
// Tester. Position sizing, PnL in rupees and order comments are not
// reproducible in this engine and are omitted.

const myNumLots = input.number('Number Of Lots', 5, { min: 1, max: 100 });
const myMaxDaily = input.number('Max Daily Trades', 4, { min: 1, max: 50 });
const myTargetPoints = input.number('Target Points', 80, { min: 1, max: 1000 });
const myStopPoints = input.number('Stop Points', 80, { min: 1, max: 1000 });

const myUnitsPerLot = 20;
const myTotalUnits = myNumLots * myUnitsPerLot;

// --- core series ---
const myEma200 = ema(close, 200);
const myRsi = rsi(close, 14);
const myVolSma = sma(volume, 20);
const myAdxObject = indicators.adx(14);
const myAdx = myAdxObject.adx;

// --- time window + day tracking, computed once per candle ---
const myDayId = time.map(_t => bar_at(_t).session);
const myIsTradeWindow = time.map(_t => {
	const myTimeParts = time_of(_t);
	const myMinutesOfDay = myTimeParts.hours * 60 + myTimeParts.minutes;
	const mySession1Start = 9 * 60 + 20;
	const mySession1End = 12 * 60 + 0;
	const mySession2Start = 13 * 60 + 30;
	const mySession2End = 14 * 60 + 30;
	const myInSession1 = myMinutesOfDay >= mySession1Start && myMinutesOfDay <= mySession1End;
	const myInSession2 = myMinutesOfDay >= mySession2Start && myMinutesOfDay <= mySession2End;
	return myInSession1 || myInSession2;
});

// --- state machine replicating tradesToday + "flat position" gating ---
const myBuyCeSeries = series_of(false);
const myBuyPeSeries = series_of(false);
const myExitSeries = series_of(false);

let myTradesToday = 0;
let myCurrentDay = null;
let myPositionDirection = 0; // 0 flat, 1 long(CE), -1 short(PE)
let myEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myDayId[myIndex] !== myCurrentDay) {
		myCurrentDay = myDayId[myIndex];
		myTradesToday = 0;
	}

	// manage exit of an existing simulated position (close-based only)
	if (myPositionDirection !== 0) {
		const myCurrentClose = close[myIndex];
		let myExitHit = false;

		if (myPositionDirection === 1) {
			if (myCurrentClose >= myEntryPrice + myTargetPoints || myCurrentClose <= myEntryPrice - myStopPoints) {
				myExitHit = true;
			}
		}
		else {
			if (myCurrentClose <= myEntryPrice - myTargetPoints || myCurrentClose >= myEntryPrice + myStopPoints) {
				myExitHit = true;
			}
		}

		if (myExitHit) {
			myExitSeries[myIndex] = true;
			myPositionDirection = 0;
			myEntryPrice = null;
		}
	}

	const myCanTrade = myIsTradeWindow[myIndex] && myTradesToday < myMaxDaily && myPositionDirection === 0;
	const myIsTrending = myAdx[myIndex] > 20;
	const myIsHighVol = volume[myIndex] > myVolSma[myIndex];

	const myBuyCe = myCanTrade && close[myIndex] > myEma200[myIndex] && myRsi[myIndex] > 60 && myIsTrending && myIsHighVol;
	const myBuyPe = myCanTrade && close[myIndex] < myEma200[myIndex] && myRsi[myIndex] < 40 && myIsTrending && myIsHighVol;

	if (myBuyCe) {
		myBuyCeSeries[myIndex] = true;
		myPositionDirection = 1;
		myEntryPrice = close[myIndex];
		myTradesToday += 1;
	}
	else if (myBuyPe) {
		myBuyPeSeries[myIndex] = true;
		myPositionDirection = -1;
		myEntryPrice = close[myIndex];
		myTradesToday += 1;
	}
}

// --- visual output ---
paint(myEma200, { name: 'EMA200', color: '#FFD54F', thickness: 1, style: 'line' });

const myBuyCeMarks = for_every(close, myBuyCeSeries, (_c, _b) => _b ? _c : null);
const myBuyPeMarks = for_every(close, myBuyPeSeries, (_c, _b) => _b ? _c : null);

paint(myBuyCeMarks, { name: 'Buy CE', color: '#26A69A', style: 'labels_below' });
paint(myBuyPeMarks, { name: 'Buy PE', color: '#EF5350', style: 'labels_above' });

// --- signals for scanners, alerts and strategy tester ---
register_signal(myBuyCeSeries, 'Buy CE Signal');
register_signal(myBuyPeSeries, 'Buy PE Signal');
register_signal(myExitSeries, 'Exit Position Signal');