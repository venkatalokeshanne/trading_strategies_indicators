describe_indicator('Booming Bull: VWAP + Stoch RSI + Multi-Pivot', 'price');

// ==========================================================
// NOTE: This indicator reproduces the core logic of the
// supplied Pine Script (VWAP, daily pivots, Stoch RSI,
// pivot crosses, buy/sell/EOD-exit conditions) as closely
// as the Custom JS API allows. A few approximations were
// unavoidable - see the flagged notes.
// ==========================================================

const myInputsTab = input.tab('Settings');
const myLogicGroup = myInputsTab.group('Logic');
const myEfficiencyFilter = myLogicGroup.boolean('Enable Efficiency Filter', true);
const myOnlyCentralPivot = myLogicGroup.boolean('Only Central Pivot', false);

const mySessionGroup = myInputsTab.group('Session And Profit');
const mySessionText = mySessionGroup.text('Trading Session Entry Window', '0915-1500');
const myProfitMode = mySessionGroup.select('Profit Mode', 'Risk/Reward', ['1% Price', 'Risk/Reward']);
const myRrRatio = mySessionGroup.number('Risk Reward Ratio', 1.5, { min: 0.1, max: 20 });

// ----------------------------------------------------------
// 1. VWAP, reset daily (session-anchored)
// ----------------------------------------------------------
const mySessionIdAtIndex = time.map(_t => bar_at(_t).session);
const myVwapValues = series_of(null);
let myCumPV = 0;
let myCumVol = 0;
let myPrevSessionId = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (mySessionIdAtIndex[myIndex] !== myPrevSessionId) {
		myCumPV = 0;
		myCumVol = 0;
		myPrevSessionId = mySessionIdAtIndex[myIndex];
	}
	const myTypicalPrice = hlc3[myIndex];
	const myVol = volume[myIndex] || 0;
	myCumPV += myTypicalPrice * myVol;
	myCumVol += myVol;
	myVwapValues[myIndex] = myCumVol > 0 ? myCumPV / myCumVol : myTypicalPrice;
}

paint(myVwapValues, { name: 'VWAP', color: '#f0c419', thickness: 2 });

// ----------------------------------------------------------
// 2. Daily pivots, computed from previous day's H/L/C
// ----------------------------------------------------------
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching daily data: ' + myDailyData.error);

const myPrevHigh = shift(myDailyData.high, 1);
const myPrevLow = shift(myDailyData.low, 1);
const myPrevClose = shift(myDailyData.close, 1);

const myP = div(add(myPrevHigh, myPrevLow, myPrevClose), 3);
const myR1 = sub(mult(myP, 2), myPrevLow);
const myS1 = sub(mult(myP, 2), myPrevHigh);
const myR2 = add(myP, sub(myPrevHigh, myPrevLow));
const myS2 = sub(myP, sub(myPrevHigh, myPrevLow));

// FIX: mult() requires its first argument to be a series.
// Previously these calls passed the constant "2" first
// (mult(2, series)) which raised "first argument is not
// a series". Swapped the arguments so the series comes first.
const myR3 = add(myPrevHigh, mult(sub(myP, myPrevLow), 2));
const myS3 = sub(myPrevLow, mult(sub(myPrevHigh, myP), 2));

const myLandAndFill = _series => interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, _series, time, 'le'),
	'constant'
);

const myPLine = myLandAndFill(myP);
const myR1Line = myLandAndFill(myR1);
const myS1Line = myLandAndFill(myS1);
const myR2Line = myLandAndFill(myR2);
const myS2Line = myLandAndFill(myS2);
const myR3Line = myLandAndFill(myR3);
const myS3Line = myLandAndFill(myS3);

paint(myPLine, { name: 'P', color: '#2962ff', style: 'ladder' });
paint(myR1Line, { name: 'R1', color: '#ef5350', style: 'ladder' });
paint(myS1Line, { name: 'S1', color: '#26a69a', style: 'ladder' });
paint(myR2Line, { name: 'R2', color: '#8d1f1f', style: 'ladder' });
paint(myS2Line, { name: 'S2', color: '#64dd17', style: 'ladder' });
paint(myR3Line, { name: 'R3', color: '#d50000', style: 'ladder' });
paint(myS3Line, { name: 'S3', color: '#00c853', style: 'ladder' });

// ----------------------------------------------------------
// 3. Stochastic RSI (K smoothed x3, D smoothed x3 of K)
// ----------------------------------------------------------
const myRsiValue = rsi(close, 14);
const myStochRaw = stochastic(myRsiValue, myRsiValue, myRsiValue, 14);
const myStochK = sma(myStochRaw, 3);
const myStochD = sma(myStochK, 3);

// ----------------------------------------------------------
// 4. Crossover / crossunder helpers (built from differences)
// ----------------------------------------------------------
function myCrossUp(_a, _b) {
	const myDiff = sub(_a, _b);
	const myPrevDiff = shift(myDiff, 1);
	return for_every(myDiff, myPrevDiff, (_d, _pd) => _d > 0 && _pd <= 0);
}

function myCrossDown(_a, _b) {
	const myDiff = sub(_a, _b);
	const myPrevDiff = shift(myDiff, 1);
	return for_every(myDiff, myPrevDiff, (_d, _pd) => _d < 0 && _pd >= 0);
}

const myPivotLevels = [myPLine, myR1Line, myR2Line, myR3Line, myS1Line, myS2Line, myS3Line];

function myAnyPivotCross(_crossFn) {
	const myLevelsToUse = myOnlyCentralPivot ? [myPLine] : myPivotLevels;
	const myCrossSeries = myLevelsToUse.map(_level => _crossFn(close, _level));
	return myCrossSeries.reduce((_acc, _series) => for_every(_acc, _series, (_a, _b) => _a || _b));
}

const myPivotCrossDown = myAnyPivotCross(myCrossDown);
const myPivotCrossUp = myAnyPivotCross(myCrossUp);

const myStochCrossDown = myCrossDown(myStochK, myStochD);
const myStochCrossUp = myCrossUp(myStochK, myStochD);
const myStochIsBearish = for_every(myStochK, myStochD, (_k, _d) => _k < _d);
const myStochIsBullish = for_every(myStochK, myStochD, (_k, _d) => _k > _d);

// ----------------------------------------------------------
// 5. Session filter
// Approximation: parses "HHMM-HHMM" session text and checks
// the exchange local hour/minute of each candle. The original
// script's custom "tzOffset" parameter (e.g. GMT+530) is not
// reproducible via the Custom JS API, so the exchange's own
// timezone is used instead.
// ----------------------------------------------------------
const mySessionParts = mySessionText.split('-');
const mySessionStartNum = parseInt(mySessionParts[0], 10) || 915;
const mySessionEndNum = parseInt(mySessionParts[1], 10) || 1500;

function myHHMMToMinutes(_num) {
	const myHours = Math.floor(_num / 100);
	const myMinutes = _num % 100;
	return myHours * 60 + myMinutes;
}

const mySessionStartMin = myHHMMToMinutes(mySessionStartNum);
const mySessionEndMin = myHHMMToMinutes(mySessionEndNum);

const myInSession = time.map(_t => {
	const myParsed = time_of(_t);
	const myMinutesOfDay = myParsed.hours * 60 + myParsed.minutes;
	return myMinutesOfDay >= mySessionStartMin && myMinutesOfDay <= mySessionEndMin;
});

const myEodExit = time.map(_t => {
	const myParsed = time_of(_t);
	const myMinutesOfDay = myParsed.hours * 60 + myParsed.minutes;
	return myMinutesOfDay >= mySessionEndMin;
});

// ----------------------------------------------------------
// 6. Buy / Sell conditions
// ----------------------------------------------------------
const myCloseBelowVwap = for_every(close, myVwapValues, (_c, _v) => _c < _v);
const myCloseAboveVwap = for_every(close, myVwapValues, (_c, _v) => _c > _v);

const mySellCondition = myEfficiencyFilter
	? for_every(myInSession, myCloseBelowVwap, myStochIsBearish, myPivotCrossDown, (_s, _b, _bear, _pc) => _s && _b && _bear && _pc)
	: for_every(myInSession, myCloseBelowVwap, myStochCrossDown, myPivotCrossDown, (_s, _b, _sc, _pc) => _s && _b && _sc && _pc);

const myBuyCondition = myEfficiencyFilter
	? for_every(myInSession, myCloseAboveVwap, myStochIsBullish, myPivotCrossUp, (_s, _a, _bull, _pc) => _s && _a && _bull && _pc)
	: for_every(myInSession, myCloseAboveVwap, myStochCrossUp, myPivotCrossUp, (_s, _a, _sc, _pc) => _s && _a && _sc && _pc);

register_signal(myBuyCondition, 'Buy Signal');
register_signal(mySellCondition, 'Sell Signal');
register_signal(myEodExit, 'EOD Exit 1500');

// ----------------------------------------------------------
// 7. Candle coloring, mirroring barcolor() in Pine
// ----------------------------------------------------------
const myCandleColors = for_every(myStochIsBullish, _bull => _bull ? 'teal' : 'maroon');
color_candles(myCandleColors);