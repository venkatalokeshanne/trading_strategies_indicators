describe_indicator('All Day Futures Trend Pullback (EMA RSI)', 'price');

// NOTE: this is a signal/visual translation of the Pine Script strategy.
// The Custom JS API has no strategy/backtest engine (no strategy.entry,
// strategy.exit, position tracking, stop/limit/trailing orders). Those
// parts of the Pine script cannot be reproduced here. This indicator
// reproduces the EMA/RSI trend-pullback signal logic exactly, and
// exposes Long/Short conditions as register_signal() outputs so they
// can be used in Scanners, Alerts and the Strategy Tester module
// (which handles the actual trade simulation on TrendSpider side).

const myTab = input.tab('Indicator Settings');
const myEmaLen = myTab.number('EMA Length', 100, { min: 1, max: 1000 });
const myRsiLen = myTab.number('RSI Length', 14, { min: 1, max: 200 });

const myRsiRow = myTab.row();
const myRsiLongMax = myRsiRow.number('Long RSI Max (pullback)', 45, { min: 0, max: 100, step: 0.5 });
const myRsiShortMin = myRsiRow.number('Short RSI Min (pullback)', 55, { min: 0, max: 100, step: 0.5 });

const mySessionTab = input.tab('Session Filter');
const myUseSession = mySessionTab.boolean('Use Session Filter?', false);
const mySessionStart = mySessionTab.text('Session Start (HHMM)', '0000');
const mySessionEnd = mySessionTab.text('Session End (HHMM)', '2359');

// Core indicators
const myEma = ema(close, myEmaLen);
const myRsi = rsi(close, myRsiLen);

// Session filter: parses "HHMM" strings and checks each candle's exchange time.
// This is an approximation of Pine's time(timeframe.period, sessionStr): it
// does not support multi-range sessions or day-of-week filters, only a single
// HHMM-HHMM intraday window, since the Custom JS API has no session() parser.
function myParseHHMM(_text) {
	const myNum = parseInt(_text, 10) || 0;
	return { hours: Math.floor(myNum / 100), minutes: myNum % 100 };
}

const myStart = myParseHHMM(mySessionStart);
const myEnd = myParseHHMM(mySessionEnd);

const myInSession = time.map(_t => {
	if (!myUseSession) return true;
	const myTime = time_of(_t);
	const myMinutesOfDay = myTime.hours * 60 + myTime.minutes;
	const myStartMinutes = myStart.hours * 60 + myStart.minutes;
	const myEndMinutes = myEnd.hours * 60 + myEnd.minutes;
	if (myStartMinutes <= myEndMinutes) {
		return myMinutesOfDay >= myStartMinutes && myMinutesOfDay <= myEndMinutes;
	}
	// overnight session (wraps past midnight)
	return myMinutesOfDay >= myStartMinutes || myMinutesOfDay <= myEndMinutes;
});

// Trend + pullback conditions (exact translation of Pine logic)
const myTrendUp = for_every(close, myEma, (_c, _e) => _c > _e);
const myTrendDown = for_every(close, myEma, (_c, _e) => _c < _e);

const myLongCond = for_every(myTrendUp, myRsi, (_up, _r, _prev, _i) => {
	return myInSession[_i] && _up && _r <= myRsiLongMax;
});

const myShortCond = for_every(myTrendDown, myRsi, (_down, _r, _prev, _i) => {
	return myInSession[_i] && _down && _r >= myRsiShortMin;
});

// Visuals
paint(myEma, { name: 'EMA', color: '#2962FF', thickness: 2 });

const myLongMarks = for_every(myLongCond, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCond, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#EF5350' });

// Signals for scanners, alerts and strategy backtesting
register_signal(myLongCond, 'Long Entry Condition');
register_signal(myShortCond, 'Short Entry Condition');