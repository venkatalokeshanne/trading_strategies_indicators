describe_indicator('NQ 21 EMA Root Pullback Strong Confirmation', 'price');

// NOTE: this script reproduces the Pine Script indicator math and entry
// signal logic. TrendSpider Custom JS API has no strategy/backtest engine
// (no strategy.entry/exit, no position sizing, no stop/take management),
// so stop/take and auto position tracking from the Pine strategy are not
// executed here. Instead this indicator exposes Long/Short entry signals
// via register_signal(), so they can be used in Scanners/Alerts/Backtester.

const myMoment = library('moment-timezone');

// ─── Inputs ───────────────────────────────────────────────────────────────
const myDateTab = input.tab('Date Range');
const myStartDate = myDateTab.text('Start Date (YYYY-MM-DD)', '2026-04-01');
const myEndDate = myDateTab.text('End Date (YYYY-MM-DD)', '2026-05-01');

const mySessionTab = input.tab('Session & Trend');
const mySessionRow = mySessionTab.row();
const mySessionStart = mySessionRow.text('Session Start (HHMM)', '0930');
const mySessionEnd = mySessionRow.text('Session End (HHMM)', '1200');

const myTrendDistance = mySessionTab.number('Trend Distance', 10.0, { min: 0, max: 1000 });
const myMaxTradesPerDay = mySessionTab.number('Max Trades Per Day', 2, { min: 1, max: 50 });

const myRiskTab = input.tab('Risk (reference only)');
const myRiskRow = myRiskTab.row();
const myStopTicks = myRiskRow.number('Stop Ticks', 20, { min: 1, max: 10000 });
const myTakeTicks = myRiskRow.number('Take Ticks', 80, { min: 1, max: 10000 });

// ─── Core series ────────────────────────────────────────────────────────
const myEmaClose = ema(close, 21);
const myEmaHigh = ema(high, 21);
const myEmaLow = ema(low, 21);
const myRoot = sma(myEmaClose, 21);

const myStartTimestamp = myMoment.tz(myStartDate, 'YYYY-MM-DD', current.session.timezone).startOf('day').unix();
const myEndTimestamp = myMoment.tz(myEndDate, 'YYYY-MM-DD', current.session.timezone).endOf('day').unix();

const mySessionStartHour = parseInt(mySessionStart.slice(0, 2), 10);
const mySessionStartMinute = parseInt(mySessionStart.slice(2, 4), 10);
const mySessionEndHour = parseInt(mySessionEnd.slice(0, 2), 10);
const mySessionEndMinute = parseInt(mySessionEnd.slice(2, 4), 10);

const myLongSignal = series_of(null);
const myShortSignal = series_of(null);

let myTradesToday = 0;
let myPreviousDayKey = null;
let myPositionOpen = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;

	if (myPreviousDayKey !== null && myDayKey !== myPreviousDayKey) {
		myTradesToday = 0;
		myPositionOpen = false;
	}
	myPreviousDayKey = myDayKey;

	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const mySessionStartMinutesOfDay = mySessionStartHour * 60 + mySessionStartMinute;
	const mySessionEndMinutesOfDay = mySessionEndHour * 60 + mySessionEndMinute;
	const myTradeSession = myMinutesOfDay >= mySessionStartMinutesOfDay && myMinutesOfDay <= mySessionEndMinutesOfDay;

	const myInDateRange = time[myIndex] >= myStartTimestamp && time[myIndex] <= myEndTimestamp;

	const myValidLongTrend = myRoot[myIndex] < myEmaClose[myIndex];
	const myValidShortTrend = myRoot[myIndex] > myEmaClose[myIndex];

	const myStrongLongTrend = close[myIndex] > myEmaClose[myIndex] + myTrendDistance;
	const myStrongShortTrend = close[myIndex] < myEmaClose[myIndex] - myTrendDistance;

	const myPrevLow = myIndex > 0 ? low[myIndex - 1] : null;
	const myPrevHigh = myIndex > 0 ? high[myIndex - 1] : null;
	const myPrevEmaClose = myIndex > 0 ? myEmaClose[myIndex - 1] : null;

	const myLongPullback = myIndex > 0 && myPrevLow <= myPrevEmaClose;
	const myShortPullback = myIndex > 0 && myPrevHigh >= myPrevEmaClose;

	const myLongConfirmation = myIndex > 0 && close[myIndex] > open[myIndex] && close[myIndex] > myPrevHigh && close[myIndex] > myEmaClose[myIndex];
	const myShortConfirmation = myIndex > 0 && close[myIndex] < open[myIndex] && close[myIndex] < myPrevLow && close[myIndex] < myEmaClose[myIndex];

	const myLongCondition = myInDateRange && myTradeSession && myValidLongTrend && myStrongLongTrend && myLongPullback && myLongConfirmation && myTradesToday < myMaxTradesPerDay;
	const myShortCondition = myInDateRange && myTradeSession && myValidShortTrend && myStrongShortTrend && myShortPullback && myShortConfirmation && myTradesToday < myMaxTradesPerDay;

	if (myLongCondition && !myPositionOpen) {
		myLongSignal[myIndex] = true;
		myTradesToday += 1;
		myPositionOpen = true;
	}
	else if (myShortCondition && !myPositionOpen) {
		myShortSignal[myIndex] = true;
		myTradesToday += 1;
		myPositionOpen = true;
	}
}

// ─── Plots ─────────────────────────────────────────────────────────────────
paint(myEmaClose, { name: 'EMA Close 21', color: '#f1c40f', thickness: 2 });
paint(myEmaHigh, { name: 'EMA High 21', color: '#2ecc71', thickness: 1 });
paint(myEmaLow, { name: 'EMA Low 21', color: '#e74c3c', thickness: 1 });
paint(myRoot, { name: 'Root SMA 21', color: '#3498db', thickness: 2 });

const myLongMarks = for_every(myLongSignal, _long => _long ? true : null);
const myShortMarks = for_every(myShortSignal, _short => _short ? true : null);
paint(myLongMarks, { name: 'Long Signal Marker', style: 'labels_below', color: '#2ecc71' });
paint(myShortMarks, { name: 'Short Signal Marker', style: 'labels_above', color: '#e74c3c' });

// ─── Signals for Scanners/Alerts/Backtester ───────────────────────────────
register_signal(for_every(myLongSignal, _long => !!_long), 'Long Entry');
register_signal(for_every(myShortSignal, _short => !!_short), 'Short Entry');