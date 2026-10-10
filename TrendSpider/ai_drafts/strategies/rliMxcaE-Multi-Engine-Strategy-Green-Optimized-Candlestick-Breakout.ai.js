describe_indicator('Multi Engine Strategy Green Optimized', 'price');

// NOTE: This is a direct, best-effort port of the Pine Script v6 strategy
// logic into TrendSpider Custom JS. A few approximations were required
// (see explanations below and in the flags section).
// Input titles were shortened across the board because the engine
// enforces a maximum length for input() names.

// ---------------- INPUTS ----------------
const toggleTab = input.tab('Strategy Engine Toggles');
const myTradeDips = toggleTab.boolean('Trade Dips', true);
const myTradeBreakouts = toggleTab.boolean('Trade Breakouts', true);

const maTab = input.tab('Moving Averages');
const myEmaFastLen = maTab.number('Fast EMA', 21, { min: 1, max: 500 });
const myEmaSlowLen = maTab.number('Trend EMA', 50, { min: 1, max: 500 });

const padTab = input.tab('Execution Padding');
const myBufferPct = padTab.number('EMA Buffer Pct', 0.15, { min: 0, max: 10 });

const breakoutTab = input.tab('Breakout Engine Configuration');
const myBreakoutLookback = breakoutTab.number('Apex Lookback', 5, { min: 1, max: 200 });
const myVolMultiplier = breakoutTab.number('Vol Spike Mult', 1.2, { min: 0.1, max: 20 });

const timeTab = input.tab('Time Horizon Filter');
const myLookbackDays = timeTab.number('Lookback Days', 30, { min: 1, max: 3650 });

// ---------------- CORE INDICATORS ----------------
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);

// Daily-resetting VWAP (approximates Pine's ta.vwap, which resets every session).
// TrendSpider's built-in vwap() does not auto-reset per session, so we
// compute it manually with a loop, resetting cumulative sums at each new day.
const myVwap = series_of(null);
{
	let myCumPV = 0;
	let myCumVol = 0;
	let myPrevSession = null;
	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const mySession = bar_at(time[myIndex]).session;
		if (mySession !== myPrevSession) {
			myCumPV = 0;
			myCumVol = 0;
			myPrevSession = mySession;
		}
		const myTypicalPrice = hlc3[myIndex];
		myCumPV += myTypicalPrice * volume[myIndex];
		myCumVol += volume[myIndex];
		myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : myTypicalPrice;
	}
}

const myAvgVolume = sma(volume, 5);
const myVolumeSpiked = for_every(volume, myAvgVolume, (_v, _av) => _v > (_av * myVolMultiplier));

// Local resistance ceiling: highest high over lookback, excluding current bar (shift by 1)
const myLocalResistanceCeilingRaw = highest(high, myBreakoutLookback);
const myLocalResistanceCeiling = shift(myLocalResistanceCeilingRaw, 1);

const myLowestLowInDip = lowest(low, 5);

const myMacroBullish = for_every(close, myVwap, myEmaSlow, (_c, _vw, _es) => (_c > _vw) && (_c > _es));

const myEmaUpperThreshold = mult(myEmaFast, 1 + (myBufferPct / 100));
const myPriceInBuyZone = for_every(low, myEmaUpperThreshold, close, myEmaSlow, (_l, _thr, _c, _es) => (_l <= _thr) && (_c > _es));

const myGreenReversalCandle = series_of(false);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myGreenReversalCandle[myIndex] = (close[myIndex] > open[myIndex]) && (close[myIndex] > close[myIndex - 1]);
}

const myDipBuySignalRaw = for_every(myMacroBullish, myPriceInBuyZone, myGreenReversalCandle, (_mb, _pz, _gr) => (_mb && _pz && _gr && myTradeDips));

const myCrossoverCeiling = series_of(false);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myCurOk = close[myIndex] > myLocalResistanceCeiling[myIndex];
	const myPrevOk = close[myIndex - 1] <= myLocalResistanceCeiling[myIndex - 1];
	myCrossoverCeiling[myIndex] = myCurOk && myPrevOk;
}

const myBreakoutBuySignalRaw = for_every(myMacroBullish, myCrossoverCeiling, myVolumeSpiked, (_mb, _co, _vs) => (_mb && _co && _vs && myTradeBreakouts));

// Time range filter: current.now acts as a proxy for Pine's "timenow"
// (both represent the current real-time server timestamp).
const myInDateRangeThreshold = current.now - (myLookbackDays * 86400);
const myInDateRange = for_every(time, _t => _t >= myInDateRangeThreshold);

// ---------------- STATE MACHINE SIMULATION ----------------
// Pine's strategy engine is sequential/stateful (position, stop, target).
// We reproduce it with an explicit bar-by-bar loop, which is the only way
// to express this kind of path-dependent logic in this engine.
const myStopLossSeries = series_of(null);
const myTakeProfitSeries = series_of(null);
const myBuySignal = series_of(false);
const myDipBuySignal = series_of(false);
const myBreakoutBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myCeilingLine = series_of(null);

let myPositionSize = 0;
let myStopLoss = null;
let myTakeProfit = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myDipBuySignal[myIndex] = !!myDipBuySignalRaw[myIndex];
	myBreakoutBuySignal[myIndex] = !!myBreakoutBuySignalRaw[myIndex];

	// Ceiling line only shown while flat, mirroring the Pine plot() condition
	myCeilingLine[myIndex] = (myTradeBreakouts && myPositionSize === 0) ? myLocalResistanceCeiling[myIndex] : null;

	if (myPositionSize === 0) {
		if (myDipBuySignalRaw[myIndex] && myInDateRange[myIndex]) {
			const myCandidateStop = myLowestLowInDip[myIndex];
			const myRiskDistance = close[myIndex] - myCandidateStop;
			if (myRiskDistance > (close[myIndex] * 0.0005)) {
				myStopLoss = myCandidateStop;
				myTakeProfit = close[myIndex] + (myRiskDistance * 2);
				myPositionSize = 1;
				myBuySignal[myIndex] = true;
			}
		}
		else if (myBreakoutBuySignalRaw[myIndex] && myInDateRange[myIndex]) {
			const myCandidateStop = myLowestLowInDip[myIndex];
			const myRiskDistance = close[myIndex] - myCandidateStop;
			if (myRiskDistance > (close[myIndex] * 0.0005)) {
				myStopLoss = myCandidateStop;
				myTakeProfit = close[myIndex] + (myRiskDistance * 2);
				myPositionSize = 1;
				myBuySignal[myIndex] = true;
			}
		}
	}
	else if (myPositionSize > 0) {
		if (close[myIndex] < myEmaSlow[myIndex]) {
			mySellSignal[myIndex] = true;
			myPositionSize = 0;
		}
		else {
			// Approximate intrabar stop/limit fills using the bar's low/high,
			// since this engine does not simulate tick-by-tick order fills.
			if (low[myIndex] <= myStopLoss) {
				mySellSignal[myIndex] = true;
				myPositionSize = 0;
			}
			else if (high[myIndex] >= myTakeProfit) {
				mySellSignal[myIndex] = true;
				myPositionSize = 0;
			}
		}
	}

	if (myPositionSize === 0) {
		myStopLoss = null;
		myTakeProfit = null;
	}

	myStopLossSeries[myIndex] = myPositionSize > 0 ? myStopLoss : null;
	myTakeProfitSeries[myIndex] = myPositionSize > 0 ? myTakeProfit : null;
}

// ---------------- PAINTING ----------------
paint(myEmaFast, { name: 'FastEMASupport', color: '#ff0055', thickness: 2 });
paint(myEmaSlow, { name: 'MicroTrendFilter', color: '#ffcc00', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#0088ff', thickness: 2 });
paint(myCeilingLine, { name: 'BreakoutCeiling', color: '#00ffff', thickness: 1, style: 'ladder' });
paint(myStopLossSeries, { name: 'ActiveStopLoss', color: 'red', thickness: 2, style: 'ladder' });
paint(myTakeProfitSeries, { name: 'ActiveTakeProfit', color: 'green', thickness: 2, style: 'ladder' });

// ---------------- SIGNALS FOR SCANNERS/ALERTS/BACKTEST ----------------
register_signal(myBuySignal, 'Buy Signal');
register_signal(myDipBuySignal, 'Dip Buy Signal');
register_signal(myBreakoutBuySignal, 'Breakout Buy Signal');
register_signal(mySellSignal, 'Sell Signal');