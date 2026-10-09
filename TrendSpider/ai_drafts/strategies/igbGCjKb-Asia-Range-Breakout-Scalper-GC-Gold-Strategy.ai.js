describe_indicator('Asia Range Breakout Scalper (GC Gold)', 'price');

// NOTE: This is a conversion of a Pine Script STRATEGY into an
// indicator. The Custom JS API has no order/position/backtest engine,
// so actual trade execution, trailing stops and strategy.exit() logic
// are approximated here with a manual state machine running candle by
// candle. Signals for entries/exits are exposed via register_signal()
// so they can be used in Scanners, Alerts and the Strategy Tester,
// but real fills, commissions and intrabar stop/limit behavior from
// Pine's strategy engine cannot be reproduced exactly.
const myMoment = library('moment-timezone');

// ---------------- Inputs ----------------
const sessionsTab = input.tab('Sessions');
const myAsiaSession = sessionsTab.text('Asia Session HHMM-HHMM', '1900-0000');
const myTradeSession = sessionsTab.text('Trade Window HHMM-HHMM', '0000-0500');
const myUseSessions = sessionsTab.boolean('Use session windows', true);
const myCloseAtTradeEnd = sessionsTab.boolean('Close at window end', true);

const trendTab = input.tab('Trend Filter');
const myEmaLen = trendTab.number('EMA Filter Length', 200, { min: 1, max: 1000 });
const myUseTrendFilter = trendTab.boolean('Use EMA trend filter', true);

const riskTab = input.tab('Risk');
const myAtrLen = riskTab.number('ATR Length', 14, { min: 1, max: 200 });
const riskRow1 = riskTab.row();
const mySlATR = riskRow1.number('Stop Loss ATR mult', 1.2, { min: 0.1, max: 20 });
const myTpATR = riskRow1.number('Take Profit ATR mult', 1.8, { min: 0.1, max: 20 });
const myUseTrailing = riskTab.boolean('Use trailing stop', false);
const myTrailATR = riskTab.number('Trail ATR mult', 1.0, { min: 0.1, max: 20 });

const otherTab = input.tab('Other');
const myMaxTradesPerDay = otherTab.number('Max trades per day', 2, { min: 1, max: 10 });
const myBufferTicks = otherTab.number('Breakout buffer ticks', 2, { min: 0, max: 50 });
const myTickSize = otherTab.number('Tick size', 0.1, { min: 0.0001, max: 10 });

// ---------------- Precomputed indicators (never in loops) ----------------
const myEma = ema(close, myEmaLen);
const myAtr = atr(high, low, close, myAtrLen);

// ---------------- Session parsing helpers ----------------
function myParseSession(_sessionText) {
	const myParts = _sessionText.split('-');
	const myStart = myParts[0];
	const myEnd = myParts[1];

	return {
		startH: parseInt(myStart.slice(0, 2), 10),
		startM: parseInt(myStart.slice(2, 4), 10),
		endH: parseInt(myEnd.slice(0, 2), 10),
		endM: parseInt(myEnd.slice(2, 4), 10)
	};
}

function myInSession(_minutesOfDay, _sessionDef) {
	const myStartMin = _sessionDef.startH * 60 + _sessionDef.startM;
	const myEndMin = _sessionDef.endH * 60 + _sessionDef.endM;

	if (myStartMin === myEndMin) {
		return false;
	}
	if (myStartMin < myEndMin) {
		return _minutesOfDay >= myStartMin && _minutesOfDay < myEndMin;
	}

	// overnight session (wraps past midnight)
	return _minutesOfDay >= myStartMin || _minutesOfDay < myEndMin;
}

const myAsiaDef = myParseSession(myAsiaSession);
const myTradeDef = myParseSession(myTradeSession);

// ---------------- Build NY-time context per candle ----------------
const myCandleCount = close.length;
const myInAsiaArr = [];
const myInTradeArr = [];
const myDayKeyArr = [];

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myNYMoment = myMoment.tz(time[myIndex] * 1000, 'America/New_York');
	const myMinutesOfDay = myNYMoment.hours() * 60 + myNYMoment.minutes();

	myInAsiaArr.push(myInSession(myMinutesOfDay, myAsiaDef));
	myInTradeArr.push(myInSession(myMinutesOfDay, myTradeDef));
	myDayKeyArr.push(myNYMoment.format('YYYY-MM-DD'));
}

// ---------------- State machine (reproduces Pine var/strategy logic) ----------------
const myAsiaHighOut = series_of(null);
const myAsiaLowOut = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myAsiaHigh = null;
let myAsiaLow = null;
let myRangeReady = false;
let myTradesToday = 0;
let myPositionSize = 0; // 0 flat, 1 long, -1 short
let myPositionAvgPrice = null;
let myLongStop = null;
let myLongLimit = null;
let myShortStop = null;
let myShortLimit = null;
let myTrailExtremum = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myIsNewDay = myIndex === 0 || myDayKeyArr[myIndex] !== myDayKeyArr[myIndex - 1];

	if (myIsNewDay) {
		myAsiaHigh = null;
		myAsiaLow = null;
		myRangeReady = false;
		myTradesToday = 0;
	}

	if (myInAsiaArr[myIndex]) {
		myAsiaHigh = myAsiaHigh === null ? high[myIndex] : Math.max(myAsiaHigh, high[myIndex]);
		myAsiaLow = myAsiaLow === null ? low[myIndex] : Math.min(myAsiaLow, low[myIndex]);
	}

	const myPrevInAsia = myIndex > 0 ? myInAsiaArr[myIndex - 1] : false;
	const myAsiaEnded = !myInAsiaArr[myIndex] && myPrevInAsia;

	if (myAsiaEnded && myAsiaHigh !== null && myAsiaLow !== null) {
		myRangeReady = true;
	}

	myAsiaHighOut[myIndex] = myRangeReady ? myAsiaHigh : null;
	myAsiaLowOut[myIndex] = myRangeReady ? myAsiaLow : null;

	const myOkTrade = myUseSessions ? myInTradeArr[myIndex] : true;
	const myBuffer = myBufferTicks * myTickSize;
	const myBreakUp = myRangeReady && myOkTrade && myAsiaHigh !== null && close[myIndex] > (myAsiaHigh + myBuffer);
	const myBreakDown = myRangeReady && myOkTrade && myAsiaLow !== null && close[myIndex] < (myAsiaLow - myBuffer);

	const myBullOK = close[myIndex] > myEma[myIndex];
	const myBearOK = close[myIndex] < myEma[myIndex];

	const myAllowLong = myBreakUp && (!myUseTrendFilter || myBullOK);
	const myAllowShort = myBreakDown && (!myUseTrendFilter || myBearOK);

	let myLongEntryHappened = false;
	let myShortEntryHappened = false;
	let myLongExitHappened = false;
	let myShortExitHappened = false;

	// manage exits first (based on this candle's high/low vs previously set stop/limit)
	if (myPositionSize === 1) {
		if (myUseTrailing && myTrailExtremum !== null) {
			const myTrailStop = myTrailExtremum - myTrailATR * myAtr[myIndex];
			myLongStop = myTrailStop;
		}

		const myHitStop = myLongStop !== null && low[myIndex] <= myLongStop;
		const myHitLimit = myLongLimit !== null && high[myIndex] >= myLongLimit;

		if (myHitStop || myHitLimit) {
			myPositionSize = 0;
			myLongExitHappened = true;
		}
		else if (myUseTrailing) {
			myTrailExtremum = myTrailExtremum === null ? high[myIndex] : Math.max(myTrailExtremum, high[myIndex]);
		}
	}
	else if (myPositionSize === -1) {
		if (myUseTrailing && myTrailExtremum !== null) {
			const myTrailStop = myTrailExtremum + myTrailATR * myAtr[myIndex];
			myShortStop = myTrailStop;
		}

		const myHitStop = myShortStop !== null && high[myIndex] >= myShortStop;
		const myHitLimit = myShortLimit !== null && low[myIndex] <= myShortLimit;

		if (myHitStop || myHitLimit) {
			myPositionSize = 0;
			myShortExitHappened = true;
		}
		else if (myUseTrailing) {
			myTrailExtremum = myTrailExtremum === null ? low[myIndex] : Math.min(myTrailExtremum, low[myIndex]);
		}
	}

	// close at trade window end
	const myPrevInTrade = myIndex > 0 ? myInTradeArr[myIndex - 1] : false;
	const myTradeEnded = myUseSessions && !myInTradeArr[myIndex] && myPrevInTrade;

	if (myCloseAtTradeEnd && myTradeEnded && myPositionSize !== 0) {
		if (myPositionSize === 1) {
			myLongExitHappened = true;
		}
		else {
			myShortExitHappened = true;
		}
		myPositionSize = 0;
	}

	// entries
	if (myPositionSize === 0 && myTradesToday < myMaxTradesPerDay) {
		if (myAllowLong) {
			myPositionSize = 1;
			myPositionAvgPrice = close[myIndex];
			myLongStop = myPositionAvgPrice - mySlATR * myAtr[myIndex];
			myLongLimit = myPositionAvgPrice + myTpATR * myAtr[myIndex];
			myTrailExtremum = high[myIndex];
			myTradesToday += 1;
			myLongEntryHappened = true;
		}
		else if (myAllowShort) {
			myPositionSize = -1;
			myPositionAvgPrice = close[myIndex];
			myShortStop = myPositionAvgPrice + mySlATR * myAtr[myIndex];
			myShortLimit = myPositionAvgPrice - myTpATR * myAtr[myIndex];
			myTrailExtremum = low[myIndex];
			myTradesToday += 1;
			myShortEntryHappened = true;
		}
	}

	myLongEntrySignal[myIndex] = myLongEntryHappened;
	myShortEntrySignal[myIndex] = myShortEntryHappened;
	myLongExitSignal[myIndex] = myLongExitHappened;
	myShortExitSignal[myIndex] = myShortExitHappened;
}

// ---------------- Painting ----------------
// Note: painted line names must be distinct from register_signal()
// names, otherwise the engine throws a duplicate-name error. The
// paint() names below were renamed (added "Marker") to avoid
// colliding with the register_signal() names used for scanners/alerts.
paint(myEma, { name: 'EMA', color: '#FFA726', thickness: 2 });
paint(myAsiaHighOut, { name: 'Asia High', style: 'ladder', color: '#42A5F5' });
paint(myAsiaLowOut, { name: 'Asia Low', style: 'ladder', color: '#42A5F5' });

const myLongMarks = for_every(myLongEntrySignal, low, (_sig, _low) => _sig ? _low : null);
const myShortMarks = for_every(myShortEntrySignal, high, (_sig, _high) => _sig ? _high : null);

paint(myLongMarks, { name: 'Long Entry Marker', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'Short Entry Marker', style: 'labels_above', color: '#EF5350' });

// ---------------- Signals (usable in Scanners, Alerts, Strategy Tester) ----------------
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');