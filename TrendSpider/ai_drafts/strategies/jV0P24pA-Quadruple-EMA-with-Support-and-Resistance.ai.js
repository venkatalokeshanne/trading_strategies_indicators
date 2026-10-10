describe_indicator('EMA and SR Strategy', 'price');

// NOTE: This is a best-effort conversion from Pine Script v6 strategy logic.
// TrendSpider Custom JS runs on closed-bar data only (no bar magnifier /
// intrabar fills), so exits that depend on intrabar stop/limit/trailing
// touches are approximated using each bar's high/low/close. Fill order
// within a single bar (whether stop or target would have hit first) cannot
// be perfectly reproduced; this script checks stop before target as a
// reasonable approximation.

const myTab = input.tab('Strategy Settings');
const myRRMultiplier = myTab.number('Risk Reward Ratio', 3.0, { min: 0.1, max: 20 });
const myShowSR = myTab.boolean('Show Support/Resistance', true);
const mySwingLookback = myTab.number('Swing Detection Bars', 20, { min: 1, max: 200 });
const myOneTradePerDay = myTab.boolean('One Trade Per Day Per Type', true);

const myTrailTab = input.tab('Trailing Stop Loss');
const myUseTrailingSL = myTrailTab.boolean('Use Trailing Stop Loss', false);
const myTrailActivation = myTrailTab.number('Trailing Activation Percent', 1.0, { min: 0.5, max: 50, step: 0.1 });
const myTrailDistance = myTrailTab.number('Trailing Distance Percent', 0.5, { min: 0.1, max: 50, step: 0.1 });

// === EMAs ===
const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);
const myEma100 = ema(close, 100);
const myEma200 = ema(close, 200);

paint(myEma20, { color: '#f6d32d', thickness: 2, name: 'EMA20' });
paint(myEma50, { color: '#3584e4', thickness: 2, name: 'EMA50' });
paint(myEma100, { color: '#ffffff', thickness: 2, name: 'EMA100' });
paint(myEma200, { color: '#2ec27e', thickness: 2, name: 'EMA200' });

// === Swing Highs/Lows for Support/Resistance ===
const mySwingHigh = pivot_high(high, mySwingLookback, mySwingLookback);
const mySwingLow = pivot_low(low, mySwingLookback, mySwingLookback);

const myResistanceRaw = for_every(mySwingHigh, (_h, _prev) => {
	return (_h !== null && _h !== undefined) ? _h : (_prev === undefined ? null : _prev);
});
const mySupportRaw = for_every(mySwingLow, (_l, _prev) => {
	return (_l !== null && _l !== undefined) ? _l : (_prev === undefined ? null : _prev);
});

const myResistance = myShowSR ? myResistanceRaw : series_of(null);
const mySupport = myShowSR ? mySupportRaw : series_of(null);

paint(myResistance, { style: 'dotted', color: '#e5a50a', thickness: 1, name: 'Resistance', forceUsePriceAxis: true });
paint(mySupport, { style: 'dotted', color: '#3584e4', thickness: 1, name: 'Support', forceUsePriceAxis: true });

// === Main simulation loop ===
const myN = close.length;
const myCeEntrySeries = series_of(null);
const myPeEntrySeries = series_of(null);
const myCeExitSeries = series_of(null);
const myPeExitSeries = series_of(null);

const myCeEntrySignal = series_of(false);
const myPeEntrySignal = series_of(false);
const myCeExitSignal = series_of(false);
const myPeExitSignal = series_of(false);

let myLastTradedDay = null;
let myCeTradedToday = false;
let myPeTradedToday = false;
let myCeIsOpen = false;
let myPeIsOpen = false;
let myCeSl = null;
let myCeTarget = null;
let myPeSl = null;
let myPeTarget = null;
let myCeEntryPrice = null;
let myPeEntryPrice = null;
let myCePeakHigh = null;
let myPeTroughLow = null;
let myCeTrailArmed = false;
let myPeTrailArmed = false;

for (let myIndex = 1; myIndex < myN; myIndex += 1) {
	const myDay = time_of(time[myIndex]).dayOfMonth;
	const myIsNewDay = myLastTradedDay === null || myDay !== myLastTradedDay;

	if (myIsNewDay) {
		myLastTradedDay = myDay;
		myCeTradedToday = false;
		myPeTradedToday = false;
	}

	const myPrevHigh = high[myIndex - 1];
	const myPrevLow = low[myIndex - 1];
	const myPrevValid = myPrevHigh != null && myPrevLow != null;

	const myEmasValid = myEma20[myIndex] != null && myEma50[myIndex] != null && myEma100[myIndex] != null && myEma200[myIndex] != null;
	const myCeEmaFilter = myEmasValid && close[myIndex] > myEma20[myIndex] && close[myIndex] > myEma50[myIndex] && close[myIndex] > myEma100[myIndex] && close[myIndex] > myEma200[myIndex];
	const myCeBreakout = myPrevValid && close[myIndex] > myPrevHigh;

	const myPeEmaFilter = myEmasValid && close[myIndex] < myEma20[myIndex] && close[myIndex] < myEma50[myIndex] && close[myIndex] < myEma100[myIndex] && close[myIndex] < myEma200[myIndex];
	const myPeBreakdown = myPrevValid && close[myIndex] < myPrevLow;

	// === CE Exit check (evaluated before new entries, mirroring Pine's per-bar exit check) ===
	if (myCeIsOpen && myCeSl != null && myCeTarget != null) {
		let myEffectiveSl = (close[myIndex] < myEma20[myIndex] || close[myIndex] < myEma50[myIndex]) ? Math.min(myCeSl, low[myIndex]) : myCeSl;

		if (myCePeakHigh === null || high[myIndex] > myCePeakHigh) {
			myCePeakHigh = high[myIndex];
		}

		let myStopHit = false;

		if (myUseTrailingSL) {
			const myActPrice = myCeEntryPrice * (1 + myTrailActivation / 100);
			if (!myCeTrailArmed && myCePeakHigh >= myActPrice) {
				myCeTrailArmed = true;
			}
			if (myCeTrailArmed) {
				const myTrailStop = myCePeakHigh * (1 - myTrailDistance / 100);
				myEffectiveSl = Math.max(myEffectiveSl, myTrailStop);
			}
		}

		if (low[myIndex] <= myEffectiveSl) {
			myStopHit = true;
		}
		else if (high[myIndex] >= myCeTarget) {
			myCeExitSeries[myIndex] = close[myIndex];
			myCeExitSignal[myIndex] = true;
			myCeIsOpen = false;
		}

		if (myStopHit) {
			myCeExitSeries[myIndex] = close[myIndex];
			myCeExitSignal[myIndex] = true;
			myCeIsOpen = false;
		}
	}

	// === PE Exit check ===
	if (myPeIsOpen && myPeSl != null && myPeTarget != null) {
		let myEffectiveSl = (close[myIndex] > myEma20[myIndex] || close[myIndex] > myEma50[myIndex]) ? Math.max(myPeSl, high[myIndex]) : myPeSl;

		if (myPeTroughLow === null || low[myIndex] < myPeTroughLow) {
			myPeTroughLow = low[myIndex];
		}

		let myStopHit = false;

		if (myUseTrailingSL) {
			const myActPrice = myPeEntryPrice * (1 - myTrailActivation / 100);
			if (!myPeTrailArmed && myPeTroughLow <= myActPrice) {
				myPeTrailArmed = true;
			}
			if (myPeTrailArmed) {
				const myTrailStop = myPeTroughLow * (1 + myTrailDistance / 100);
				myEffectiveSl = Math.min(myEffectiveSl, myTrailStop);
			}
		}

		if (high[myIndex] >= myEffectiveSl) {
			myStopHit = true;
		}
		else if (low[myIndex] <= myPeTarget) {
			myPeExitSeries[myIndex] = close[myIndex];
			myPeExitSignal[myIndex] = true;
			myPeIsOpen = false;
		}

		if (myStopHit) {
			myPeExitSeries[myIndex] = close[myIndex];
			myPeExitSignal[myIndex] = true;
			myPeIsOpen = false;
		}
	}

	if (!myCeIsOpen) {
		myCeSl = null;
		myCeTarget = null;
	}
	if (!myPeIsOpen) {
		myPeSl = null;
		myPeTarget = null;
	}

	// === CE Entry ===
	const myCeCanTrade = !myOneTradePerDay || !myCeTradedToday;
	const myCeEntry = myCeEmaFilter && myCeBreakout && myCeCanTrade && !myCeIsOpen && !myPeIsOpen;

	if (myCeEntry) {
		const myRisk = close[myIndex] - myPrevLow;
		if (myRisk > 0) {
			myCeSl = myPrevLow;
			myCeTarget = close[myIndex] + myRRMultiplier * myRisk;
			myCeIsOpen = true;
			myCeEntryPrice = close[myIndex];
			myCePeakHigh = high[myIndex];
			myCeTrailArmed = false;
			myCeTradedToday = true;
			myCeEntrySeries[myIndex] = low[myIndex];
			myCeEntrySignal[myIndex] = true;
		}
	}

	// === PE Entry ===
	const myPeCanTrade = !myOneTradePerDay || !myPeTradedToday;
	const myPeEntry = myPeEmaFilter && myPeBreakdown && myPeCanTrade && !myPeIsOpen && !myCeIsOpen;

	if (myPeEntry) {
		const myRisk = myPrevHigh - close[myIndex];
		if (myRisk > 0) {
			myPeSl = myPrevHigh;
			myPeTarget = close[myIndex] - myRRMultiplier * myRisk;
			myPeIsOpen = true;
			myPeEntryPrice = close[myIndex];
			myPeTroughLow = low[myIndex];
			myPeTrailArmed = false;
			myPeTradedToday = true;
			myPeEntrySeries[myIndex] = high[myIndex];
			myPeEntrySignal[myIndex] = true;
		}
	}
}

paint(myCeEntrySeries, { style: 'labels_below', color: '#2ec27e', name: 'CE Entry' });
paint(myPeEntrySeries, { style: 'labels_above', color: '#e01b24', name: 'PE Entry' });
paint(myCeExitSeries, { style: 'labels_above', color: '#9141ac', name: 'CE Exit' });
paint(myPeExitSeries, { style: 'labels_below', color: '#1a5fb4', name: 'PE Exit' });

// Signal names must differ from the paint() line names above to avoid
// the "signal already exists" naming collision inside the engine.
register_signal(myCeEntrySignal, 'Buy CE Entry Signal');
register_signal(myPeEntrySignal, 'Buy PE Entry Signal');
register_signal(myCeExitSignal, 'CE Exit Signal');
register_signal(myPeExitSignal, 'PE Exit Signal');