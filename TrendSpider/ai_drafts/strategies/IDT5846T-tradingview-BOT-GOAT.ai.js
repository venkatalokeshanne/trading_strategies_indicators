describe_indicator('BOT GOAT EMA Cross Signals', 'price');

// NOTE: This is a signal/indicator conversion of the Pine Script strategy.
// TrendSpider's Custom JS API does not provide a backtesting/strategy engine
// (no position sizing, stop-loss, take-profit, trailing-stop or order
// management primitives). Only the entry logic (EMA cross + day/timeframe
// filters), the EMA plots, the entry arrows and scanner/alert signals can be
// reproduced exactly. The $ -> ticks risk management (SL $1, TP1 $1, TP2 $3,
// trailing) cannot be expressed here; use TrendSpider Strategy Tester with
// equivalent manual exit rules if you need backtesting of those exits.

const myTrendTab = input.tab('Trend');
const myEmaFastLen = myTrendTab.number('Fast EMA', 21, { min: 1, max: 500 });
const myEmaSlowLen = myTrendTab.number('Slow EMA', 55, { min: 1, max: 500 });

const myFiltersTab = input.tab('Filters');
const myOnly15m = myFiltersTab.boolean('Only trade on the 15-minute chart', true);
const myTradeWeekdaysOnly = myFiltersTab.boolean('Trade weekdays only (Mon-Fri)', true);

const myDisplayTab = input.tab('Display');
const myShowArrows = myDisplayTab.boolean('Show entry arrows', true);

// ---------------- CALCULATIONS ----------------
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);

// Crossover / Crossunder, computed manually since there is no built-in
// crossover() function in the Custom JS API.
const myEmaCrossUp = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index < 1) return false;
	return myEmaFast[_index] > myEmaSlow[_index] && myEmaFast[_index - 1] <= myEmaSlow[_index - 1];
});

const myEmaCrossDown = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index < 1) return false;
	return myEmaFast[_index] < myEmaSlow[_index] && myEmaFast[_index - 1] >= myEmaSlow[_index - 1];
});

// Weekday filter, using the exchange time zone for the current ticker.
const myIsWeekday = time.map(_t => {
	const myDow = time_of(_t).dayOfWeek; // 1 Mon ... 7 Sun
	return myDow >= 1 && myDow <= 5;
});

// Timeframe filter: Pine's timeframe.period == "15" maps to current.resolution == "15"
const myTfOk = !myOnly15m || current.resolution == '15';

const myTradeOk = myIsWeekday.map(_wd => myTfOk && (!myTradeWeekdaysOnly || _wd));

// ---------------- SIGNALS ----------------
const myLongSignal = for_every(myEmaCrossUp, myTradeOk, (_up, _ok) => Boolean(_up && _ok));
const myShortSignal = for_every(myEmaCrossDown, myTradeOk, (_down, _ok) => Boolean(_down && _ok));

// ---------------- PLOTS ----------------
paint(myEmaFast, { name: 'FastEMA', color: '#00BCD4', thickness: 2 });
paint(myEmaSlow, { name: 'SlowEMA', color: '#FF9800', thickness: 2 });

const myLongArrowSeries = for_every(myLongSignal, _l => (myShowArrows && _l) ? constants.icons.triangle_up : null);
const myShortArrowSeries = for_every(myShortSignal, _s => (myShowArrows && _s) ? constants.icons.triangle_down : null);

paint(myLongArrowSeries, { name: 'LongArrow', style: 'labels_below', color: '#00E676' });
paint(myShortArrowSeries, { name: 'ShortArrow', style: 'labels_above', color: '#E040FB' });

// ---------------- SIGNALS FOR SCANNER/ALERTS/STRATEGY ----------------
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');