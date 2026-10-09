describe_indicator('Gold Swing More Trades', 'price');

// ───────────────────────────────────────────────────────────
// Inputs (grouped to keep panel readable)
// ───────────────────────────────────────────────────────────
const myEmaTab = input.tab('Core');
const myEmaFastLen = myEmaTab.number('Fast EMA', 20, { min: 1, max: 500 });
const myEmaSlowLen = myEmaTab.number('Slow EMA', 50, { min: 1, max: 500 });
const myRsiLen = myEmaTab.number('RSI Length', 14, { min: 1, max: 200 });

const myRsiRow = myEmaTab.row();
const myRsiLongMin = myRsiRow.number('RSI Long Min', 54, { min: 1, max: 100 });
const myRsiShortMax = myRsiRow.number('RSI Short Max', 46, { min: 1, max: 100 });

const myToggleRow = myEmaTab.row();
const myEnableLongs = myToggleRow.boolean('Enable Longs', true);
const myEnableShorts = myToggleRow.boolean('Enable Shorts', true);

const mySessionTab = input.tab('Session & Risk');
const myUseSessionFilter = mySessionTab.boolean('Use Session Filter', true);
const mySessionStartHour = mySessionTab.number('Session Start Hour', 6, { min: 0, max: 23 });
const mySessionEndHour = mySessionTab.number('Session End Hour', 20, { min: 0, max: 23 });
const myCooldownBars = mySessionTab.number('Cooldown Bars', 2, { min: 0, max: 50 });

const myRiskRow = mySessionTab.row();
const mySlPips = myRiskRow.number('SL Pips', 50, { min: 0.1, max: 10000, step: 0.1 });
const myTpPips = myRiskRow.number('TP Pips', 100, { min: 0.1, max: 10000, step: 0.1 });
const myPipSize = myRiskRow.number('Pip Size', 0.1, { min: 0.00001, max: 10, step: 0.00001 });

const myTagTab = input.tab('Signal Tag');
const myShowTradeTag = myTagTab.boolean('Show Signal Tag', true);
const myTagAtrOffset = myTagTab.number('Tag ATR Offset', 0.45, { min: 0.05, max: 10, step: 0.05 });

// ───────────────────────────────────────────────────────────
// Core series
// ───────────────────────────────────────────────────────────
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myRsiVal = rsi(close, myRsiLen);
const myAtrVal = atr(high, low, close, 14);

// Daily-reset VWAP (Pine's ta.vwap resets every session/day by default).
// We approximate "day" using bar_at() daily session id.
const myVwapVal = [];
let myCumPV = 0;
let myCumV = 0;
let myPrevDay = null;
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myDayId = bar_at(time[myIndex]).session;
	if (myDayId !== myPrevDay) {
		myCumPV = 0;
		myCumV = 0;
		myPrevDay = myDayId;
	}
	const myTypicalPrice = hlc3[myIndex];
	myCumPV += myTypicalPrice * volume[myIndex];
	myCumV += volume[myIndex];
	myVwapVal.push(myCumV !== 0 ? myCumPV / myCumV : myTypicalPrice);
}

// ───────────────────────────────────────────────────────────
// Session filter: approximates Pine's session("0600-2000"):"23456"
// (Mon-Fri). ISO dayOfWeek: 1=Mon ... 7=Sun.
// ───────────────────────────────────────────────────────────
const mySessionOk = [];
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myStartMinutes = mySessionStartHour * 60;
	const myEndMinutes = mySessionEndHour * 60;
	const myIsWeekday = myTimeInfo.dayOfWeek >= 1 && myTimeInfo.dayOfWeek <= 5;
	const myInSession = myIsWeekday && myMinutesOfDay >= myStartMinutes && myMinutesOfDay < myEndMinutes;
	mySessionOk.push(myUseSessionFilter ? myInSession : true);
}

// ───────────────────────────────────────────────────────────
// Main loop: reproduces trend/reclaim conditions, cooldown logic
// and a simplified strategy position simulation (entry on close,
// SL/TP checked against subsequent candles' high/low).
// ───────────────────────────────────────────────────────────
const myLongSignalArr = series_of(false);
const myShortSignalArr = series_of(false);
const myPositionSizeArr = series_of(0);
const myBuyTagArr = series_of(null);
const mySellTagArr = series_of(null);

let myLastTradeBar = null;
let myPositionSize = 0;
let myStopPrice = null;
let myTakePrice = null;
let myPositionIsLong = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// Check SL/TP hit against the current candle before evaluating new signals
	if (myPositionSize !== 0) {
		if (myPositionIsLong) {
			if (low[myIndex] <= myStopPrice || high[myIndex] >= myTakePrice) {
				myPositionSize = 0;
			}
		}
		else {
			if (high[myIndex] >= myStopPrice || low[myIndex] <= myTakePrice) {
				myPositionSize = 0;
			}
		}
	}

	const myEmaFastRising = myIndex >= 2 && myEmaFast[myIndex] > myEmaFast[myIndex - 2];
	const myEmaFastFalling = myIndex >= 2 && myEmaFast[myIndex] < myEmaFast[myIndex - 2];

	const myBullTrend = close[myIndex] > myVwapVal[myIndex] && myEmaFast[myIndex] > myEmaSlow[myIndex] && myEmaFastRising;
	const myBearTrend = close[myIndex] < myVwapVal[myIndex] && myEmaFast[myIndex] < myEmaSlow[myIndex] && myEmaFastFalling;

	const myBullReclaim = low[myIndex] <= myEmaFast[myIndex] && close[myIndex] > myEmaFast[myIndex] && close[myIndex] > open[myIndex];
	const myBearReclaim = high[myIndex] >= myEmaFast[myIndex] && close[myIndex] < myEmaFast[myIndex] && close[myIndex] < open[myIndex];

	const myRsiLongOk = myRsiVal[myIndex] >= myRsiLongMin;
	const myRsiShortOk = myRsiVal[myIndex] <= myRsiShortMax;

	const myCooldownOk = myLastTradeBar === null || (myIndex - myLastTradeBar > myCooldownBars);

	const myLongSignal = myEnableLongs && mySessionOk[myIndex] && myCooldownOk && myBullTrend && myBullReclaim && myRsiLongOk && myPositionSize <= 0;
	const myShortSignal = myEnableShorts && mySessionOk[myIndex] && myCooldownOk && myBearTrend && myBearReclaim && myRsiShortOk && myPositionSize >= 0;

	myLongSignalArr[myIndex] = myLongSignal;
	myShortSignalArr[myIndex] = myShortSignal;

	if (myLongSignal) {
		const myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice - (mySlPips * myPipSize);
		myTakePrice = myEntryPrice + (myTpPips * myPipSize);
		myPositionIsLong = true;
		myPositionSize = 1;
		myLastTradeBar = myIndex;

		if (myShowTradeTag) {
			myBuyTagArr[myIndex] = low[myIndex] - myAtrVal[myIndex] * myTagAtrOffset;
		}
	}
	else if (myShortSignal) {
		const myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice + (mySlPips * myPipSize);
		myTakePrice = myEntryPrice - (myTpPips * myPipSize);
		myPositionIsLong = false;
		myPositionSize = -1;
		myLastTradeBar = myIndex;

		if (myShowTradeTag) {
			mySellTagArr[myIndex] = high[myIndex] + myAtrVal[myIndex] * myTagAtrOffset;
		}
	}

	myPositionSizeArr[myIndex] = myPositionSize;
}

// ───────────────────────────────────────────────────────────
// Painting
// ───────────────────────────────────────────────────────────
paint(myVwapVal, { name: 'VWAP', color: '#f0c419', thickness: 2 });
paint(myEmaFast, { name: 'EMA Fast', color: '#1fc3c0', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#ff8c42', thickness: 2 });

const myBuyShapeLine = for_every(myLongSignalArr, low, (_signal, _low) => _signal ? _low : null);
const mySellShapeLine = for_every(myShortSignalArr, high, (_signal, _high) => _signal ? _high : null);

paint(myBuyShapeLine, { name: 'Buy Signal', style: 'labels_below', color: '#2ecc71' });
paint(mySellShapeLine, { name: 'Sell Signal', style: 'labels_above', color: '#e74c3c' });

const myBuyTagLine = myShowTradeTag ? myBuyTagArr : series_of(null);
const mySellTagLine = myShowTradeTag ? mySellTagArr : series_of(null);
paint(myBuyTagLine, { name: 'Buy Tag', style: 'labels_below', color: '#2ecc71' });
paint(mySellTagLine, { name: 'Sell Tag', style: 'labels_above', color: '#e74c3c' });

register_signal(myLongSignalArr, 'Entry Up');
register_signal(myShortSignalArr, 'Entry Down');