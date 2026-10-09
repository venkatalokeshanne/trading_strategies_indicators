// EXPERIMENTAL CONVERSION NOTE:
// Pine's strategy.equity, strategy.entry/exit and order fills do not exist
// in the Custom JS API (no simulated broker, no live PnL off actual fills).
// This indicator reproduces the STRUCTURE/EDGE logic (pivots, sweeps, trend,
// session) and the "max 3 trades/day" counter exactly as in Pine, but the
// "dailyPnL > -300" equity-based risk gate can only be approximated: it is
// treated as always true because real position PnL from TP/SL fills is not
// computable here. Treat canTrade as "trade count < 3 for the day" only.
describe_indicator('MNQ Prop Firm Execution System', 'price');

const myPivotLen = input.number('Pivot Length', 3, { min: 1, max: 50 });
const myEmaLength = input.number('EMA Length', 200, { min: 1, max: 500 });
const myMaxTrades = input.number('Max Trades Per Day', 3, { min: 1, max: 50 });
const mySessionStartHour = input.number('Session Start Hour', 13, { min: 0, max: 23 });
const mySessionEndHour = input.number('Session End Hour', 16, { min: 0, max: 23 });

// Pivot points (sparse series: null where no pivot)
const myPivotHigh = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLow = pivot_low(low, myPivotLen, myPivotLen);

// EMA trend filter
const myEma = ema(close, myEmaLength);

const myCandleCount = close.length;

// Forward-filled swing high/low (var float behavior in Pine)
const mySwingHigh = series_of(null);
const mySwingLow = series_of(null);

// Sweep flags
const mySweepLow = series_of(false);
const mySweepHigh = series_of(false);

// Trend flags
const myTrendUp = series_of(false);
const myTrendDown = series_of(false);

// Session flag (approximated using exchange local time via time_of)
const mySession = series_of(false);

// Daily trade counter / signals
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

let myPrevSwingHigh = null;
let myPrevSwingLow = null;
let myCurrentDaySession = null;
let myTradesToday = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		myPrevSwingHigh = myPivotHigh[myIndex];
	}
	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		myPrevSwingLow = myPivotLow[myIndex];
	}

	mySwingHigh[myIndex] = myPrevSwingHigh;
	mySwingLow[myIndex] = myPrevSwingLow;

	mySweepLow[myIndex] = (myPrevSwingLow !== null) && (low[myIndex] < myPrevSwingLow) && (close[myIndex] > myPrevSwingLow);
	mySweepHigh[myIndex] = (myPrevSwingHigh !== null) && (high[myIndex] > myPrevSwingHigh) && (close[myIndex] < myPrevSwingHigh);

	myTrendUp[myIndex] = close[myIndex] > myEma[myIndex];
	myTrendDown[myIndex] = close[myIndex] < myEma[myIndex];

	const myTimeInfo = time_of(time[myIndex]);
	const myHourFraction = myTimeInfo.hours + (myTimeInfo.minutes / 60);
	mySession[myIndex] = (myHourFraction >= mySessionStartHour) && (myHourFraction < mySessionEndHour);

	// Daily reset of trade counter (approximation of ta.change(time("D")))
	const myBarInfo = bar_at(time[myIndex]);
	if (myCurrentDaySession !== myBarInfo.session) {
		myCurrentDaySession = myBarInfo.session;
		myTradesToday = 0;
	}

	const myCanTrade = myTradesToday < myMaxTrades;

	const myLong = mySession[myIndex] && myCanTrade && mySweepLow[myIndex] && myTrendUp[myIndex];
	const myShort = mySession[myIndex] && myCanTrade && mySweepHigh[myIndex] && myTrendDown[myIndex];

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;

	if (myLong || myShort) {
		myTradesToday += 1;
	}
}

paint(mySwingHigh, { name: 'SwingHigh', color: '#ef5350', style: 'ladder' });
paint(mySwingLow, { name: 'SwingLow', color: '#26a69a', style: 'ladder' });
paint(myEma, { name: 'EMA200', color: '#ff9800' });

register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');