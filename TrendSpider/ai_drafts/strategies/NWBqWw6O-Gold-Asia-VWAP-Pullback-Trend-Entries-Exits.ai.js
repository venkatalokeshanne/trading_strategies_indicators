describe_indicator('GC Asia VWAP Pullback Trend', 'price');

// ───────── Inputs
const generalTab = input.tab('General');
const myTimezone = generalTab.text('Timezone', 'America/New_York');
const mySessionString = generalTab.text('Asia Session (trade only)', '1800-0300');

const trendTab = input.tab('Trend Filter');
const myUseEma = trendTab.boolean('Use EMA Trend Filter (optional)', false);
const myEmaLen = trendTab.number('EMA Length', 100, { min: 1, max: 500 });

const entryTab = input.tab('Entry');
const entryRow1 = entryTab.row();
const myVwapBand = entryRow1.number('VWAP pullback band (dollars)', 0.60, { min: 0, max: 100, step: 0.05 });
const myConfirmClose = entryRow1.boolean('Require close back through VWAP after touch', true);
const myOneTradePerDay = entryTab.boolean('Max 1 trade per day', false);

const exitTab = input.tab('Exits (reference only)');
const useAtrGroup = exitTab.group('ATR stop/target');
const myUseATR = useAtrGroup.boolean('Use ATR stop/target', true);
const atrRow = useAtrGroup.row();
const myAtrLen = atrRow.number('ATR Length', 14, { min: 1, max: 200 });
const myStopATR = atrRow.number('Stop = ATR x', 1.2, { min: 0.1, max: 20, step: 0.1 });
const myTgtATR = atrRow.number('Target = ATR x', 1.8, { min: 0.1, max: 20, step: 0.1 });

const fixedGroup = exitTab.group('Fixed dollar stop/target (overrides ATR if ON)');
const myUseFixed = fixedGroup.boolean('Use fixed dollar stop/target', false);
const fixedRow = fixedGroup.row();
const myStopDol = fixedRow.number('Stop (dollars)', 4.0, { min: 0.1, max: 1000, step: 0.1 });
const myTgtDol = fixedRow.number('Target (dollars)', 7.0, { min: 0.1, max: 1000, step: 0.1 });

const myUseTimeExit = exitTab.boolean('Time exit at session end', true);

// ───────── Session parsing
// Parses "HHMM-HHMM" into minute-of-day boundaries. Supports overnight wrap.
const mySessionMatch = mySessionString.match(/(\d{2})(\d{2})-(\d{2})(\d{2})/);
assert(mySessionMatch, `Invalid session string: "${mySessionString}"`);
const myStartMinute = parseInt(mySessionMatch[1], 10) * 60 + parseInt(mySessionMatch[2], 10);
const myEndMinute = parseInt(mySessionMatch[3], 10) * 60 + parseInt(mySessionMatch[4], 10);
const myWrapsMidnight = myEndMinute <= myStartMinute;
const myMoment = library('moment-timezone');

// ───────── Per-candle helpers (session flag, day key)
// NOTE: "new Array(n)" is prohibited by the engine; using "Array(n)"
// (without "new") works the same way, so we use that instead.
const myBarCount = close.length;
const myInAsia = Array(myBarCount);
const myDayKey = Array(myBarCount);

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myLocalMoment = myMoment(time[myIndex] * 1000).tz(myTimezone);
	const myMinuteOfDay = myLocalMoment.hours() * 60 + myLocalMoment.minutes();
	myInAsia[myIndex] = myWrapsMidnight
		? (myMinuteOfDay >= myStartMinute || myMinuteOfDay < myEndMinute)
		: (myMinuteOfDay >= myStartMinute && myMinuteOfDay < myEndMinute);
	myDayKey[myIndex] = myLocalMoment.format('YYYYMMDD');
}

// ───────── Manual session/day-anchored VWAP (resets on new day in tz)
const myTypicalPrice = hlc3;
const myVwapSeries = Array(myBarCount).fill(null);
let myCumPV = 0;
let myCumVol = 0;

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myIsNewDay = myIndex === 0 || myDayKey[myIndex] !== myDayKey[myIndex - 1];

	if (myIsNewDay) {
		myCumPV = 0;
		myCumVol = 0;
	}

	myCumPV += myTypicalPrice[myIndex] * volume[myIndex];
	myCumVol += volume[myIndex];
	myVwapSeries[myIndex] = myCumVol !== 0 ? (myCumPV / myCumVol) : myTypicalPrice[myIndex];
}

// ───────── Trend filter and ATR (built-in calls, outside loops)
const myEmaSeries = ema(close, myEmaLen);
const myAtrSeries = atr(high, low, close, myAtrLen);

// ───────── Sequential entry logic (stateful: new-day reset, one-trade gate)
const myLongSignal = Array(myBarCount).fill(false);
const myShortSignal = Array(myBarCount).fill(false);
const mySessionEndExit = Array(myBarCount).fill(false);
let myTradedToday = false;

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myIsNewDay = myIndex === 0 || myDayKey[myIndex] !== myDayKey[myIndex - 1];

	if (myIsNewDay) {
		myTradedToday = false;
	}

	const myCanTrade = (!myOneTradePerDay) || (myOneTradePerDay && !myTradedToday);
	const myVwapValue = myVwapSeries[myIndex];
	const myTrendLongOk = close[myIndex] > myVwapValue && (!myUseEma || close[myIndex] > myEmaSeries[myIndex]);
	const myTrendShortOk = close[myIndex] < myVwapValue && (!myUseEma || close[myIndex] < myEmaSeries[myIndex]);

	const myTouchLong = myInAsia[myIndex] && myCanTrade && myTrendLongOk &&
		low[myIndex] <= (myVwapValue + myVwapBand) && low[myIndex] >= (myVwapValue - myVwapBand);
	const myTouchShort = myInAsia[myIndex] && myCanTrade && myTrendShortOk &&
		high[myIndex] >= (myVwapValue - myVwapBand) && high[myIndex] <= (myVwapValue + myVwapBand);

	const myLong = myTouchLong && (!myConfirmClose || close[myIndex] > myVwapValue);
	const myShort = myTouchShort && (!myConfirmClose || close[myIndex] < myVwapValue);

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;

	if (myLong || myShort) {
		myTradedToday = true;
	}

	const myWasInAsiaPrev = myIndex > 0 && myInAsia[myIndex - 1];
	mySessionEndExit[myIndex] = myUseTimeExit && (!myInAsia[myIndex]) && myWasInAsiaPrev;
}

// ───────── Reference stop/target distances (informational only, see note below)
const myStopDistance = for_every(myAtrSeries, _atr => myUseFixed ? myStopDol : (_atr * myStopATR));
const myTargetDistance = for_every(myAtrSeries, _atr => myUseFixed ? myTgtDol : (_atr * myTgtATR));

// ───────── Visuals
paint(myVwapSeries, { name: 'VWAP', color: '#00BCD4', thickness: 2 });
paint(myUseEma ? myEmaSeries : constants.empty_series, { name: 'EMA', color: '#FFD54F', thickness: 1 });

const myLongMarks = myLongSignal.map((_v, _i) => _v ? low[_i] : null);
const myShortMarks = myShortSignal.map((_v, _i) => _v ? high[_i] : null);

paint(myLongMarks, { name: 'Long Pullback', style: 'labels_below', color: '#00E676' });
paint(myShortMarks, { name: 'Short Pullback', style: 'labels_above', color: '#FF5252' });

// ───────── Signals for scanner/alerts/strategy tester
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(mySessionEndExit, 'Session End Exit');