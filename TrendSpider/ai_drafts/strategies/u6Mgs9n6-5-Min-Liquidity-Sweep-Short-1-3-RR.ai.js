describe_indicator('5 Min Liquidity Sweep Short 1 to 3 RR', 'price');

// NOTE: this indicator reproduces the Pine strategy's ENTRY logic exactly
// (dayHigh tracking, sweep conditions). The STOP/TARGET tracking is
// approximated with a simple state machine (not a real backtest engine),
// since TrendSpider Custom JS indicators cannot execute broker-style
// position management. Use the "Strategy Tester" / Scanner with the
// registered signal below for actual backtesting.

const myRRMultiplier = input.number('Risk Reward Multiplier', 1, { min: 0.1, max: 10 });

const myIsFiveMin = current.resolution == '5';

const myDayHigh = series_of(null);
const myShortSL = series_of(null);
const myShortTP = series_of(null);
const myShortCondition = series_of(false);

let myInTrade = false;
let myActiveSL = null;
let myActiveTP = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIndex == 0) {
		myDayHigh[myIndex] = high[myIndex];
		continue;
	}

	const mySessionCurr = bar_at(time[myIndex]).session;
	const mySessionPrev = bar_at(time[myIndex - 1]).session;
	const myNewDay = mySessionCurr != mySessionPrev;

	myDayHigh[myIndex] = myNewDay ? high[myIndex] : Math.max(myDayHigh[myIndex - 1], high[myIndex]);

	const myPrevBullish = close[myIndex - 1] > open[myIndex - 1];
	const myPrevHighAtDayHigh = high[myIndex - 1] >= myDayHigh[myIndex - 1];
	const myLatestCloseBelowPrevOpen = close[myIndex] < open[myIndex - 1];
	const myLatestHighCrossAbovePrevHigh = high[myIndex] > high[myIndex - 1];

	const myShortConditionValue = myIsFiveMin && myPrevBullish && myPrevHighAtDayHigh && myLatestCloseBelowPrevOpen && myLatestHighCrossAbovePrevHigh;
	myShortCondition[myIndex] = myShortConditionValue;

	if (myShortConditionValue && !myInTrade) {
		const mySLCandidate = high[myIndex];
		const myEntryPrice = close[myIndex];
		const myRisk = mySLCandidate - myEntryPrice;

		if (myRisk > 0) {
			myActiveSL = mySLCandidate;
			myActiveTP = myEntryPrice - myRisk * myRRMultiplier;
			myInTrade = true;
		}
	}

	if (myInTrade) {
		myShortSL[myIndex] = myActiveSL;
		myShortTP[myIndex] = myActiveTP;

		// approximate exit check: stop or target hit intrabar
		if (high[myIndex] >= myActiveSL || low[myIndex] <= myActiveTP) {
			myInTrade = false;
			myActiveSL = null;
			myActiveTP = null;
		}
	}
	else {
		myShortSL[myIndex] = null;
		myShortTP[myIndex] = null;
	}
}

const myShortSignalMarks = for_every(myShortCondition, _cond => _cond ? constants.icons.triangle_down : null);

paint(myDayHigh, { name: 'Day High', color: '#FF9800', thickness: 2 });
paint(myShortSL, { name: 'Short SL', color: '#EF5350', thickness: 1, style: 'line' });
paint(myShortTP, { name: 'Short TP', color: '#26A69A', thickness: 1, style: 'line' });
// renamed the painted marker series to avoid a name clash with the
// register_signal() output below (both can't share the same name)
paint(myShortSignalMarks, { name: 'Short Signal Marker', style: 'labels_above', color: 'red' });

register_signal(myShortCondition, 'Short Signal');