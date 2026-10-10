describe_indicator('Inside Day Breakout Antigravity', 'price');

//	IMPORTANT ASSUMPTIONS / LIMITATIONS (see also the flagged notes below):
//	TrendSpider Custom JS API is an indicator engine, not an order-management
//	/ broker-strategy engine. There is no concept of strategy.equity,
//	strategy.position_size, pyramiding, qty sizing, strategy.exit/entry,
//	or opentrades.entry_price in this environment. This script reproduces
//	the core TECHNICAL logic of the Pine strategy (Inside Day detection,
//	breakout levels, ATR, session/EOD detection) and exposes it as
//	paint()ed levels plus register_signal() outputs so it can be used in
//	Scanners / Alerts / Strategy Tester (via Visual Scripts), but it can
//	not place real orders, size positions, or track equity/win-rate like
//	the original Pine strategy did.

const myTradeDir = input.select('Trade Direction', 'Both', ['Both', 'Long Only', 'Short Only']);
const myUseTakeProfit = input.boolean('Use Fixed Take Profit', false);
const myTakeProfitMultiplier = input.number('Take Profit (x Daily ATR)', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myAtrLength = input.number('Daily ATR Length', 14, { min: 1, max: 100 });
const myUseEod = input.boolean('Close Position at EOD (16:55 NY Time)', true);

// Fetch Daily data to compute d_high1, d_low1, d_high2, d_low2 and Daily ATR.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching Daily data: ' + myDailyData.error);

const myDailyAtr = atr(myDailyData.high, myDailyData.low, myDailyData.close, myAtrLength);

// Shift daily series by 1 and 2 bars (equivalent of high[1], high[2] etc in Pine).
const myDailyHigh1 = shift(myDailyData.high, 1);
const myDailyLow1 = shift(myDailyData.low, 1);
const myDailyHigh2 = shift(myDailyData.high, 2);
const myDailyLow2 = shift(myDailyData.low, 2);
const myDailyAtr1 = shift(myDailyAtr, 1);

// Land the daily values onto the current chart's time series ("ge" picks the
// first daily candle timestamp greater or equal to the current candle, which
// approximates the Pine's lookahead_on behavior for the current forming day).
const myHigh1Landed = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyHigh1, time, 'ge'),
	'constant'
);
const myLow1Landed = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyLow1, time, 'ge'),
	'constant'
);
const myHigh2Landed = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyHigh2, time, 'ge'),
	'constant'
);
const myLow2Landed = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyLow2, time, 'ge'),
	'constant'
);
const myAtrLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyAtr1, time, 'ge'),
	'constant'
);

// Inside Day condition: today's prior day range is contained inside the day before.
const myIsInsideDay = for_every(
	myHigh1Landed, myLow1Landed, myHigh2Landed, myLow2Landed,
	(_h1, _l1, _h2, _l2) => (_h1 < _h2) && (_l1 > _l2)
);

// Session approximation: Pine uses "1800-1655" America/New_York (an overnight
// session). We approximate "in_session" as "NOT within the last 5 minutes
// before 16:55 NY close", using time_of() on each candle's timestamp. This is
// an approximation since exact exchange-session crossing midnight handling
// in a custom timezone is not directly exposed by the API the same way Pine's
// time() function works.
const myInSession = for_every(time, _t => {
	const myTimeInfo = time_of(_t);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myEodMinutes = 16 * 60 + 55;
	return myMinutesOfDay !== myEodMinutes;
});

// Breakout trigger levels (only valid on Inside Day bars), mirroring the Pine plots.
const myLongLevel = for_every(myIsInsideDay, myHigh1Landed, (_inside, _h1) =>
	(_inside && (myTradeDir === 'Both' || myTradeDir === 'Long Only')) ? _h1 : null
);
const myShortLevel = for_every(myIsInsideDay, myLow1Landed, (_inside, _l1) =>
	(_inside && (myTradeDir === 'Both' || myTradeDir === 'Short Only')) ? _l1 : null
);

paint(myLongLevel, { name: 'LongBreakoutLevel', color: '#26A69A', thickness: 2, style: 'line' });
paint(myShortLevel, { name: 'ShortBreakoutLevel', color: '#EF5350', thickness: 2, style: 'line' });

// Optional take profit reference lines (price-axis), approximated using the
// current close as a stand-in for an actual open trade entry price, since
// there is no persistent order/trade state in this API.
const myLongTakeProfit = for_every(myIsInsideDay, close, myAtrLanded, (_inside, _c, _atr) =>
	(myUseTakeProfit && _inside && (myTradeDir === 'Both' || myTradeDir === 'Long Only')) ? (_c + _atr * myTakeProfitMultiplier) : null
);
const myShortTakeProfit = for_every(myIsInsideDay, close, myAtrLanded, (_inside, _c, _atr) =>
	(myUseTakeProfit && _inside && (myTradeDir === 'Both' || myTradeDir === 'Short Only')) ? (_c - _atr * myTakeProfitMultiplier) : null
);

paint(myLongTakeProfit, { name: 'LongTakeProfitRef', color: '#80CBC4', thickness: 1, style: 'dotted' });
paint(myShortTakeProfit, { name: 'ShortTakeProfitRef', color: '#EF9A9A', thickness: 1, style: 'dotted' });

// Scanning / Alert / Strategy Tester signals.
const myInsideDaySignal = myIsInsideDay;
register_signal(myInsideDaySignal, 'Inside Day');

const myLongBreakoutSignal = for_every(myIsInsideDay, myInSession, high, myHigh1Landed, (_inside, _sess, _h, _h1) =>
	_inside && _sess && (myTradeDir === 'Both' || myTradeDir === 'Long Only') && _h >= _h1
);
register_signal(myLongBreakoutSignal, 'Long Breakout Trigger');

// Removed the broken malformed for_every() call that passed a non-series
// callback as an argument (that caused the "All arguments except of the
// last one must be time series" error). The actual Short Breakout Trigger
// signal below is the correct, equivalent computation.
const myShortBreakoutSignal = for_every(myIsInsideDay, myInSession, low, myLow1Landed, (_inside, _sess, _l, _l1) =>
	_inside && _sess && (myTradeDir === 'Both' || myTradeDir === 'Short Only') && _l <= _l1
);
register_signal(myShortBreakoutSignal, 'Short Breakout Trigger');

const myEodCloseSignal = for_every(myInSession, _sess => myUseEod && !_sess);
register_signal(myEodCloseSignal, 'EOD Close Trigger');