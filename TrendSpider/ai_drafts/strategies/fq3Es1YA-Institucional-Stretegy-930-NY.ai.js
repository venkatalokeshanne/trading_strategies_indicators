describe_indicator('9:30 AM Precision Breakout', 'price');

// ======================================================
// NOTE: This script approximates syminfo.mintick with
// 1 / 10^current.decimals, since the Custom JS API does
// not expose a direct "minimum tick" value. This is a
// reasonable approximation for most symbols but may not
// be perfectly exact for some exotic instruments.
// ======================================================

const myMoment = library('moment-timezone');

// -------------------- Inputs --------------------
const myTab = input.tab('Settings');

const myRefStartRow = myTab.row();
const myRefStartHour = myRefStartRow.number('Ref Candle Start Hour (NY)', 9, { min: 0, max: 23 });
const myRefStartMinute = myRefStartRow.number('Ref Candle Start Min (NY)', 30, { min: 0, max: 59 });

const myRefEndRow = myTab.row();
const myRefEndHour = myRefEndRow.number('Ref Candle End Hour (NY)', 9, { min: 0, max: 23 });
const myRefEndMinute = myRefEndRow.number('Ref Candle End Min (NY)', 35, { min: 0, max: 59 });

const myTradeStartRow = myTab.row();
const myTradeStartHour = myTradeStartRow.number('Trade Window Start Hour (NY)', 9, { min: 0, max: 23 });
const myTradeStartMinute = myTradeStartRow.number('Trade Window Start Min (NY)', 36, { min: 0, max: 59 });

const myTradeEndRow = myTab.row();
const myTradeEndHour = myTradeEndRow.number('Trade Window End Hour (NY)', 15, { min: 0, max: 23 });
const myTradeEndMinute = myTradeEndRow.number('Trade Window End Min (NY)', 50, { min: 0, max: 59 });

const myRiskGroup = myTab.group('Risk');
const myTpRatio = myRiskGroup.number('TP Ratio (R:R)', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myMinSlFx = myRiskGroup.number('Min SL (Forex, pips*10)', 10.0, { min: 0, max: 1000 });
const myMinSlIdx = myRiskGroup.number('Min SL (Index/Stock, ticks)', 1500.0, { min: 0, max: 100000 });

// -------------------- Precompute NY session info --------------------
const myNyTimes = time.map(_t => myMoment.unix(_t).tz('America/New_York'));
const myDayKeys = myNyTimes.map(_m => _m.format('YYYYMMDD'));
const myMinuteOfDay = myNyTimes.map(_m => _m.hours() * 60 + _m.minutes());

const myRefStartMin = myRefStartHour * 60 + myRefStartMinute;
const myRefEndMin = myRefEndHour * 60 + myRefEndMinute;
const myTradeStartMin = myTradeStartHour * 60 + myTradeStartMinute;
const myTradeEndMin = myTradeEndHour * 60 + myTradeEndMinute;

const myIsForex = current.assetType === 'fx';
const myMinTick = Math.pow(10, -(current.decimals || 2));
const myMinSl = myIsForex ? (myMinSlFx * myMinTick * 10) : (myMinSlIdx * myMinTick);

// -------------------- Main loop (sequential state machine, mirrors Pine logic) --------------------
const myHiLine = series_of(null);
const myLoLine = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const mySlLine = series_of(null);
const myTpLine = series_of(null);

let myHi930 = null;
let myLo930 = null;
let myTradesCount = 0;
let myLastDay = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// New trading day: reset state (equivalent to ta.change(time("D", ...)))
	if (myDayKeys[myIndex] !== myLastDay) {
		myLastDay = myDayKeys[myIndex];
		myHi930 = null;
		myLo930 = null;
		myTradesCount = 0;
	}

	// Capture institutional reference candle range
	const myMinuteNow = myMinuteOfDay[myIndex];
	if (myMinuteNow >= myRefStartMin && myMinuteNow < myRefEndMin) {
		myHi930 = (myHi930 === null) ? high[myIndex] : Math.max(myHi930, high[myIndex]);
		myLo930 = (myLo930 === null) ? low[myIndex] : Math.min(myLo930, low[myIndex]);
	}

	myHiLine[myIndex] = myHi930;
	myLoLine[myIndex] = myLo930;

	const myCanTrade = myMinuteNow >= myTradeStartMin && myMinuteNow <= myTradeEndMin
		&& myTradesCount === 0 && myHi930 !== null && myLo930 !== null;

	const myLongBodyBreak = myCanTrade && close[myIndex] > myHi930;
	const myShortBodyBreak = myCanTrade && close[myIndex] < myLo930;

	myLongSignal[myIndex] = myLongBodyBreak;
	myShortSignal[myIndex] = myShortBodyBreak;

	if (myLongBodyBreak) {
		const mySlDist = Math.max(myHi930 - myLo930, myMinSl);
		mySlLine[myIndex] = myHi930 - mySlDist;
		myTpLine[myIndex] = myHi930 + (mySlDist * myTpRatio);
		myTradesCount = 1;
	}
	else if (myShortBodyBreak) {
		const mySlDist = Math.max(myHi930 - myLo930, myMinSl);
		mySlLine[myIndex] = myLo930 + mySlDist;
		myTpLine[myIndex] = myLo930 - (mySlDist * myTpRatio);
		myTradesCount = 1;
	}
	else {
		mySlLine[myIndex] = null;
		myTpLine[myIndex] = null;
	}
}

// -------------------- Painting --------------------
paint(myHiLine, { name: 'Zona Alta', color: '#2962FF', thickness: 2, style: 'ladder' });
paint(myLoLine, { name: 'Zona Baja', color: '#2962FF', thickness: 2, style: 'ladder' });

const myLongMarks = for_every(myLongSignal, low, (_l, _lo) => _l ? _lo : null);
const myShortMarks = for_every(myShortSignal, high, (_s, _hi) => _s ? _hi : null);

paint(myLongMarks, { name: 'Long Entry', color: '#26A69A', style: 'labels_below' });
paint(myShortMarks, { name: 'Short Entry', color: '#EF5350', style: 'labels_above' });

paint(mySlLine, { name: 'Stop Loss', color: 'red', style: 'dotted', thickness: 2 });
paint(myTpLine, { name: 'Take Profit', color: 'green', style: 'dotted', thickness: 2 });

// -------------------- Signals for Scanner / Alerts / Strategy Tester --------------------
register_signal(myLongSignal, 'Long Entry Breakout');
register_signal(myShortSignal, 'Short Entry Breakout');