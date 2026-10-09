describe_indicator('BankNifty 15m Clear TP/SL Strategy', 'price');

// INPUTS
const myTab = input.tab('Settings');

const myEmaRow = myTab.row();
const myEmaFastLen = myEmaRow.number('EMA Fast Length', 20, { min: 1, max: 500 });
const myEmaSlowLen = myEmaRow.number('EMA Slow Length', 50, { min: 1, max: 500 });

const myOscRow = myTab.row();
const myRsiLen = myOscRow.number('RSI Length', 14, { min: 1, max: 200 });
const myAdxLen = myOscRow.number('ADX Length', 14, { min: 1, max: 200 });
const myAtrLen = myOscRow.number('ATR Length', 14, { min: 1, max: 200 });

const myRiskGroup = myTab.group('Risk');
const myRiskRow = myRiskGroup.row();
const myRR = myRiskRow.number('Risk Reward (TP multiple)', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myAtrMult = myRiskRow.number('SL ATR Multiplier', 1.2, { min: 0.1, max: 20, step: 0.1 });

const myNoTradeAdx = myTab.number('No Trade ADX Threshold', 12, { min: 0, max: 100 });

// INDICATORS
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;

// TIME FILTER components, precomputed per candle (minutes since midnight, exchange tz)
const myTotalMin = time.map(_t => {
	const myParsed = time_of(_t);
	return myParsed.hours * 60 + myParsed.minutes;
});

// Series we will build via a stateful loop (allowed: not calling indicator
// functions inside the loop, only plain arithmetic/state tracking)
const myLongSL = series_of(null);
const myLongTP = series_of(null);
const myShortSL = series_of(null);
const myShortTP = series_of(null);

const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const mySLExitSignal = series_of(false);
const myTPExitSignal = series_of(false);

const myBuyLabel = series_of(null);
const mySellLabel = series_of(null);
const mySLLabel = series_of(null);
const myTPLabel = series_of(null);

let myPositionSize = 0; // 0 flat, 1 long, -1 short
let myCurrentLongSL = null;
let myCurrentLongTP = null;
let myCurrentShortSL = null;
let myCurrentShortTP = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myTradeWindow = myTotalMin[myIndex] >= 570 && myTotalMin[myIndex] <= 735;
	const myNoTradeZone = myAdx[myIndex] < myNoTradeAdx;

	const myTrendBull = myEmaFast[myIndex] > myEmaSlow[myIndex] && close[myIndex] > myEmaFast[myIndex];
	const myTrendBear = myEmaFast[myIndex] < myEmaSlow[myIndex] && close[myIndex] < myEmaFast[myIndex];

	const myLongCondition = myTradeWindow && !myNoTradeZone && myTrendBull && close[myIndex] > high[myIndex - 1];
	const myShortCondition = myTradeWindow && !myNoTradeZone && myTrendBear && close[myIndex] < low[myIndex - 1];

	// carry forward previous levels by default
	myCurrentLongSL = myCurrentLongSL;
	myCurrentLongTP = myCurrentLongTP;
	myCurrentShortSL = myCurrentShortSL;
	myCurrentShortTP = myCurrentShortTP;

	// LONG ENTRY
	if (myLongCondition && myPositionSize <= 0) {
		myPositionSize = 1;
		myCurrentLongSL = close[myIndex] - myAtr[myIndex] * myAtrMult;
		myCurrentLongTP = close[myIndex] + (myAtr[myIndex] * myAtrMult * myRR);
		myBuySignal[myIndex] = true;
		myBuyLabel[myIndex] = low[myIndex];
	}

	// SHORT ENTRY
	if (myShortCondition && myPositionSize >= 0) {
		myPositionSize = -1;
		myCurrentShortSL = close[myIndex] + myAtr[myIndex] * myAtrMult;
		myCurrentShortTP = close[myIndex] - (myAtr[myIndex] * myAtrMult * myRR);
		mySellSignal[myIndex] = true;
		mySellLabel[myIndex] = high[myIndex];
	}

	// EXIT LOGIC - LONG
	if (myPositionSize > 0) {
		if (close[myIndex] <= myCurrentLongSL) {
			myPositionSize = 0;
			mySLExitSignal[myIndex] = true;
			mySLLabel[myIndex] = high[myIndex];
		}
		else if (close[myIndex] >= myCurrentLongTP) {
			myPositionSize = 0;
			myTPExitSignal[myIndex] = true;
			myTPLabel[myIndex] = high[myIndex];
		}
	}

	// EXIT LOGIC - SHORT
	if (myPositionSize < 0) {
		if (close[myIndex] >= myCurrentShortSL) {
			myPositionSize = 0;
			mySLExitSignal[myIndex] = true;
			mySLLabel[myIndex] = low[myIndex];
		}
		else if (close[myIndex] <= myCurrentShortTP) {
			myPositionSize = 0;
			myTPExitSignal[myIndex] = true;
			myTPLabel[myIndex] = low[myIndex];
		}
	}

	// PLOT TP/SL LINES, only while the corresponding position is open
	myLongSL[myIndex] = myPositionSize > 0 ? myCurrentLongSL : null;
	myLongTP[myIndex] = myPositionSize > 0 ? myCurrentLongTP : null;
	myShortSL[myIndex] = myPositionSize < 0 ? myCurrentShortSL : null;
	myShortTP[myIndex] = myPositionSize < 0 ? myCurrentShortTP : null;
}

// EMAs
paint(myEmaFast, { name: 'EMA Fast', color: '#26A69A', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#EF5350', thickness: 2 });

// TP/SL lines (ladder style, mimics Pine's plot.style_linebr - breaks when null)
paint(myLongSL, { name: 'Long SL', color: '#EF5350', style: 'ladder' });
paint(myLongTP, { name: 'Long TP', color: '#26A69A', style: 'ladder' });
paint(myShortSL, { name: 'Short SL', color: '#EF5350', style: 'ladder' });
paint(myShortTP, { name: 'Short TP', color: '#26A69A', style: 'ladder' });

// Entry/Exit markers
paint(myBuyLabel, { name: 'Buy Marker', style: 'labels_below', color: 'green' });
paint(mySellLabel, { name: 'Sell Marker', style: 'labels_above', color: 'red' });
paint(mySLLabel, { name: 'SL Marker', style: 'labels_above', color: 'red' });
paint(myTPLabel, { name: 'TP Marker', style: 'labels_above', color: 'green' });

// Signals for scanners, alerts and strategy tester
register_signal(myBuySignal, 'Long Entry');
register_signal(mySellSignal, 'Short Entry');
register_signal(mySLExitSignal, 'Stop Loss Exit');
register_signal(myTPExitSignal, 'Take Profit Exit');