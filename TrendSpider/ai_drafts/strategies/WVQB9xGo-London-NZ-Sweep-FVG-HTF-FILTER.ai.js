// Converted from a TradingView Pine Script strategy. The Custom JS API has
// no concept of broker orders, equity or position sizing, so this script
// reproduces the SIGNAL LOGIC exactly (same bars/values for bias, sweep,
// displacement, FVG and buy/sell triggers) and exposes them as paintable
// series plus register_signal() outputs usable in scanners/alerts.
// Position sizing, strategy.entry/exit, equity curve and PnL are NOT
// reproducible in an indicator and are therefore omitted.
describe_indicator('London NZ Sweep FVG HTF Filter', 'lower');

const myTimezone = input.text('Timezone', 'Pacific/Auckland');
const myAsiaStart = input.number('Asia Start HHMM', 1300, { min: 0, max: 2359 });
const myAsiaEnd = input.number('Asia End HHMM', 1900, { min: 0, max: 2359 });
const myLondonStart = input.number('London Start HHMM', 2000, { min: 0, max: 2359 });
const myLondonEnd = input.number('London End HHMM', 2200, { min: 0, max: 2359 });
const myRR = input.number('RR', 3, { min: 0.1, max: 20 });
const myHtfLength = input.number('HTF SMA Length', 20, { min: 1, max: 300 });

const moment = library('moment-timezone');

// ===== HTF (60min) BIAS =====
const myHtfData = await request.history(current.ticker, '60');
assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);

const myHtfSma = sma(myHtfData.close, myHtfLength);
const myHtfCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.close, time, 'le'),
	'constant'
);
const myHtfSmaLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfSma, time, 'le'),
	'constant'
);

const myBullBias = for_every(myHtfCloseLanded, myHtfSmaLanded, (_c, _s) => _c != null && _s != null && _c > _s);
const myBearBias = for_every(myHtfCloseLanded, myHtfSmaLanded, (_c, _s) => _c != null && _s != null && _c < _s);

// ===== SESSION DETECTION (based on provided timezone) =====
const myHHMM = time.map(_t => {
	const myLocal = moment.unix(_t).tz(myTimezone);
	return myLocal.hours() * 100 + myLocal.minutes();
});

const myInAsia = myHHMM.map(_h => _h >= myAsiaStart && _h < myAsiaEnd);
const myInLondon = myHHMM.map(_h => _h >= myLondonStart && _h < myLondonEnd);

// ===== ATR / DISPLACEMENT / FVG =====
const myAtr14 = atr(high, low, close, 14);
const myBullDisplacement = for_every(close, open, myAtr14, (_c, _o, _a) => _c > _o && Math.abs(_c - _o) > _a);
const myBearDisplacement = for_every(close, open, myAtr14, (_c, _o, _a) => _c < _o && Math.abs(_c - _o) > _a);

const myHigh2 = shift(high, 2);
const myLow2 = shift(low, 2);
const myBullFVG = for_every(low, myHigh2, (_l, _h2) => _h2 != null && _l > _h2);
const myBearFVG = for_every(high, myLow2, (_h, _l2) => _l2 != null && _h < _l2);

// ===== STATEFUL LOGIC: ASIA RANGE, SWEEP, TRADE STATE =====
// This part depends on the previous candle's state (session range, sweep
// direction, whether a trade was already taken this London session), so it
// is implemented as a sequential loop over candle indexes, mirroring the
// Pine Script's "var" persisted state exactly.
const myCandleCount = close.length;

const myAsiaHigh = series_of(null);
const myAsiaLow = series_of(null);
const mySweepDirArr = series_of(0);
const myTradeTakenArr = series_of(false);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myEntryArr = series_of(null);
const mySlArr = series_of(null);
const myTpArr = series_of(null);

let myRunningAsiaHigh = null;
let myRunningAsiaLow = null;
let mySweepDir = 0;
let myTradeTaken = false;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myWasInAsia = myIndex > 0 ? myInAsia[myIndex - 1] : false;
	const myWasInLondon = myIndex > 0 ? myInLondon[myIndex - 1] : false;

	const myAsiaStartedNow = myInAsia[myIndex] && !myWasInAsia;
	const myLondonStartedNow = myInLondon[myIndex] && !myWasInLondon;

	if (myAsiaStartedNow) {
		myRunningAsiaHigh = high[myIndex];
		myRunningAsiaLow = low[myIndex];
	}

	if (myInAsia[myIndex]) {
		myRunningAsiaHigh = myRunningAsiaHigh == null ? high[myIndex] : Math.max(myRunningAsiaHigh, high[myIndex]);
		myRunningAsiaLow = myRunningAsiaLow == null ? low[myIndex] : Math.min(myRunningAsiaLow, low[myIndex]);
	}

	myAsiaHigh[myIndex] = myRunningAsiaHigh;
	myAsiaLow[myIndex] = myRunningAsiaLow;

	if (myLondonStartedNow) {
		myTradeTaken = false;
		mySweepDir = 0;
	}

	const myBullSweep = myInLondon[myIndex] && myRunningAsiaLow != null && low[myIndex] < myRunningAsiaLow;
	const myBearSweep = myInLondon[myIndex] && myRunningAsiaHigh != null && high[myIndex] > myRunningAsiaHigh;

	if (!myTradeTaken && mySweepDir === 0) {
		if (myBullSweep) {
			mySweepDir = 1;
		}
		else if (myBearSweep) {
			mySweepDir = -1;
		}
	}

	mySweepDirArr[myIndex] = mySweepDir;

	const myBuy = !myTradeTaken && myInLondon[myIndex] && mySweepDir === 1 &&
		myBullDisplacement[myIndex] && myBullFVG[myIndex] && myBullBias[myIndex];

	const mySell = !myTradeTaken && myInLondon[myIndex] && mySweepDir === -1 &&
		myBearDisplacement[myIndex] && myBearFVG[myIndex] && myBearBias[myIndex];

	myBuySignal[myIndex] = myBuy;
	mySellSignal[myIndex] = mySell;

	if (myBuy && myIndex > 0) {
		const myEntry = close[myIndex];
		const mySl = low[myIndex - 1];
		const myTp = myEntry + (myEntry - mySl) * myRR;
		myEntryArr[myIndex] = myEntry;
		mySlArr[myIndex] = mySl;
		myTpArr[myIndex] = myTp;
		myTradeTaken = true;
	}

	if (mySell && myIndex > 0) {
		const myEntry = close[myIndex];
		const mySl = high[myIndex - 1];
		const myTp = myEntry - (mySl - myEntry) * myRR;
		myEntryArr[myIndex] = myEntry;
		mySlArr[myIndex] = mySl;
		myTpArr[myIndex] = myTp;
		myTradeTaken = true;
	}

	myTradeTakenArr[myIndex] = myTradeTaken;
}

// ===== SIGNALS FOR SCANNERS / ALERTS / STRATEGY TESTER =====
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');

// ===== VISUALS =====
const myAsiaHighPainted = paint(myAsiaHigh, { name: 'AsiaHigh', color: '#4DA3FF', style: 'ladder', forceUsePriceAxis: true });
const myAsiaLowPainted = paint(myAsiaLow, { name: 'AsiaLow', color: '#FF8A65', style: 'ladder', forceUsePriceAxis: true });

const myBuyMarks = myBuySignal.map(_v => _v ? 1 : null);
const mySellMarks = mySellSignal.map(_v => _v ? 1 : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

paint(myEntryArr, { name: 'EntryLevel', color: '#9575CD', style: 'line', forceUsePriceAxis: true });
paint(mySlArr, { name: 'StopLevel', color: '#EF5350', style: 'line', forceUsePriceAxis: true });
paint(myTpArr, { name: 'TargetLevel', color: '#26A69A', style: 'line', forceUsePriceAxis: true });