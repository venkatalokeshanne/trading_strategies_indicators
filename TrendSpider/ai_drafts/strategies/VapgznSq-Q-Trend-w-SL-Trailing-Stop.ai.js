describe_indicator('Q Trend Signals', 'price');

// ─────────────────────────────────────────────────────────────────────────
// NOTE: This indicator reproduces the Q-Trend trend-line/signal logic from
// the Pine script. Pine's strategy.entry/exit (stop loss, trailing stop)
// cannot be executed inside a TrendSpider indicator - there is no built in
// position/order simulation API available to Custom JS indicators. Instead
// this script exposes Long/Short entry signals (and Strong Buy/Sell) via
// register_signal(), so they can be used in the Strategy Tester, Scanner
// and Alerts modules, where actual stop/trailing-stop logic can be added.
// ─────────────────────────────────────────────────────────────────────────

const myDateTab = input.tab('Date Range');
const myUseDateFilter = myDateTab.boolean('Use Date Range Filter', true);
const myStartDateText = myDateTab.text('Start Date (YYYY-MM-DD)', '2024-01-01');
const myEndDateText = myDateTab.text('End Date (YYYY-MM-DD)', '2026-12-31');

const myMainTab = input.tab('Main Settings');
const myTrendPeriod = myMainTab.number('Trend period', 200, { min: 1, max: 1000 });
const myAtrPeriod = myMainTab.number('ATR Period', 14, { min: 1, max: 500 });
const myAtrMultiplier = myMainTab.number('ATR Multiplier', 1.0, { min: -10, max: 10, step: 0.1 });
const mySignalMode = myMainTab.select('Signal mode', 'Type A', ['Type A', 'Type B']);

const mySourceTab = input.tab('Source');
const myUseEmaSmoother = mySourceTab.boolean('Smooth source with EMA?', false);
const mySrcEmaPeriod = mySourceTab.number('EMA Smoother period', 3, { min: 1, max: 500 });

// Parse the date range (Date.parse is a static call, not "new Date()")
const myStartTimestamp = Date.parse(myStartDateText + 'T00:00:00Z') / 1000;
const myEndTimestamp = Date.parse(myEndDateText + 'T23:59:59Z') / 1000;
assert(!isNaN(myStartTimestamp) && !isNaN(myEndTimestamp), 'Invalid date range input');

// Source series
const mySrc = myUseEmaSmoother ? ema(close, mySrcEmaPeriod) : close;

// Trend channel
const myHighest = highest(mySrc, myTrendPeriod);
const myLowest = lowest(mySrc, myTrendPeriod);
const myRange = sub(myHighest, myLowest);

// ATR shifted by 1 (ta.atr(atr_p)[1])
const myAtrSeries = shift(atr(high, low, close, myAtrPeriod), 1);

const myCandleCount = close.length;

const myTrendLine = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myStrongBuySignal = series_of(false);
const myStrongSellSignal = series_of(false);
const myLineColor = series_of('gray');

// Strong buy/sell raw conditions (non-recursive)
const mySb = series_of(false);
const mySs = series_of(false);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myD8 = myRange[myIndex] / 8;
	mySb[myIndex] = open[myIndex] < (myLowest[myIndex] + myD8) && open[myIndex] >= myLowest[myIndex];
	mySs[myIndex] = open[myIndex] > (myHighest[myIndex] - myD8) && open[myIndex] <= myHighest[myIndex];
}

let myPrevFinalM = null;
let myPrevLs = '';
let myPrevLevelUp = null;
let myPrevLevelDown = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTentativeM = (myHighest[myIndex] + myLowest[myIndex]) / 2;
	const myStep2M = (myIndex > myTrendPeriod && myPrevFinalM !== null) ? myPrevFinalM : myTentativeM;

	const myAtrPrev = myAtrSeries[myIndex];
	const myEpsilon = (myAtrPrev === null || isNaN(myAtrPrev)) ? 0 : myAtrMultiplier * myAtrPrev;

	const myLevelUpCur = myStep2M + myEpsilon;
	const myLevelDownCur = myStep2M - myEpsilon;

	const myCurSrc = mySrc[myIndex];
	const myPrevSrc = myIndex > 0 ? mySrc[myIndex - 1] : myCurSrc;

	let myChangeUp = false;
	let myChangeDown = false;

	if (myIndex > 0 && myPrevLevelUp !== null && myPrevLevelDown !== null) {
		const myCrossoverUp = myCurSrc > myLevelUpCur && myPrevSrc <= myPrevLevelUp;
		const myCrossunderUp = myCurSrc < myLevelUpCur && myPrevSrc >= myPrevLevelUp;
		const myCrossUp = myCrossoverUp || myCrossunderUp;

		const myCrossoverDown = myCurSrc > myLevelDownCur && myPrevSrc <= myPrevLevelDown;
		const myCrossunderDown = myCurSrc < myLevelDownCur && myPrevSrc >= myPrevLevelDown;
		const myCrossDown = myCrossoverDown || myCrossunderDown;

		myChangeUp = (mySignalMode === 'Type B' ? myCrossUp : myCrossoverUp) || myCurSrc > myLevelUpCur;
		myChangeDown = (mySignalMode === 'Type B' ? myCrossDown : myCrossunderDown) || myCurSrc < myLevelDownCur;
	}
	else {
		myChangeUp = myCurSrc > myLevelUpCur;
		myChangeDown = myCurSrc < myLevelDownCur;
	}

	let myFinalM;
	if ((myChangeUp || myChangeDown) && myStep2M !== myPrevFinalM) {
		myFinalM = myStep2M;
	}
	else if (myChangeUp) {
		myFinalM = myLevelUpCur;
	}
	else if (myChangeDown) {
		myFinalM = myLevelDownCur;
	}
	else {
		myFinalM = (myPrevFinalM !== null) ? myPrevFinalM : myStep2M;
	}

	const myLsCur = myChangeUp ? 'B' : (myChangeDown ? 'S' : myPrevLs);

	const myInDateRange = !myUseDateFilter || (time[myIndex] >= myStartTimestamp && time[myIndex] <= myEndTimestamp);

	const myLongCondition = myChangeUp && myPrevLs !== 'B' && myInDateRange;
	const myShortCondition = myChangeDown && myPrevLs !== 'S' && myInDateRange;

	myTrendLine[myIndex] = myFinalM;
	myLineColor[myIndex] = myLsCur === 'B' ? '#26A69A' : '#EF5350';
	myLongSignal[myIndex] = myLongCondition;
	myShortSignal[myIndex] = myShortCondition;

	myStrongBuySignal[myIndex] = mySb[myIndex] || (myIndex >= 1 && mySb[myIndex - 1]) || (myIndex >= 2 && mySb[myIndex - 2]) || (myIndex >= 3 && mySb[myIndex - 3]) || (myIndex >= 4 && mySb[myIndex - 4]);
	myStrongSellSignal[myIndex] = mySs[myIndex] || (myIndex >= 1 && mySs[myIndex - 1]) || (myIndex >= 2 && mySs[myIndex - 2]) || (myIndex >= 3 && mySs[myIndex - 3]) || (myIndex >= 4 && mySs[myIndex - 4]);

	myPrevFinalM = myFinalM;
	myPrevLs = myLsCur;
	myPrevLevelUp = myLevelUpCur;
	myPrevLevelDown = myLevelDownCur;
}

paint(myTrendLine, { name: 'Trend Line', color: myLineColor, thickness: 2 });

register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myStrongBuySignal, 'Strong Buy');
register_signal(myStrongSellSignal, 'Strong Sell');