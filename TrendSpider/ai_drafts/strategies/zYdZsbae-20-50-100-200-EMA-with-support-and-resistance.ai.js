describe_indicator('EMA and SR Strategy', 'price');

// NOTE: This is a best-effort port of the Pine Script strategy logic.
// TrendSpider custom indicators cannot simulate a true bar-by-bar broker
// (fills, pyramiding limits, bar magnifier, tick-level trailing stops), so
// position/entry/exit state is simulated manually in a loop using OHLC
// of each candle. Trailing stop logic is approximated using candle
// high/low rather than tick data.

const myTab = input.tab('Strategy');
const myRiskReward = myTab.number('Risk Reward Ratio', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myShowSR = myTab.boolean('Show Support/Resistance', true);
const mySwingLookback = myTab.number('Swing Detection Bars', 20, { min: 2, max: 100 });
const myOneTradePerDay = myTab.boolean('One Trade Per Day Per Type (CE/PE)', true);

const trailingTab = input.tab('Trailing Stop Loss');
const myUseTrailingSl = trailingTab.boolean('Use Trailing Stop Loss', false);
const myTrailActivation = trailingTab.number('Trailing Activation Percent', 1.0, { min: 0.5, max: 50, step: 0.1 });
const myTrailDistance = trailingTab.number('Trailing Distance Percent', 0.5, { min: 0.1, max: 50, step: 0.1 });

const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);
const myEma100 = ema(close, 100);
const myEma200 = ema(close, 200);

const myResistancePivot = pivot_high(high, mySwingLookback, mySwingLookback);
const mySupportPivot = pivot_low(low, mySwingLookback, mySwingLookback);

const myCeEntrySeries = series_of(null);
const myPeEntrySeries = series_of(null);
const myCeExitSeries = series_of(null);
const myPeExitSeries = series_of(null);
const myResistanceSeries = series_of(null);
const mySupportSeries = series_of(null);

let myCeOpen = false;
let myPeOpen = false;
let myCeSl = null;
let myCeTarget = null;
let myPeSl = null;
let myPeTarget = null;
let myCeEntryPrice = null;
let myPeEntryPrice = null;
let myCeTradedToday = false;
let myPeTradedToday = false;
let myLastDay = null;
let myCeTrailArmed = false;
let myPeTrailArmed = false;
let myCePeak = null;
let myPePeak = null;
let myResistanceLevel = null;
let mySupportLevel = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// === Daily trade tracking ===
	const myDayOfMonth = time_of(time[myIndex]).dayOfMonth;
	const myIsNewDay = myLastDay === null || myDayOfMonth !== myLastDay;
	if (myIsNewDay) {
		myLastDay = myDayOfMonth;
		myCeTradedToday = false;
		myPeTradedToday = false;
	}

	const myPrevValid = myIndex >= 1;
	const myPrevHigh = myPrevValid ? high[myIndex - 1] : null;
	const myPrevLow = myPrevValid ? low[myIndex - 1] : null;

	const myEmasValid = myEma20[myIndex] != null && myEma50[myIndex] != null && myEma100[myIndex] != null && myEma200[myIndex] != null;

	const myCeEmaFilter = myEmasValid && close[myIndex] > myEma20[myIndex] && close[myIndex] > myEma50[myIndex] && close[myIndex] > myEma100[myIndex] && close[myIndex] > myEma200[myIndex];
	const myCeBreakout = myPrevValid && close[myIndex] > myPrevHigh;

	const myPeEmaFilter = myEmasValid && close[myIndex] < myEma20[myIndex] && close[myIndex] < myEma50[myIndex] && close[myIndex] < myEma100[myIndex] && close[myIndex] < myEma200[myIndex];
	const myPeBreakdown = myPrevValid && close[myIndex] < myPrevLow;

	const myCeOpenAtStart = myCeOpen;
	const myPeOpenAtStart = myPeOpen;

	// === CE entry ===
	const myCeCanTrade = !myOneTradePerDay || !myCeTradedToday;
	const myCeEntry = myCeEmaFilter && myCeBreakout && myCeCanTrade && !myCeOpenAtStart && !myPeOpenAtStart;

	if (myCeEntry) {
		const myRisk = close[myIndex] - myPrevLow;
		if (myRisk > 0) {
			myCeSl = myPrevLow;
			myCeTarget = close[myIndex] + myRiskReward * myRisk;
			myCeOpen = true;
			myCeEntryPrice = close[myIndex];
			myCeTradedToday = true;
			myCeTrailArmed = false;
			myCePeak = close[myIndex];
			myCeEntrySeries[myIndex] = true;
		}
	}

	// === CE exit ===
	if (myCeOpenAtStart && myCeSl != null && myCeTarget != null) {
		let myEffectiveSl = (close[myIndex] < myEma20[myIndex] || close[myIndex] < myEma50[myIndex]) ? Math.min(myCeSl, low[myIndex]) : myCeSl;

		if (myUseTrailingSl && myCeEntryPrice != null) {
			const myActPrice = myCeEntryPrice * (1 + myTrailActivation / 100);
			if (!myCeTrailArmed && high[myIndex] >= myActPrice) {
				myCeTrailArmed = true;
				myCePeak = high[myIndex];
			}
			else if (myCeTrailArmed) {
				myCePeak = Math.max(myCePeak, high[myIndex]);
			}
			if (myCeTrailArmed) {
				const myTrailStop = myCePeak * (1 - myTrailDistance / 100);
				myEffectiveSl = Math.max(myEffectiveSl, myTrailStop);
			}
		}

		const myExitHit = low[myIndex] <= myEffectiveSl || high[myIndex] >= myCeTarget;
		if (myExitHit) {
			myCeOpen = false;
			myCeSl = null;
			myCeTarget = null;
			myCeEntryPrice = null;
			myCeExitSeries[myIndex] = true;
		}
	}

	// === PE entry ===
	const myPeCanTrade = !myOneTradePerDay || !myPeTradedToday;
	const myPeEntry = myPeEmaFilter && myPeBreakdown && myPeCanTrade && !myPeOpenAtStart && !myCeOpenAtStart;

	if (myPeEntry) {
		const myRisk = myPrevHigh - close[myIndex];
		if (myRisk > 0) {
			myPeSl = myPrevHigh;
			myPeTarget = close[myIndex] - myRiskReward * myRisk;
			myPeOpen = true;
			myPeEntryPrice = close[myIndex];
			myPeTradedToday = true;
			myPeTrailArmed = false;
			myPePeak = close[myIndex];
			myPeEntrySeries[myIndex] = true;
		}
	}

	// === PE exit ===
	if (myPeOpenAtStart && myPeSl != null && myPeTarget != null) {
		let myEffectiveSl = (close[myIndex] > myEma20[myIndex] || close[myIndex] > myEma50[myIndex]) ? Math.max(myPeSl, high[myIndex]) : myPeSl;

		if (myUseTrailingSl && myPeEntryPrice != null) {
			const myActPrice = myPeEntryPrice * (1 - myTrailActivation / 100);
			if (!myPeTrailArmed && low[myIndex] <= myActPrice) {
				myPeTrailArmed = true;
				myPePeak = low[myIndex];
			}
			else if (myPeTrailArmed) {
				myPePeak = Math.min(myPePeak, low[myIndex]);
			}
			if (myPeTrailArmed) {
				const myTrailStop = myPePeak * (1 + myTrailDistance / 100);
				myEffectiveSl = Math.min(myEffectiveSl, myTrailStop);
			}
		}

		const myExitHit = high[myIndex] >= myEffectiveSl || low[myIndex] <= myPeTarget;
		if (myExitHit) {
			myPeOpen = false;
			myPeSl = null;
			myPeTarget = null;
			myPeEntryPrice = null;
			myPeExitSeries[myIndex] = true;
		}
	}

	// === Support & Resistance (sticky last pivot value) ===
	if (myResistancePivot[myIndex] != null) {
		myResistanceLevel = myResistancePivot[myIndex];
	}
	if (mySupportPivot[myIndex] != null) {
		mySupportLevel = mySupportPivot[myIndex];
	}
	myResistanceSeries[myIndex] = myShowSR ? myResistanceLevel : null;
	mySupportSeries[myIndex] = myShowSR ? mySupportLevel : null;
}

paint(myEma20, { name: 'EMA20', color: '#f2c744', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#2a7de1', thickness: 2 });
paint(myEma100, { name: 'EMA100', color: '#dddddd', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#2fae4e', thickness: 2 });

paint(myResistanceSeries, { name: 'Resistance', color: '#ff9933', style: 'dotted', thickness: 1 });
paint(mySupportSeries, { name: 'Support', color: '#2a7de1', style: 'dotted', thickness: 1 });

const myCeEntryIcons = myCeEntrySeries.map(myVal => myVal ? constants.icons.arrow_up : null);
const myPeEntryIcons = myPeEntrySeries.map(myVal => myVal ? constants.icons.arrow_down : null);

paint(myCeEntryIcons, { name: 'CEEntry', style: 'labels_below', color: '#26a69a' });
paint(myPeEntryIcons, { name: 'PEEntry', style: 'labels_above', color: '#ef5350' });

register_signal(myCeEntrySeries.map(myVal => !!myVal), 'CE Entry');
register_signal(myPeEntrySeries.map(myVal => !!myVal), 'PE Entry');
register_signal(myCeExitSeries.map(myVal => !!myVal), 'CE Exit');
register_signal(myPeExitSeries.map(myVal => !!myVal), 'PE Exit');