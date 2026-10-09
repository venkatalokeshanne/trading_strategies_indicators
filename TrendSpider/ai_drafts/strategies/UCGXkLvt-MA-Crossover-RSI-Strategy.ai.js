describe_indicator('MA Crossover Plus RSI Strategy Signals', 'price');

// NOTE: TrendSpider Custom JS indicators cannot place real orders,
// manage equity, commissions, or position sizing like a Pine
// strategy() script. This indicator reproduces the signal logic
// (EMA crossovers filtered by RSI) and plots an approximate
// Stop Loss / Take Profit level while a simulated position is
// open, computed bar by bar in the same way Pine would track it.

const myTab = input.tab('Strategy Settings');

const myMaRow = myTab.row();
const myFastLen = myMaRow.number('Fast MA Length', 9, { min: 1, max: 500 });
const mySlowLen = myMaRow.number('Slow MA Length', 21, { min: 1, max: 500 });

const myRsiGroup = myTab.group('RSI Filter');
const myRsiLen = myRsiGroup.number('RSI Length', 14, { min: 1, max: 500 });
const myRsiRow = myRsiGroup.row();
const myRsiOB = myRsiRow.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOS = myRsiRow.number('RSI Oversold', 30, { min: 1, max: 99 });

const mySlGroup = myTab.group('Stop Loss / Take Profit');
const myUseSL = mySlGroup.boolean('Use Stop Loss', true);
const mySlPerc = mySlGroup.number('Stop Loss %', 2, { min: 0.01, max: 100 });
const myUseTP = mySlGroup.boolean('Use Take Profit', true);
const myTpPerc = mySlGroup.number('Take Profit %', 4, { min: 0.01, max: 100 });

const myFastMA = ema(close, myFastLen);
const mySlowMA = ema(close, mySlowLen);
const myRsiVal = rsi(close, myRsiLen);

// Crossover / crossunder, equivalent to ta.crossover / ta.crossunder
const myBullCross = for_every(myFastMA, mySlowMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myFastMA[_i - 1] <= mySlowMA[_i - 1] && _fast > _slow;
});

const myBearCross = for_every(myFastMA, mySlowMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myFastMA[_i - 1] >= mySlowMA[_i - 1] && _fast < _slow;
});

const myBuySignal = for_every(myBullCross, myRsiVal, (_bull, _rsi) => _bull && _rsi < myRsiOB);
const mySellSignal = for_every(myBearCross, myRsiVal, (_bear, _rsi) => _bear && _rsi > myRsiOS);

// Simulate a single-position state machine (long only), the same
// way the Pine strategy would behave: enter on buySignal, exit on
// sellSignal or when SL/TP level is touched intrabar (approximated
// using high/low of the bar).
const myEntryPriceSeries = series_of(null);
const mySlLevelSeries = series_of(null);
const myTpLevelSeries = series_of(null);

let myInPosition = false;
let myEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (!myInPosition && myBuySignal[myIndex]) {
		myInPosition = true;
		myEntryPrice = close[myIndex];
	}
	else if (myInPosition) {
		const mySlPrice = myUseSL ? myEntryPrice * (1 - mySlPerc / 100) : null;
		const myTpPrice = myUseTP ? myEntryPrice * (1 + myTpPerc / 100) : null;

		const myHitSL = mySlPrice !== null && low[myIndex] <= mySlPrice;
		const myHitTP = myTpPrice !== null && high[myIndex] >= myTpPrice;

		if (mySellSignal[myIndex] || myHitSL || myHitTP) {
			myInPosition = false;
			myEntryPrice = null;
		}
	}

	if (myInPosition) {
		myEntryPriceSeries[myIndex] = myEntryPrice;
		mySlLevelSeries[myIndex] = myUseSL ? myEntryPrice * (1 - mySlPerc / 100) : null;
		myTpLevelSeries[myIndex] = myUseTP ? myEntryPrice * (1 + myTpPerc / 100) : null;
	}
}

paint(myFastMA, { name: 'FastMA', color: '#2962FF', thickness: 2 });
paint(mySlowMA, { name: 'SlowMA', color: '#FF9800', thickness: 2 });

paint(mySlLevelSeries, { name: 'StopLoss', style: 'ladder', color: '#EF5350', thickness: 1 });
paint(myTpLevelSeries, { name: 'TakeProfit', style: 'ladder', color: '#26A69A', thickness: 1 });

const myBuyMarks = for_every(myBuySignal, low, (_buy, _low) => _buy ? _low : null);
const mySellMarks = for_every(mySellSignal, high, (_sell, _high) => _sell ? _high : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350', thickness: 3 });

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');