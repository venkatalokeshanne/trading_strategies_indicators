describe_indicator('M15 Scalp V1 (SuperTrend plus RSI)', 'price');

// -----------------------------------------------------------------------
// NOTE: TrendSpider Custom JS has no strategy/backtest engine, no access
// to strategy.equity, and no built-in trailing-stop exit mechanism like
// Pine's strategy.exit(). This script reproduces only the ENTRY LOGIC
// (SuperTrend flip + RSI filter + volume filter + session filter + daily
// trade limit) as signals/labels. Position sizing (2% risk math) and the
// trailing stop/loss exit logic from the original strategy can not be
// expressed here and are therefore omitted.
// Also, the built-in supertrend() function only returns the SuperTrend
// line, not a separate "direction" series like Pine's ta.supertrend().
// Direction is approximated here as: bullish when close is above the
// SuperTrend line, bearish when close is below it. This should behave
// the same way as Pine's st_dir in the vast majority of cases, but is an
// approximation since we don't have access to the native direction flag.
// -----------------------------------------------------------------------

const myTab = input.tab('Settings');

const myMultiplier = myTab.number('Multiplier', 0.7, { min: 0.1, max: 10, step: 0.1 });
const myPeriod = myTab.number('Period', 10, { min: 1, max: 100 });
const myRsiLength = myTab.number('RSI Length', 14, { min: 1, max: 100 });
const myVolMaLength = myTab.number('Volume MA Length', 20, { min: 1, max: 200 });
const myMaxTradesDaily = myTab.number('Max Trades Daily', 1, { min: 1, max: 20 });

const mySessionRow = myTab.row();
const mySessionStart = mySessionRow.text('Session Start (HHMM)', '0530');
const mySessionEnd = mySessionRow.text('Session End (HHMM)', '1630');

const myRsiRow = myTab.row();
const myRsiLongMax = myRsiRow.number('RSI Max for Long', 60, { min: 1, max: 100 });
const myRsiShortMin = myRsiRow.number('RSI Min for Short', 40, { min: 1, max: 100 });

// -----------------------------------------------------------------------
// Indicators
// -----------------------------------------------------------------------
const mySuperTrendLine = supertrend(myPeriod, myMultiplier, false);
const myRsi = rsi(close, myRsiLength);
const myVolMa = sma(volume, myVolMaLength);

// direction: -1 means bullish (close above line), 1 means bearish (close below line)
const myDirection = for_every(close, mySuperTrendLine, (_c, _l) => (_c > _l ? -1 : 1));

// parse session boundaries, format HHMM as plain numbers
function myParseHHMM(_text) {
	const myNum = parseInt(_text, 10);
	assert(!isNaN(myNum), `Invalid session time: "${_text}"`);
	return myNum;
}

const mySessionStartNum = myParseHHMM(mySessionStart);
const mySessionEndNum = myParseHHMM(mySessionEnd);

// -----------------------------------------------------------------------
// Main loop: daily trade counting, direction change detection, filters
// -----------------------------------------------------------------------
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myBuyLabelSeries = series_of(null);
const mySellLabelSeries = series_of(null);

let myTodayCount = 0;
let myLastDay = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;

	if (myDayKey !== myLastDay) {
		myTodayCount = 0;
		myLastDay = myDayKey;
	}

	const myHHMM = myTimeInfo.hours * 100 + myTimeInfo.minutes;
	const myTimeOk = mySessionStartNum <= mySessionEndNum
		? (myHHMM >= mySessionStartNum && myHHMM <= mySessionEndNum)
		: (myHHMM >= mySessionStartNum || myHHMM <= mySessionEndNum);

	const myCheckVol = volume[myIndex] > myVolMa[myIndex];
	const myCanTrade = myTimeOk && myCheckVol && myTodayCount < myMaxTradesDaily;

	const myDirChanged = myIndex > 0 ? (myDirection[myIndex] !== myDirection[myIndex - 1]) : false;
	const myDirWentBullish = myDirChanged && myDirection[myIndex] === -1;
	const myDirWentBearish = myDirChanged && myDirection[myIndex] === 1;

	if (myCanTrade && myDirWentBullish && myRsi[myIndex] < myRsiLongMax) {
		myBuySignal[myIndex] = true;
		myBuyLabelSeries[myIndex] = constants.icons.triangle_up;
		myTodayCount += 1;
	}
	else if (myCanTrade && myDirWentBearish && myRsi[myIndex] > myRsiShortMin) {
		mySellSignal[myIndex] = true;
		mySellLabelSeries[myIndex] = constants.icons.triangle_down;
		myTodayCount += 1;
	}
}

// -----------------------------------------------------------------------
// Painting
// -----------------------------------------------------------------------
const myDirColor = for_every(myDirection, _d => (_d === -1 ? '#26A69A' : '#EF5350'));
paint(mySuperTrendLine, { name: 'SuperTrend', color: myDirColor, thickness: 2 });

paint(myBuyLabelSeries, { style: 'labels_below', color: 'green', name: 'Buy Signal' });
paint(mySellLabelSeries, { style: 'labels_above', color: 'red', name: 'Sell Signal' });

register_signal(myBuySignal, 'Long Entry');
register_signal(mySellSignal, 'Short Entry');