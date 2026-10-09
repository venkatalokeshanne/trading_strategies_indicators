describe_indicator('Three Muskateers Signals', 'price');

// Inputs organized in tabs matching the Pine script groups
const signalsTab = input.tab('Signal Settings');
const myTradeDirection = signalsTab.select('Trade Direction', 'Long', ['Long', 'Short', 'Both']);

const displayTab = input.tab('Display');
const myShowBuySellSignals = displayTab.boolean('Show Buy/Sell Tags', false);
const mySignalHoldBars = displayTab.number('Trade Signal Hold Bars', 1, { min: 1, max: 500 });

// Fixed parameters, as hardcoded in the original Pine script
const myEmaFastLen = 50;
const myEmaSlowLen = 200;
const myBbLen = 20;
const myBbMult = 2.0;

const myRsi = rsi(close, 14);
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myBasis = sma(close, myBbLen);
const myStdevVal = stdev(close, myBbLen);
const myDev = mult(myStdevVal, myBbMult);
const myUpperBB = add(myBasis, myDev);
const myLowerBB = sub(myBasis, myDev);

const myN = close.length;

// Helper series computed via for_every, no custom loops needed for indicator math
const myTrendBull = for_every(myEmaFast, myEmaSlow, (_fast, _slow) => _fast > _slow);
const myTrendBear = for_every(myEmaFast, myEmaSlow, (_fast, _slow) => _fast < _slow);

// crossover / crossunder helpers, computed with simple index-based arrays
const myMeanRevBull = series_of(false);
const myMeanRevBear = series_of(false);
const myArbBull = series_of(false);
const myArbBear = series_of(false);

for (let myIndex = 1; myIndex < myN; myIndex += 1) {
	myMeanRevBull[myIndex] = myRsi[myIndex] > 30 && myRsi[myIndex - 1] <= 30;
	myMeanRevBear[myIndex] = myRsi[myIndex] < 70 && myRsi[myIndex - 1] >= 70;
	myArbBull[myIndex] = close[myIndex] > myLowerBB[myIndex] && close[myIndex - 1] <= myLowerBB[myIndex - 1];
	myArbBear[myIndex] = close[myIndex] < myUpperBB[myIndex] && close[myIndex - 1] >= myUpperBB[myIndex - 1];
}

const myAllowLong = myTradeDirection === 'Long' || myTradeDirection === 'Both';
const myAllowShort = myTradeDirection === 'Short' || myTradeDirection === 'Both';
const myLongOnly = myTradeDirection === 'Long';
const myShortOnly = myTradeDirection === 'Short';

// Series to be populated during the position-state simulation below
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myOpenLongEvent = series_of(false);
const myOpenShortEvent = series_of(false);
const myCloseLongEvent = series_of(false);
const myCloseShortEvent = series_of(false);
const myBuyTradeEvent = series_of(false);
const mySellTradeEvent = series_of(false);
const mySignalActive = series_of(false);

// Simulating strategy.position_size requires sequential state tracking,
// which cannot be expressed via built-in series functions, so a loop
// is used here (not calling any indicator function inside it).
let myPositionSize = 0;
let myLastSignalBar = null;
let myLastSignalIsBuy = true;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myBullCount = (myTrendBull[myIndex] ? 1 : 0) + (myMeanRevBull[myIndex] ? 1 : 0) + (myArbBull[myIndex] ? 1 : 0);
	const myBearCount = (myTrendBear[myIndex] ? 1 : 0) + (myMeanRevBear[myIndex] ? 1 : 0) + (myArbBear[myIndex] ? 1 : 0);

	const myBuy = myBullCount >= 2;
	const mySell = myBearCount >= 2;

	myBuySignal[myIndex] = myBuy;
	mySellSignal[myIndex] = mySell;

	const myOpenLong = myAllowLong && myBuy && myPositionSize <= 0;
	const myOpenShort = myAllowShort && mySell && myPositionSize >= 0;
	const myCloseLong = myLongOnly && mySell && myPositionSize > 0;
	const myCloseShort = myShortOnly && myBuy && myPositionSize < 0;

	myOpenLongEvent[myIndex] = myOpenLong;
	myOpenShortEvent[myIndex] = myOpenShort;
	myCloseLongEvent[myIndex] = myCloseLong;
	myCloseShortEvent[myIndex] = myCloseShort;

	// Update simulated position state, mirroring strategy.entry/strategy.close
	if (myCloseLong) {
		myPositionSize = 0;
	}
	if (myCloseShort) {
		myPositionSize = 0;
	}
	if (myOpenLong) {
		myPositionSize = 1;
	}
	if (myOpenShort) {
		myPositionSize = -1;
	}

	const myBuyTrade = myOpenLong || myCloseShort;
	const mySellTrade = myOpenShort || myCloseLong;

	myBuyTradeEvent[myIndex] = myBuyTrade;
	mySellTradeEvent[myIndex] = mySellTrade;

	if (myBuyTrade) {
		myLastSignalBar = myIndex;
		myLastSignalIsBuy = true;
	}
	else if (mySellTrade) {
		myLastSignalBar = myIndex;
		myLastSignalIsBuy = false;
	}

	mySignalActive[myIndex] = myLastSignalBar !== null && myIndex >= myLastSignalBar && myIndex < myLastSignalBar + mySignalHoldBars;
}

// Buy/Sell shape labels (equivalent to plotshape with labelup/labeldown)
const myBuyLabelSeries = for_every(myBuySignal, _b => _b && myAllowLong ? low[close.length - close.length] : null);
const myBuyMarks = series_of(null);
const mySellMarks = series_of(null);
for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myShowBuySellSignals && myAllowLong && myBuySignal[myIndex]) {
		myBuyMarks[myIndex] = low[myIndex];
	}
	if (myShowBuySellSignals && myAllowShort && mySellSignal[myIndex]) {
		mySellMarks[myIndex] = high[myIndex];
	}
}

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// Signals available for Scanners, Alerts and Strategy Tester
register_signal(myBuyTradeEvent, 'Buy Trade Event');
register_signal(mySellTradeEvent, 'Sell Trade Event');
register_signal(myOpenLongEvent, 'Open Long');
register_signal(myOpenShortEvent, 'Open Short');
register_signal(myCloseLongEvent, 'Close Long');
register_signal(myCloseShortEvent, 'Close Short');
register_signal(myBuySignal, 'Raw Buy Signal');
register_signal(mySellSignal, 'Raw Sell Signal');
register_signal(mySignalActive, 'Signal Active');