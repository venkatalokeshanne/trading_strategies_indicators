describe_indicator('Return Dispersion Matrix Strategy', 'lower');

// ── Inputs ──────────────────────────────────────────────────────────
const myDataPoints = input.number('Data Points', 50, { min: 5, max: 450 });
const mySmaLength = input.number('Trend SMA Length', 20, { min: 1, max: 500 });
const myRsiLength = input.number('Mean Revert RSI Length', 14, { min: 1, max: 500 });
const myRsiCrossLevel = input.number('RSI Crossunder Level', 35, { min: 1, max: 99 });
const myTakeProfitPct = input.number('Take Profit %', 5, { min: 0.1, max: 100 });
const myStopLossPct = input.number('Stop Loss %', 15, { min: 0.1, max: 100 });

// ── Base series (no indicator calls inside loops) ───────────────────
const myCurrentReturns = roc(close, 1);
const myPreviousReturns = shift(myCurrentReturns, 1);
const mySmaValue = sma(close, mySmaLength);
const myRsiValue = rsi(close, myRsiLength);

const myBarCount = close.length;

// ── Output series ────────────────────────────────────────────────────
const myDominantQuadrant = series_of(null);
const myQ1Pct = series_of(null);
const myQ2Pct = series_of(null);
const myQ3Pct = series_of(null);
const myQ4Pct = series_of(null);
const myNoTradingFlag = series_of(false);

const myTrendEntrySignal = series_of(false);
const myMeanRevertEntrySignal = series_of(false);
const myTakeProfitTrendSignal = series_of(false);
const myStopLossTrendSignal = series_of(false);
const myTakeProfitMeanRevertSignal = series_of(false);
const myStopLossMeanRevertSignal = series_of(false);

const myCandleColors = series_of(null);

// ── Rolling window state (mirrors Pine's returns_x / returns_y arrays) ─
const myWindowX = [];
const myWindowY = [];

// ── Trade state (only one open trade at a time, as per opentrades==0 guard) ─
let myOpenTradeType = null; // 'trend' or 'meanrevert'
let myInitPrice = 0;
let myTakeProfitLevelTrend = 0;
let myStopLossLevelTrend = 0;
let myTakeProfitLevelMeanRevert = 0;
let myStopLossLevelMeanRevert = 0;

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	// -- Pine pushes current/previous returns every bar unconditionally --
	if (myIndex >= 2) {
		myWindowX.push(myPreviousReturns[myIndex]);
		myWindowY.push(myCurrentReturns[myIndex]);

		if (myWindowX.length > myDataPoints) {
			myWindowX.shift();
			myWindowY.shift();
		}
	}

	let myDominantQuadrantValue = 0;
	let myQ1 = 0, myQ2 = 0, myQ3 = 0, myQ4 = 0;

	if (myWindowX.length > 0) {
		let myCountQ1 = 0, myCountQ2 = 0, myCountQ3 = 0, myCountQ4 = 0;
		const myTotalPoints = myWindowY.length;

		for (let myWinIndex = 0; myWinIndex < myTotalPoints; myWinIndex += 1) {
			const myX = myWindowX[myWinIndex];
			const myY = myWindowY[myWinIndex];

			if (myX >= 0 && myY >= 0) {
				myCountQ1 += 1;
			}
			else if (myX < 0 && myY >= 0) {
				myCountQ2 += 1;
			}
			else if (myX < 0 && myY < 0) {
				myCountQ3 += 1;
			}
			else if (myX >= 0 && myY < 0) {
				myCountQ4 += 1;
			}
		}

		myQ1 = (myCountQ1 / myTotalPoints) * 100.0;
		myQ2 = (myCountQ2 / myTotalPoints) * 100.0;
		myQ3 = (myCountQ3 / myTotalPoints) * 100.0;
		myQ4 = (myCountQ4 / myTotalPoints) * 100.0;

		myDominantQuadrantValue = 1;
		let myMaxVal = myCountQ1;

		if (myCountQ2 > myMaxVal) { myMaxVal = myCountQ2; myDominantQuadrantValue = 2; }
		if (myCountQ3 > myMaxVal) { myMaxVal = myCountQ3; myDominantQuadrantValue = 3; }
		if (myCountQ4 > myMaxVal) { myMaxVal = myCountQ4; myDominantQuadrantValue = 4; }
	}

	myDominantQuadrant[myIndex] = myDominantQuadrantValue;
	myQ1Pct[myIndex] = myQ1;
	myQ2Pct[myIndex] = myQ2;
	myQ3Pct[myIndex] = myQ3;
	myQ4Pct[myIndex] = myQ4;

	const myTrendFollowingStrat = myDominantQuadrantValue === 1;
	const myMeanRevStrat = myDominantQuadrantValue === 2;
	const myNoTrading = myDominantQuadrantValue === 3 || myDominantQuadrantValue === 4;
	myNoTradingFlag[myIndex] = myNoTrading;
	myCandleColors[myIndex] = myNoTrading ? 'rgba(255,255,255,0.5)' : null;

	const myCloseNow = close[myIndex];
	const myClosePrev = myIndex >= 1 ? close[myIndex - 1] : null;

	const myTrendEntryCondition = myIndex >= 1 && myCloseNow > myClosePrev && myCloseNow > mySmaValue[myIndex];
	const myRsiNow = myRsiValue[myIndex];
	const myRsiPrev = myIndex >= 1 ? myRsiValue[myIndex - 1] : null;
	const myMeanRevertEntryCondition = myIndex >= 1 && myRsiPrev !== null && myRsiPrev >= myRsiCrossLevel && myRsiNow < myRsiCrossLevel;

	// -- Trend following entry --
	let myTrendEntryFired = false;
	if (myTrendFollowingStrat && myTrendEntryCondition && myOpenTradeType === null) {
		myInitPrice = myCloseNow;
		myOpenTradeType = 'trend';
		myTakeProfitLevelTrend = myInitPrice + (myInitPrice * myTakeProfitPct) / 100;
		myStopLossLevelTrend = myInitPrice - (myInitPrice * myStopLossPct) / 100;
		myTrendEntryFired = true;
	}
	myTrendEntrySignal[myIndex] = myTrendEntryFired;

	// -- Trend following exits (crossover / crossunder on close) --
	let myTakeProfitTrendFired = false;
	let myStopLossTrendFired = false;
	if (myIndex >= 1 && myOpenTradeType === 'trend') {
		const myTpCrossOver = myClosePrev <= myTakeProfitLevelTrend && myCloseNow > myTakeProfitLevelTrend;
		const mySlCrossUnder = myClosePrev >= myStopLossLevelTrend && myCloseNow < myStopLossLevelTrend;

		if (myTpCrossOver) {
			myTakeProfitTrendFired = true;
			myOpenTradeType = null;
		}
		else if (mySlCrossUnder) {
			myStopLossTrendFired = true;
			myOpenTradeType = null;
		}
	}
	myTakeProfitTrendSignal[myIndex] = myTakeProfitTrendFired;
	myStopLossTrendSignal[myIndex] = myStopLossTrendFired;

	// -- Mean revert entry --
	let myMeanRevertEntryFired = false;
	if (myMeanRevertEntryCondition && myMeanRevStrat && myOpenTradeType === null) {
		myInitPrice = myCloseNow;
		myOpenTradeType = 'meanrevert';
		myTakeProfitLevelMeanRevert = myInitPrice + (myInitPrice * myTakeProfitPct) / 100;
		myStopLossLevelMeanRevert = myInitPrice - (myInitPrice * myStopLossPct) / 100;
		myMeanRevertEntryFired = true;
	}
	myMeanRevertEntrySignal[myIndex] = myMeanRevertEntryFired;

	// -- Mean revert exits --
	let myTakeProfitMeanRevertFired = false;
	let myStopLossMeanRevertFired = false;
	if (myIndex >= 1 && myOpenTradeType === 'meanrevert') {
		const myTpCrossOverMr = myClosePrev <= myTakeProfitLevelMeanRevert && myCloseNow > myTakeProfitLevelMeanRevert;
		const mySlCrossUnderMr = myClosePrev >= myStopLossLevelMeanRevert && myCloseNow < myStopLossLevelMeanRevert;

		if (myTpCrossOverMr) {
			myTakeProfitMeanRevertFired = true;
			myOpenTradeType = null;
		}
		else if (mySlCrossUnderMr) {
			myStopLossMeanRevertFired = true;
			myOpenTradeType = null;
		}
	}
	myTakeProfitMeanRevertSignal[myIndex] = myTakeProfitMeanRevertFired;
	myStopLossMeanRevertSignal[myIndex] = myStopLossMeanRevertFired;
}

// ── Painting ──────────────────────────────────────────────────────────
paint(myDominantQuadrant, { name: 'DominantQuadrant', color: '#4DA3FF', style: 'line' });
paint(myQ1Pct, { name: 'Q1Pct', color: '#26A69A', style: 'line' });
paint(myQ2Pct, { name: 'Q2Pct', color: '#EF5350', style: 'line' });
paint(myQ3Pct, { name: 'Q3Pct', color: '#AB47BC', style: 'line' });
paint(myQ4Pct, { name: 'Q4Pct', color: '#FFA726', style: 'line' });

color_candles(myCandleColors);

// ── Signals for scanner, alerts, strategy tester ───────────────────────
register_signal(myTrendEntrySignal, 'Trend Following Entry');
register_signal(myMeanRevertEntrySignal, 'Mean Revert Entry');
register_signal(myTakeProfitTrendSignal, 'Take Profit Trend Following');
register_signal(myStopLossTrendSignal, 'Stop Loss Trend Following');
register_signal(myTakeProfitMeanRevertSignal, 'Take Profit Mean Revert');
register_signal(myStopLossMeanRevertSignal, 'Stop Loss Mean Revert');
register_signal(myNoTradingFlag, 'No Trading Zone');