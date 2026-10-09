describe_indicator('BTC Multi-TF Ringing Strategy (Signals)', 'price');

// ===================== INPUTS =====================
const myGeneralTab = input.tab('General');
const mySmoothLen = myGeneralTab.number('EMA Smooth Length', 5, { min: 1, max: 200 });
const myImpulseATR = myGeneralTab.number('Impulse ATR Threshold', 0.9, { min: 0, max: 10, step: 0.01 });
const myDecayFactor = myGeneralTab.number('Oscillation Decay Factor', 0.45, { min: 0, max: 1, step: 0.01 });
const myPullbackFactor = myGeneralTab.number('Pullback Fraction LTF', 0.15, { min: 0, max: 1, step: 0.01 });

const myTradeTab = input.tab('Trade Params');
const myTpFactor = myTradeTab.number('Take Profit %', 0.8, { min: 0, max: 10, step: 0.01 });
const myPartialProfitPct = myTradeTab.number('Partial Profit %', 30, { min: 0, max: 100 });
const myPartialProfitGain = myTradeTab.number('Partial Profit Gain %', 5, { min: 0, max: 100 });
const mySlATRMult = myTradeTab.number('Stop ATR Multiplier', 1.1, { min: 0, max: 10, step: 0.01 });
const myMaxSwings = myTradeTab.number('Max Swings', 2, { min: 1, max: 10 });
const myMaxEntriesPerImpulse = myTradeTab.number('Max Entries Per Impulse', 4, { min: 1, max: 50 });

const myTFTab = input.tab('Timeframes');
const myPrimaryTF = myTFTab.select('Primary Impulse TF', '60', constants.time_frames);
const myEntryTF = myTFTab.select('Entry TF', '3', constants.time_frames);
const myTrendTF = myTFTab.select('Trend TF', '240', constants.time_frames);
const myHtfEmaLen = myTFTab.number('Trend EMA Length', 50, { min: 1, max: 500 });

// ===================== FETCH MULTI-TF DATA =====================
const [myDataPrimary, myDataEntry, myDataTrend] = await Promise.all([
	request.history(current.ticker, myPrimaryTF),
	request.history(current.ticker, myEntryTF),
	request.history(current.ticker, myTrendTF)
]);

assert(!myDataPrimary.error, `Error fetching Primary TF data: ${myDataPrimary.error}`);
assert(!myDataEntry.error, `Error fetching Entry TF data: ${myDataEntry.error}`);
assert(!myDataTrend.error, `Error fetching Trend TF data: ${myDataTrend.error}`);

// Primary TF math
const myEmaPrimaryRaw = ema(myDataPrimary.close, mySmoothLen);
const myAtrPrimaryRaw = atr(myDataPrimary.high, myDataPrimary.low, myDataPrimary.close, 14);
const myAtrPrimaryAvgRaw = sma(myAtrPrimaryRaw, 20);

// Entry TF math
const myAtrEntryRaw = atr(myDataEntry.high, myDataEntry.low, myDataEntry.close, 14);

// Trend TF math
const myEmaTrendRaw = ema(myDataTrend.close, myHtfEmaLen);

// Land everything onto the chart's own time series ("le" avoids future lookahead:
// a source point only lands on a target candle whose time is >= source time? we
// use "le" so the mapping always points to data available at/at-before chart time).
function myLandConstant(_srcTime, _srcValues) {
	const myLanded = land_points_onto_series(_srcTime, _srcValues, time, 'le');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myHighPrimary = myLandConstant(myDataPrimary.time, myDataPrimary.high);
const myLowPrimary = myLandConstant(myDataPrimary.time, myDataPrimary.low);
const myEmaPrimary = myLandConstant(myDataPrimary.time, myEmaPrimaryRaw);
const myAtrPrimary = myLandConstant(myDataPrimary.time, myAtrPrimaryRaw);
const myAtrPrimaryAvg = myLandConstant(myDataPrimary.time, myAtrPrimaryAvgRaw);

const myCloseEntry = myLandConstant(myDataEntry.time, myDataEntry.close);
const myAtrEntry = myLandConstant(myDataEntry.time, myAtrEntryRaw);

const myEmaTrend = myLandConstant(myDataTrend.time, myEmaTrendRaw);

// ===================== MAIN LOGIC LOOP =====================
const myBarCount = close.length;

const myLongCond = series_of(false);
const myShortCond = series_of(false);
const myImpulseStrength = series_of(null);
const myCandleColors = series_of(null);

let myEntriesPerImpulse = 0;

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myEmaPrimaryCurr = myEmaPrimary[myIndex];
	const myEmaPrimaryPrev = myIndex > 0 ? myEmaPrimary[myIndex - 1] : null;
	const myAtrPrimaryCurr = myAtrPrimary[myIndex];
	const myAtrPrimaryAvgCurr = myAtrPrimaryAvg[myIndex];
	const myHighPrimaryCurr = myHighPrimary[myIndex];
	const myLowPrimaryCurr = myLowPrimary[myIndex];
	const myCloseEntryCurr = myCloseEntry[myIndex];
	const myAtrEntryCurr = myAtrEntry[myIndex];
	const myEmaTrendCurr = myEmaTrend[myIndex];
	const myCloseCurr = close[myIndex];

	if (myEmaPrimaryCurr == null || myEmaPrimaryPrev == null || myAtrPrimaryCurr == null ||
		myAtrPrimaryAvgCurr == null || myHighPrimaryCurr == null || myLowPrimaryCurr == null ||
		myCloseEntryCurr == null || myAtrEntryCurr == null || myEmaTrendCurr == null ||
		!myAtrPrimaryCurr) {
		continue;
	}

	// Replicates: "if strongImpulse and barstate.isfirst -> entriesPerImpulse := 0"
	// Note: in Pine this only ever fires on the very first bar of the whole
	// data set, so entriesPerImpulse effectively never resets afterwards.
	const myD1 = myEmaPrimaryCurr - myEmaPrimaryPrev;
	const myImpulseRaw = Math.abs(myD1) / myAtrPrimaryCurr > myImpulseATR;
	const myStrongImpulse = myImpulseRaw && (myAtrPrimaryCurr > 0.8 * myAtrPrimaryAvgCurr);

	if (myStrongImpulse && myIndex === 0) {
		myEntriesPerImpulse = 0;
	}

	const myImpulseHigh = myStrongImpulse ? myHighPrimaryCurr : null;
	const myImpulseLow = myStrongImpulse ? myLowPrimaryCurr : null;
	const myOscAmp = (myImpulseHigh != null && myImpulseLow != null)
		? (myImpulseHigh - myImpulseLow) * myDecayFactor
		: null;

	const myUptrend = myCloseCurr > myEmaTrendCurr * 0.995;
	const myDowntrend = myCloseCurr < myEmaTrendCurr * 1.005;

	let myPullbackLong = false;
	let myPullbackShort = false;

	if (myOscAmp != null) {
		myPullbackLong = myCloseEntryCurr < Math.min(myImpulseLow + myOscAmp * myPullbackFactor, myEmaPrimaryCurr);
		myPullbackShort = myCloseEntryCurr > Math.max(myImpulseHigh - myOscAmp * myPullbackFactor, myEmaPrimaryCurr);
	}

	const myLongSignal = myStrongImpulse && myPullbackLong && myUptrend && myEntriesPerImpulse < myMaxEntriesPerImpulse;
	const myShortSignal = myStrongImpulse && myPullbackShort && myDowntrend && myEntriesPerImpulse < myMaxEntriesPerImpulse;

	if (myLongSignal || myShortSignal) {
		myEntriesPerImpulse += 1;
	}

	myLongCond[myIndex] = myLongSignal;
	myShortCond[myIndex] = myShortSignal;

	const myStrength = Math.min(Math.abs(myD1) / myAtrPrimaryCurr, 2);
	myImpulseStrength[myIndex] = myStrength;

	const myOpacity = Math.max(0, Math.min(1, (80 - 40 * myStrength) / 100));

	if (myLongSignal) {
		myCandleColors[myIndex] = `rgba(0,180,90,${1 - myOpacity})`;
	}
	else if (myShortSignal) {
		myCandleColors[myIndex] = `rgba(220,60,60,${1 - myOpacity})`;
	}
}

color_candles(myCandleColors);

register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');