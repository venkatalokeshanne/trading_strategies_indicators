// NOTE: TrendSpider's Custom JS API has no broker/strategy simulation layer
// (no strategy.entry / strategy.exit / position tracking). This indicator
// manually re-implements the Pine Script's internal state machine (position,
// stage, trailing levels) bar by bar to reproduce the same stop/profit level
// values and the same signal bars as closely as possible. See the warnings
// below for the approximations that had to be made because of API limits.
describe_indicator('Stepped Trailing Strategy Example', 'price');

const myTab = input.tab('Parameters');

const myStopLossPct = myTab.number('Stop loss %', 5, { min: 0, max: 100 });
const myTp1Pct = myTab.number('Take profit 1 %', 5, { min: 0, max: 100 });
const myTp2Pct = myTab.number('Take profit 2 %', 10, { min: 0, max: 100 });
const myTp3Pct = myTab.number('Take profit 3 %', 15, { min: 0, max: 100 });
const myActivateTrailingOnThirdStep = myTab.boolean('Activate trailing on third stage', false);

// Pine's syminfo.mintick is not exposed in Custom JS. We approximate it
// using the symbol's displayed decimals (10^-decimals), which matches
// mintick for the vast majority of stocks/forex/crypto pairs but is not
// guaranteed to be identical to the exchange's real tick size everywhere.
const myMinTick = Math.pow(10, -current.decimals);

const myMaFast = sma(close, 14);
const myMaSlow = sma(close, 28);

const myN = close.length;

const myStopLevel = series_of(null);
const myProfitLevel = series_of(null);
const myTrailOffsetLevel = series_of(null);
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);

let myPosSize = 0;
let myAvgPrice = 0;
let myStage = 0;

// Two independent persistent trackers, mirroring the two distinct call
// sites of calcTrailingAmountLevel() in the original Pine code (Pine's
// "var" state is scoped per call-site, not per function).
let myTrailAmountState1 = null;
let myTrailAmountState2 = null;

function myCalcStopLossPrice(_offsetPts, _avgPrice) {
	// long only, since the Pine script only ever enters strategy.long
	return _avgPrice - _offsetPts * myMinTick;
}

function myCalcProfitTrgtPrice(_offsetPts, _avgPrice) {
	return myCalcStopLossPrice(-_offsetPts, _avgPrice);
}

function myCalcTrailingAmountLevel(_points, _avgPrice, _high, _prevLevel) {
	let myLevel = myCalcProfitTrgtPrice(_points, _avgPrice);
	if (myLevel !== null) {
		if (_prevLevel !== null) {
			myLevel = Math.max(_prevLevel, myLevel);
		}
		if (myLevel !== null) {
			myLevel = Math.max(_high, myLevel);
		}
	}
	return myLevel;
}

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myHigh = high[myIndex];
	const myLow = low[myIndex];
	const myClose = close[myIndex];

	const myCrossover = myIndex > 0 &&
		myMaFast[myIndex] > myMaSlow[myIndex] &&
		myMaFast[myIndex - 1] <= myMaSlow[myIndex - 1];

	// Entry: approximated as filling at the signal bar's close, since
	// Pine's default strategy.entry() fills on the NEXT bar's open and
	// there is no equivalent broker-fill simulation available here.
	if (myPosSize === 0 && myCrossover) {
		myPosSize = 1;
		myAvgPrice = myClose;
		myStage = 0;
		myTrailAmountState1 = null;
		myTrailAmountState2 = null;
		myEntrySignal[myIndex] = true;
	}

	const mySlPts = myPosSize !== 0 ? (myAvgPrice * myStopLossPct / 100 / myMinTick) : 0;
	const myTp1Pts = myPosSize !== 0 ? (myAvgPrice * myTp1Pct / 100 / myMinTick) : 0;
	const myTp2Pts = myPosSize !== 0 ? (myAvgPrice * myTp2Pct / 100 / myMinTick) : 0;
	const myTp3Pts = myPosSize !== 0 ? (myAvgPrice * myTp3Pct / 100 / myMinTick) : 0;

	const myCurProfitPts = myPosSize > 0 ? ((myHigh - myAvgPrice) / myMinTick) : 0;

	if (myPosSize === 0) {
		myStage = 0;
	}
	if (myStage === 0 && myPosSize !== 0) {
		myStage = 1;
	}
	else if (myStage === 1 && myCurProfitPts >= myTp1Pts) {
		myStage = 2;
	}
	else if (myStage === 2 && myCurProfitPts >= myTp2Pts) {
		myStage = 3;
	}

	const myAmountLevel1 = myCalcTrailingAmountLevel(myTp3Pts, myAvgPrice, myHigh, myTrailAmountState1);
	myTrailAmountState1 = myAmountLevel1;

	const myAmountLevel2 = myCalcTrailingAmountLevel(myTp3Pts, myAvgPrice, myHigh, myTrailAmountState2);
	myTrailAmountState2 = myAmountLevel2;

	let myTrailOffsetTmp = null;
	if (myPosSize > 0 && myAmountLevel2 !== null) {
		const myTrailActiveDiff = myAmountLevel2 - myCalcProfitTrgtPrice(myTp3Pts, myAvgPrice);
		if (myTrailActiveDiff > 0) {
			myTrailOffsetTmp = myTrailActiveDiff + myCalcProfitTrgtPrice(myTp2Pts, myAvgPrice);
		}
	}

	const myProfitLevelValue = myActivateTrailingOnThirdStep ?
		myAmountLevel1 :
		(myPosSize !== 0 ? myCalcProfitTrgtPrice(myTp3Pts, myAvgPrice) : null);

	let myStopLevelValue = null;
	let myTrailOffsetLevelValue = null;

	if (myPosSize !== 0) {
		if (myStage === 1) {
			myStopLevelValue = myCalcStopLossPrice(mySlPts, myAvgPrice);
		}
		else if (myStage === 2) {
			myStopLevelValue = myCalcStopLossPrice(0, myAvgPrice);
		}
		else if (myStage === 3) {
			myStopLevelValue = myCalcStopLossPrice(-myTp1Pts, myAvgPrice);
			if (myActivateTrailingOnThirdStep) {
				myTrailOffsetLevelValue = myTrailOffsetTmp;
			}
		}
	}

	myStopLevel[myIndex] = myStopLevelValue;
	myProfitLevel[myIndex] = myProfitLevelValue;
	myTrailOffsetLevel[myIndex] = myTrailOffsetLevelValue;

	// Exit check against the current bar's range. Order approximated as
	// "stop first, then profit/trailing", since Pine's exact intrabar
	// fill order cannot be reproduced without tick-level data.
	if (myPosSize !== 0) {
		let myExitHit = false;

		if (myStage === 3 && myActivateTrailingOnThirdStep) {
			if (myStopLevelValue !== null && myLow <= myStopLevelValue) {
				myExitHit = true;
			}
			else if (myTrailOffsetLevelValue !== null && myLow <= myTrailOffsetLevelValue) {
				myExitHit = true;
			}
		}
		else {
			if (myStopLevelValue !== null && myLow <= myStopLevelValue) {
				myExitHit = true;
			}
			if (!myExitHit && myProfitLevelValue !== null && myHigh >= myProfitLevelValue) {
				myExitHit = true;
			}
		}

		if (myExitHit) {
			myPosSize = 0;
			myStage = 0;
			myExitSignal[myIndex] = true;
		}
	}
}

paint(myStopLevel, { name: 'Stop Level', color: '#ef5350', style: 'line' });
paint(myProfitLevel, { name: 'Profit Level', color: '#4da3ff', style: 'line' });
paint(myTrailOffsetLevel, { name: 'Trail Offset Level', color: '#26a69a', style: 'line' });

register_signal(myEntrySignal, 'Long Entry');
register_signal(myExitSignal, 'Long Exit');