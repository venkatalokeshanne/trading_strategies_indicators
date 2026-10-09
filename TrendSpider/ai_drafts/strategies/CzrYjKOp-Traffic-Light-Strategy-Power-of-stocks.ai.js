describe_indicator('Traffic Light Strategy Power Of Stocks', 'price');

// ─── Inputs ──────────────────────────────────────────────────────────
const myRiskTab = input.tab('Settings');
const myRrRatio = myRiskTab.number('Risk to Reward Ratio', 2.0, { min: 0.1, max: 50 });
const myUseMaxSlFilter = myRiskTab.boolean('Enable Max SL Point Filter', false);
const myMaxSlPoints = myRiskTab.number('Max SL Filter (Index Points)', 100.0, { min: 0.1, max: 100000 });
const myExitRow = myRiskTab.row();
const myExitHour = myExitRow.number('Exit Hour (24hr)', 15, { min: 0, max: 23 });
const myExitMinute = myExitRow.number('Exit Minute', 20, { min: 0, max: 59 });

// Note: this is intraday day-session based logic, assumes current.resolution
// is intraday. "1" resolution gets special treatment of the 9:15 candle,
// matching the Pine `timeframe.isintraday and timeframe.multiplier == 1` check.
const myIsOneMinute = current.resolution === '1';

const myCandlesCount = close.length;

// per-candle time components
const myHours = time.map(_t => time_of(_t).hours);
const myMinutes = time.map(_t => time_of(_t).minutes);
const myDayKeys = time.map(_t => {
	const myParsed = time_of(_t);
	return `${myParsed.year}-${myParsed.dayOfYear}`;
});

// state series we will build
const myHiSeries = series_of(null);
const myLoSeries = series_of(null);
const myPairFoundSeries = series_of(false);
const myLongEntrySeries = series_of(false);
const myShortEntrySeries = series_of(false);
const myExitSeries = series_of(false);
const myStopSeries = series_of(null);
const myTargetSeries = series_of(null);
const myPositionSeries = series_of(0);

// mutable state while walking the candles
let myHi = null;
let myLo = null;
let myPairFound = false;
let myTradeCount = 0;
let myPosition = 0;
let myCurrentStop = null;
let myCurrentTarget = null;

for (let myIndex = 0; myIndex < myCandlesCount; myIndex += 1) {
	const myIsNewDay = myIndex === 0 || myDayKeys[myIndex] !== myDayKeys[myIndex - 1];

	if (myIsNewDay) {
		myPairFound = false;
		myHi = null;
		myLo = null;
		myTradeCount = 0;
	}

	const myIsGreen = close[myIndex] > open[myIndex];
	const myIsRed = close[myIndex] < open[myIndex];

	const myIsFirstCandle = myHours[myIndex] === 9 && myMinutes[myIndex] === 15;
	const myCanSearch = !(myIsOneMinute && myIsFirstCandle);

	if (!myPairFound && !myIsNewDay && myCanSearch && myIndex >= 1) {
		const myPrevCanSearch = !(myIsOneMinute && myHours[myIndex - 1] === 9 && myMinutes[myIndex - 1] === 15);
		const myIsGreenPrev = close[myIndex - 1] > open[myIndex - 1];
		const myIsRedPrev = close[myIndex - 1] < open[myIndex - 1];

		if (myPrevCanSearch && ((myIsGreen && myIsRedPrev) || (myIsRed && myIsGreenPrev))) {
			const myTempHi = Math.max(high[myIndex], high[myIndex - 1]);
			const myTempLo = Math.min(low[myIndex], low[myIndex - 1]);
			const myRangeSize = myTempHi - myTempLo;
			const myIsRangeValid = !myUseMaxSlFilter || (myRangeSize <= myMaxSlPoints);

			if (myIsRangeValid) {
				myHi = myTempHi;
				myLo = myTempLo;
				myPairFound = true;
			}
		}
	}

	// crossover / crossunder, replicating ta.crossover(close, hi) / ta.crossunder(close, lo)
	const myPrevHi = myIndex >= 1 ? myHiSeries[myIndex - 1] : null;
	const myPrevLo = myIndex >= 1 ? myLoSeries[myIndex - 1] : null;
	const myPrevClose = myIndex >= 1 ? close[myIndex - 1] : null;

	const myCrossOverHi = myHi !== null && myPrevHi !== null && close[myIndex] > myHi && myPrevClose <= myPrevHi;
	const myCrossUnderLo = myLo !== null && myPrevLo !== null && close[myIndex] < myLo && myPrevClose >= myPrevLo;

	const myLongCondition = myPairFound && myCrossOverHi && myPosition === 0 && myTradeCount < 3;
	const myShortCondition = myPairFound && myCrossUnderLo && myPosition === 0 && myTradeCount < 3;

	let myLongEntry = false;
	let myShortEntry = false;
	let myExit = false;

	if (myLongCondition) {
		myCurrentStop = myLo;
		myCurrentTarget = myHi + ((myHi - myLo) * myRrRatio);
		myTradeCount += 1;
		myPosition = 1;
		myLongEntry = true;
	}
	else if (myShortCondition) {
		myCurrentStop = myHi;
		myCurrentTarget = myLo - ((myHi - myLo) * myRrRatio);
		myTradeCount += 1;
		myPosition = -1;
		myShortEntry = true;
	}
	else if (myPosition !== 0) {
		// stop / target checks (orders placed on a prior bar, fill this bar)
		if (myPosition === 1) {
			if (low[myIndex] <= myCurrentStop) {
				myPosition = 0;
				myExit = true;
			}
			else if (high[myIndex] >= myCurrentTarget) {
				myPosition = 0;
				myExit = true;
			}
		}
		else if (myPosition === -1) {
			if (high[myIndex] >= myCurrentStop) {
				myPosition = 0;
				myExit = true;
			}
			else if (low[myIndex] <= myCurrentTarget) {
				myPosition = 0;
				myExit = true;
			}
		}

		// time based exit, overrides if still open
		const myTimeExit = myHours[myIndex] === myExitHour && myMinutes[myIndex] >= myExitMinute;
		if (myTimeExit && myPosition !== 0) {
			myPosition = 0;
			myExit = true;
		}
	}

	myHiSeries[myIndex] = myHi;
	myLoSeries[myIndex] = myLo;
	myPairFoundSeries[myIndex] = myPairFound;
	myLongEntrySeries[myIndex] = myLongEntry;
	myShortEntrySeries[myIndex] = myShortEntry;
	myExitSeries[myIndex] = myExit;
	myStopSeries[myIndex] = myPosition !== 0 ? myCurrentStop : null;
	myTargetSeries[myIndex] = myPosition !== 0 ? myCurrentTarget : null;
	myPositionSeries[myIndex] = myPosition;
}

// lines are only shown while a pair is found for the current day
const myHiLine = for_every(myPairFoundSeries, myHiSeries, (_pairFound, _hi) => _pairFound ? _hi : null);
const myLoLine = for_every(myPairFoundSeries, myLoSeries, (_pairFound, _lo) => _pairFound ? _lo : null);

paint(myHiLine, { name: 'PairHigh', color: '#26A69A', thickness: 2, style: 'ladder' });
paint(myLoLine, { name: 'PairLow', color: '#EF5350', thickness: 2, style: 'ladder' });
paint(myTargetSeries, { name: 'ActiveTarget', color: '#00E676', thickness: 2, style: 'ladder' });
paint(myStopSeries, { name: 'ActiveStop', color: '#FF5252', thickness: 2, style: 'ladder' });

// signals usable in scanners, alerts and backtests
register_signal(myLongEntrySeries, 'Long Entry');
register_signal(myShortEntrySeries, 'Short Entry');
register_signal(myExitSeries, 'Position Exit');
register_signal(myPairFoundSeries, 'Pair Found');