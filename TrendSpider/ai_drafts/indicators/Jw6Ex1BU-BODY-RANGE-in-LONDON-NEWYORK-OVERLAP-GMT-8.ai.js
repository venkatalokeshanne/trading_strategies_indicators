describe_indicator('BODY RANGE IN L-N OVERLAP', 'price');

// Bull/bear colors mapped from Pine hex defaults (#26a69a, #ef5350)
const myBullColor = 'rgb(38,166,154)';
const myBearColor = 'rgb(239,83,80)';

// candle_range = |close - open|, plotted as columns on price axis (matches Pine plot.style_columns)
const myCandleRange = for_every(close, open, (_c, _o) => _c >= _o ? (_c - _o) : (_o - _c));
paint(myCandleRange, { name: 'CandleRange', style: 'column', color: 'blue' });

// Reproduces plotcandle() coloring: bull color when close >= open, bear color otherwise
const myCandleColors = for_every(close, open, (_c, _o) => _c >= _o ? myBullColor : myBearColor);
color_candles(myCandleColors);

// Session inputs replace Pine's input.session("2000-2359") + sessionTimezone="GMT+8".
// The Custom JS API has no native session-string parser nor a custom timezone
// parameter for time_of(), so the session window and the UTC offset are both
// exposed as explicit numeric inputs instead of a single session-string input.
const mySessionTab = input.tab('Session');
const myStartRow = mySessionTab.row();
const mySessionStartHour = myStartRow.number('Start Hour', 20, { min: 0, max: 23 });
const mySessionStartMinute = myStartRow.number('Start Minute', 0, { min: 0, max: 59 });
const myEndRow = mySessionTab.row();
const mySessionEndHour = myEndRow.number('End Hour', 23, { min: 0, max: 23 });
const mySessionEndMinute = myEndRow.number('End Minute', 59, { min: 0, max: 59 });
// Shortened title to satisfy the input() name length limit (was too long before)
const myTimezoneOffsetHours = mySessionTab.number('UTC Offset (hours)', 8, { min: -12, max: 14 });

// Computes "in session" per candle using manual UTC-second arithmetic shifted by
// the fixed timezone offset (equivalent to the Pine time(...) GMT+8 check).
const myInSession = for_every(time, _t => {
	const myShiftedSeconds = (_t + myTimezoneOffsetHours * 3600) % 86400;
	const myNormalizedSeconds = myShiftedSeconds < 0 ? myShiftedSeconds + 86400 : myShiftedSeconds;
	const myHour = Math.floor(myNormalizedSeconds / 3600);
	const myMinute = Math.floor((myNormalizedSeconds % 3600) / 60);
	const myCurrentTotalMinutes = myHour * 60 + myMinute;
	const myStartTotalMinutes = mySessionStartHour * 60 + mySessionStartMinute;
	const myEndTotalMinutes = mySessionEndHour * 60 + mySessionEndMinute;
	return myCurrentTotalMinutes >= myStartTotalMinutes && myCurrentTotalMinutes <= myEndTotalMinutes;
});

// Signals for scanning/alerts/strategy use, since the Pine bgcolor() highlight
// itself can't be reproduced visually (see note below).
register_signal(myInSession, 'In Trading Session');
register_signal(for_every(close, open, (_c, _o) => _c >= _o), 'Bullish Candle');
register_signal(for_every(close, open, (_c, _o) => _c < _o), 'Bearish Candle');