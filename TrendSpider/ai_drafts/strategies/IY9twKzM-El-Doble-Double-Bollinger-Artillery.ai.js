describe_indicator('El Doble Double Bollinger', 'price');

// === Bollinger Bands ===
const myTab = input.tab('Bollinger Bands');
const myBbLen = myTab.number('BB Length', 20, { min: 5, max: 200 });
const myBbMult = myTab.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myFastBbLen = myTab.number('Fast BB Length', 4, { min: 2, max: 100 });
const myFastBbMult = myTab.number('Fast BB Mult', 2.0, { min: 0.1, max: 10, step: 0.1 });

const myTrendTab = input.tab('Trend Filter');
const myEmaLen = myTrendTab.number('EMA Length', 55, { min: 10, max: 500 });
const myAdxLen = myTrendTab.number('ADX Length', 14, { min: 5, max: 100 });
const myAdxThresh = myTrendTab.number('ADX Min', 18.0, { min: 0, max: 100, step: 1.0 });

const myExitsTab = input.tab('Exits');
const mySlPts = myExitsTab.number('Stop Loss Points', 15.0, { min: 0, max: 1000, step: 1.0 });
const myTpPts = myExitsTab.number('Take Profit Points', 25.0, { min: 0, max: 1000, step: 1.0 });
const myTimeStop = myExitsTab.number('Time Stop Bars', 20, { min: 5, max: 500 });

const myMgmtTab = input.tab('Trade Mgmt');
const myMaxTrades = myMgmtTab.number('Max Trades Per Day', 3, { min: 1, max: 50 });
const myCdBars = myMgmtTab.number('Cooldown Bars', 1, { min: 1, max: 100 });
const myTouchAge = myMgmtTab.number('Max Touch Age', 10, { min: 3, max: 200 });

const mySessionTab = input.tab('Session');
const mySessStart = mySessionTab.number('Start Hour ET', 2, { min: 0, max: 23 });
const mySessEnd = mySessionTab.number('End Hour ET', 9, { min: 0, max: 23 });

// === Core math ===
const myBbBasis = sma(close, myBbLen);
const myBbDev = mult(stdev(close, myBbLen), myBbMult);
const myBbUpper = add(myBbBasis, myBbDev);
const myBbLower = sub(myBbBasis, myBbDev);

const myFastBasis = sma(close, myFastBbLen);
const myFastDev = mult(stdev(close, myFastBbLen), myFastBbMult);
const myFastUpper = add(myFastBasis, myFastDev);
const myFastLower = sub(myFastBasis, myFastDev);

const myEma55 = ema(close, myEmaLen);
const myEmaSlope = sub(myEma55, shift(myEma55, 5));

const myAdxObject = indicators.adx(myAdxLen);
const myAdxVal = myAdxObject.adx;

// === Touch detection (sparse boolean series) ===
const myBullTouch = for_every(low, myBbLower, (_l, _b) => _l <= _b);
const myBearTouch = for_every(high, myBbUpper, (_h, _b) => _h >= _b);

const myCount = close.length;

// barssince implemented via explicit loop (no indicator calls inside)
// NOTE: "new Array(...)" is disallowed by the scripting engine, so we
// build plain arrays using Array(...).fill(...) without the "new" keyword.
const myBsSinceBull = Array(myCount).fill(null);
const myBsSinceBear = Array(myCount).fill(null);

let myLastBullIdx = -1;
let myLastBearIdx = -1;

for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
	if (myBullTouch[myIndex]) {
		myLastBullIdx = myIndex;
	}
	if (myBearTouch[myIndex]) {
		myLastBearIdx = myIndex;
	}
	myBsSinceBull[myIndex] = myLastBullIdx === -1 ? null : myIndex - myLastBullIdx;
	myBsSinceBear[myIndex] = myLastBearIdx === -1 ? null : myIndex - myLastBearIdx;
}

// ASSUMPTION: current.now/time timezone assumed to match exchange timezone which
// may differ from "America/New_York" used in the original Pine script. We use
// time_of() which resolves hours in the exchange timezone of the current symbol.
const myLongSig = Array(myCount).fill(false);
const myShortSig = Array(myCount).fill(false);

let myTradesToday = 0;
let myCurrentDaySession = null;

// Approximation of strategy.position_size==0: we track a pseudo "position open"
// state until the Time Stop bars elapse, since actual SL/TP intrabar fills
// cannot be reproduced in an indicator script. This is a simplification.
let myPositionOpenUntil = -1;

for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const mySessionKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;

	if (mySessionKey !== myCurrentDaySession) {
		myCurrentDaySession = mySessionKey;
		myTradesToday = 0;
	}

	const myEtHour = myTimeInfo.hours;
	const myInSession = myEtHour >= mySessStart && myEtHour < mySessEnd;

	const myBullSetup = myBsSinceBull[myIndex] !== null && myBsSinceBull[myIndex] >= myCdBars && myBsSinceBull[myIndex] <= myTouchAge;
	const myBearSetup = myBsSinceBear[myIndex] !== null && myBsSinceBear[myIndex] >= myCdBars && myBsSinceBear[myIndex] <= myTouchAge;

	const myBullRev = close[myIndex] > open[myIndex] && close[myIndex] > myFastBasis[myIndex];
	const myBearRev = close[myIndex] < open[myIndex] && close[myIndex] < myFastBasis[myIndex];

	const myBullTrend = close[myIndex] > myEma55[myIndex] || myEmaSlope[myIndex] > 0;
	const myBearTrend = close[myIndex] < myEma55[myIndex] || myEmaSlope[myIndex] < 0;

	const myAdxOk = myAdxVal[myIndex] !== null && myAdxVal[myIndex] > myAdxThresh;

	const myNoPos = myIndex > myPositionOpenUntil;
	const myCanTrade = myTradesToday < myMaxTrades && myInSession && myNoPos;

	const myLong = myCanTrade && myBullSetup && myBullRev && myBullTrend && myAdxOk;
	const myShort = myCanTrade && myBearSetup && myBearRev && myBearTrend && myAdxOk;

	if (myLong || myShort) {
		myTradesToday += 1;
		myPositionOpenUntil = myIndex + myTimeStop;
	}

	myLongSig[myIndex] = myLong;
	myShortSig[myIndex] = myShort;
}

// === Painting ===
const myBullColor = '#00E676';
const myBearColor = '#FF1744';
const myNeutColor = '#78909C';

const myUpperLine = paint(myBbUpper, { name: 'BBU', color: myNeutColor, thickness: 1 });
const myLowerLine = paint(myBbLower, { name: 'BBL', color: myNeutColor, thickness: 1 });
paint(myBbBasis, { name: 'MID', color: myNeutColor, style: 'dotted', thickness: 1 });

const myFastUpperLine = paint(myFastUpper, { name: 'FU', color: myBullColor, thickness: 1 });
const myFastLowerLine = paint(myFastLower, { name: 'FL', color: myBearColor, thickness: 1 });

fill(myUpperLine, myFastUpperLine, myBullColor, 0.05, 'Bull Fill');
fill(myLowerLine, myFastLowerLine, myBearColor, 0.05, 'Bear Fill');

const myEmaColor = for_every(myEmaSlope, _s => _s > 0 ? myBullColor : myBearColor);
paint(myEma55, { name: 'EMA', color: myEmaColor, thickness: 2 });

const myLongMarks = for_every(myLongSig, low, (_sig, _l) => _sig ? _l : null);
const myShortMarks = for_every(myShortSig, high, (_sig, _h) => _sig ? _h : null);

paint(myLongMarks, { name: 'Long', style: 'labels_below', color: myBullColor });
paint(myShortMarks, { name: 'Short', style: 'labels_above', color: myBearColor });

// === Signals for scanner / alerts / strategy tester ===
register_signal(myLongSig, 'Long Signal');
register_signal(myShortSig, 'Short Signal');