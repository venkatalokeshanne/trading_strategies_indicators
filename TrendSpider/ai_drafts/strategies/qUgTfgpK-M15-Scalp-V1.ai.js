describe_indicator('M15 Scalp V1 (signals)', 'price');

/*
	NOTE: TrendSpider Custom JS indicators cannot place real orders,
	track open position size, or simulate a broker-side trailing
	stop / stop-loss exit engine (strategy.entry/strategy.exit have
	no equivalent here). This script reproduces the SIGNAL logic
	(Supertrend flip + RSI + volume filter + session + daily trade
	cap) as closely as possible and exposes it via register_signal()
	so it can be used in Scanners/Alerts/Backtester. The exit logic
	(trailing profit/stop loss/trail offset) and the position-size
	math (based on strategy.equity) are NOT reproduced here, since
	there is no broker/position state available in this API.
*/

const tab1 = input.tab('Indicator');
const myMultiplier = input.number('Multiplier', 0.7, { min: 0.1, max: 10, step: 0.1 });
const myPeriod = input.number('Period', 10, { min: 1, max: 100 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myVolMaLength = input.number('Volume MA Length', 20, { min: 1, max: 200 });

const tab2 = input.tab('Trade Filters');
const myMaxTradesDaily = tab2.number('Max trades daily', 1, { min: 1, max: 50 });
const myLookbackDays = tab2.number('Backtest lookback days', 60, { min: 1, max: 3650 });
const myRsiLongMax = tab2.number('RSI Long Max', 60, { min: 1, max: 100 });
const myRsiShortMin = tab2.number('RSI Short Min', 40, { min: 1, max: 100 });

const tab3 = input.tab('Session');
const mySessionStartHour = tab3.number('Session start hour', 5, { min: 0, max: 23 });
const mySessionStartMinute = tab3.number('Session start minute', 30, { min: 0, max: 59 });
const mySessionEndHour = tab3.number('Session end hour', 16, { min: 0, max: 23 });
const mySessionEndMinute = tab3.number('Session end minute', 30, { min: 0, max: 59 });

// Supertrend line (built-in function only returns the trend line itself)
const mySupertrendLine = supertrend(myPeriod, myMultiplier, false);

// Direction: -1 means bullish (close above the line), 1 means bearish,
// mirroring Pine's st_dir convention (-1 up, 1 down)
const myDirection = for_every(close, mySupertrendLine, (_c, _l) => (_c > _l ? -1 : 1));
const myPrevDirection = shift(myDirection, 1);
const myDirectionChanged = for_every(myDirection, myPrevDirection, (_d, _pd) => _d - _pd);

const myRsi = rsi(close, myRsiLength);
const myVolMa = sma(volume, myVolMaLength);
const myCheckVol = for_every(volume, myVolMa, (_v, _vma) => _v > _vma);

// Session check (approximated using exchange time zone minutes-of-day)
const myTimeInfo = time.map(_t => time_of(_t));
const mySessionStartMinutes = mySessionStartHour * 60 + mySessionStartMinute;
const mySessionEndMinutes = mySessionEndHour * 60 + mySessionEndMinute;
const myTimeOk = myTimeInfo.map(_ti => {
	const myMinutesOfDay = _ti.hours * 60 + _ti.minutes;
	return myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay <= mySessionEndMinutes;
});

// Lookback window (start date)
const myStartTimestamp = current.now - (myLookbackDays * 86400);

// Daily trade counter, reset on new day
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
let myTodayCount = 0;
let myLastDayOfYear = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myDayInfo = time_of(time[myIndex]);
	const myDayKey = `${myDayInfo.year}-${myDayInfo.dayOfYear}`;

	if (myDayKey !== myLastDayOfYear) {
		myTodayCount = 0;
		myLastDayOfYear = myDayKey;
	}

	const myCanTrade = (
		time[myIndex] >= myStartTimestamp &&
		myTimeOk[myIndex] &&
		myCheckVol[myIndex] &&
		myTodayCount < myMaxTradesDaily
	);

	const myIsLongFlip = myDirectionChanged[myIndex] < 0;
	const myIsShortFlip = myDirectionChanged[myIndex] > 0;

	if (myCanTrade && myIsLongFlip && myRsi[myIndex] < myRsiLongMax) {
		myLongSignal[myIndex] = true;
		myTodayCount += 1;
	}
	else if (myCanTrade && myIsShortFlip && myRsi[myIndex] > myRsiShortMin) {
		myShortSignal[myIndex] = true;
		myTodayCount += 1;
	}
}

const myLineColor = for_every(myDirection, _d => (_d < 0 ? 'green' : 'red'));
paint(mySupertrendLine, { name: 'Supertrend', color: myLineColor, thickness: 2 });

const myBuyMarks = for_every(myLongSignal, low, (_s, _l) => (_s ? _l : null));
const mySellMarks = for_every(myShortSignal, high, (_s, _h) => (_s ? _h : null));

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green', thickness: 3 });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red', thickness: 3 });

register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');