describe_indicator('EMA RSI ATR ETH 4H Strategy', 'price');

// --- INPUT PARAMETERS ---
const myTab = input.tab('Settings');

const myEmaRow = myTab.row();
const myEmaFastLen = myEmaRow.number('EMA Fast', 21, { min: 1, max: 500 });
const myEmaSlowLen = myEmaRow.number('EMA Slow', 89, { min: 1, max: 500 });

const myRsiGroup = myTab.group('RSI');
const myRsiLen = myRsiGroup.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiRow = myRsiGroup.row();
const myRsiMin = myRsiRow.number('RSI Min', 55, { min: 0, max: 100 });
const myRsiMax = myRsiRow.number('RSI Max', 75, { min: 0, max: 100 });

const myAtrGroup = myTab.group('ATR');
const myAtrLen = myAtrGroup.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMaLen = myAtrGroup.number('ATR MA Length', 20, { min: 1, max: 200 });

const myRiskRow = myTab.row();
const mySlMultiplier = myRiskRow.number('Stop Loss ATR Mult', 2.5, { min: 0.1, max: 20 });
const myTpMultiplier = myRiskRow.number('Take Profit ATR Mult', 4.0, { min: 0.1, max: 20 });

// --- CALCULATIONS (computed once, outside loops) ---
const myEma21 = ema(close, myEmaFastLen);
const myEma89 = ema(close, myEmaSlowLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);
const myAtrAvg = sma(myAtr, myAtrMaLen);

// --- SIMULATE STRATEGY STATE (position, SL/TP) ---
// Pine's 'var' persistence is reproduced via a sequential loop over candles.
// Only one position (Long) can be open at a time, matching the original script.
const myStopLossSeries = series_of(null);
const myTakeProfitSeries = series_of(null);
const myLongEntrySignal = series_of(false);
const myExitLossSignal = series_of(false);
const myExitProfitSignal = series_of(false);

let myPositionOpen = false;
let myStopLossLevel = null;
let myTakeProfitLevel = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTrendCondition = myEma21[myIndex] > myEma89[myIndex] && close[myIndex] > myEma21[myIndex];
	const myMomentumCondition = myRsi[myIndex] >= myRsiMin && myRsi[myIndex] <= myRsiMax;
	const myVolatilityCondition = myAtr[myIndex] > myAtrAvg[myIndex];
	const myLongCondition = myTrendCondition && myMomentumCondition && myVolatilityCondition;

	// Check exits first (position opened on a previous candle)
	if (myPositionOpen) {
		if (low[myIndex] <= myStopLossLevel) {
			myExitLossSignal[myIndex] = true;
			myPositionOpen = false;
			myStopLossLevel = null;
			myTakeProfitLevel = null;
		}
		else if (high[myIndex] >= myTakeProfitLevel) {
			myExitProfitSignal[myIndex] = true;
			myPositionOpen = false;
			myStopLossLevel = null;
			myTakeProfitLevel = null;
		}
	}

	// Entry logic: only when flat
	if (!myPositionOpen && myLongCondition) {
		myStopLossLevel = close[myIndex] - (myAtr[myIndex] * mySlMultiplier);
		myTakeProfitLevel = close[myIndex] + (myAtr[myIndex] * myTpMultiplier);
		myLongEntrySignal[myIndex] = true;
		myPositionOpen = true;
	}

	myStopLossSeries[myIndex] = myPositionOpen ? myStopLossLevel : null;
	myTakeProfitSeries[myIndex] = myPositionOpen ? myTakeProfitLevel : null;
}

// --- PAINTING ---
paint(myEma21, { name: 'EMA21', color: '#2962ff', thickness: 1 });
paint(myEma89, { name: 'EMA89', color: '#ff9800', thickness: 2 });
paint(myStopLossSeries, { name: 'StopLossLevel', color: '#ef5350', style: 'line' });
paint(myTakeProfitSeries, { name: 'TakeProfitLevel', color: '#26a69a', style: 'line' });

// --- SIGNALS FOR SCANNER STRATEGY TESTER ALERTS ---
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myExitLossSignal, 'Exit Long Stop Loss');
register_signal(myExitProfitSignal, 'Exit Long Take Profit');