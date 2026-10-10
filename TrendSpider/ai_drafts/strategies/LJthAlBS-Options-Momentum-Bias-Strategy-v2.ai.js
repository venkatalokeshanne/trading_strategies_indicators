describe_indicator('Options Momentum Bias Strategy v2', 'price');
// === Inputs, organized ===
const emaTab = input.tab('EMAs');
const myFastEmaLen = emaTab.number('Fast EMA Length', 9, { min: 1, max: 500 });
const mySlowEmaLen = emaTab.number('Slow EMA Length', 20, { min: 1, max: 500 });
const myTrendEmaLen = emaTab.number('Trend EMA Length', 50, { min: 1, max: 500 });
const volTab = input.tab('Volume & Volatility');
const myVolLen = volTab.number('Volume Avg Length', 20, { min: 1, max: 500 });
const myVolMult = volTab.number('Volume Multiplier', 1.2, { min: 0.1, max: 10, step: 0.1 });
const myAtrLen = volTab.number('ATR Length', 14, { min: 1, max: 500 });
const myStopATR = volTab.number('Stop Loss ATR Mult', 1.0, { min: 0.1, max: 10, step: 0.1 });
const myTargetATR = volTab.number('Target ATR Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });
const logicTab = input.tab('Logic');
const myPullbackLookback = logicTab.number('Pullback Lookback Bars', 3, { min: 1, max: 100 });
const myCooldownBars = logicTab.number('Signal Cooldown Bars', 5, { min: 0, max: 500 });
const myUseSession = logicTab.boolean('Use Regular Session Filter', true);
const displayTab = input.tab('Display');
const myShowBg = displayTab.boolean('Show Bias Background', true);
const myShowLabels = displayTab.boolean('Show CALL/PUT Labels', true);
const myShowVWAP = displayTab.boolean('Show VWAP', true);
const myShowEMAs = displayTab.boolean('Show EMAs', true);

// === Core calculations (computed outside any loop, as required) ===
const myVwapValue = vwap(0);
const myFastEma = ema(close, myFastEmaLen);
const mySlowEma = ema(close, mySlowEmaLen);
const myTrendEma = ema(close, myTrendEmaLen);
const myAvgVol = sma(volume, myVolLen);
const myAtr = atr(high, low, close, myAtrLen);
const myLowestLow = lowest(low, myPullbackLookback);
const myHighestHigh = highest(high, myPullbackLookback);

// Session filter: approximated using exchange session hours (9:30-16:00),
// since Pine's time(timeframe.period, sessionInput) string parsing is not
// available as-is in Custom JS API. We assume the regular session matches
// current.session boundaries.
const mySessionStartMinutes = current.session.start.hours * 60 + current.session.start.minutes;
const mySessionEndMinutes = current.session.end.hours * 60 + current.session.end.minutes;
const myCount = close.length;

// Output series
const myBullSignal = series_of(false);
const myBearSignal = series_of(false);
const myBullBiasSeries = series_of(false);
const myBearBiasSeries = series_of(false);
const myCallLabelSeries = series_of(null);
const myPutLabelSeries = series_of(null);
const myPositionSizeSeries = series_of(0);

// === Sequential state simulation (replicates Pine's bar-by-bar strategy state) ===
// position: 1 = long (CALL), -1 = short (PUT), 0 = flat
let myPosition = 0;
let myPositionAvgPrice = null;
let myLastBullBar = null;
let myLastBearBar = null;

for (let myIndex = 1; myIndex < myCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myInSession = myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay < mySessionEndMinutes;
	const mySessionOK = myUseSession ? myInSession : true;
	const myVol = myAvgVol[myIndex];
	const myVolActive = myVol != null && volume[myIndex] > myVol * myVolMult;
	const myBullBias = close[myIndex] > myVwapValue[myIndex] && myFastEma[myIndex] > mySlowEma[myIndex] && close[myIndex] > myTrendEma[myIndex];
	const myBearBias = close[myIndex] < myVwapValue[myIndex] && myFastEma[myIndex] < mySlowEma[myIndex] && close[myIndex] < myTrendEma[myIndex];
	const myBullPullback = myLowestLow[myIndex] != null && myLowestLow[myIndex] <= myFastEma[myIndex];
	const myBearPullback = myHighestHigh[myIndex] != null && myHighestHigh[myIndex] >= myFastEma[myIndex];
	const myBullBreak = close[myIndex] > high[myIndex - 1] && close[myIndex] > open[myIndex] && myFastEma[myIndex] > myFastEma[myIndex - 1];
	const myBearBreak = close[myIndex] < low[myIndex - 1] && close[myIndex] < open[myIndex] && myFastEma[myIndex] < myFastEma[myIndex - 1];
	const myBullSignalRaw = mySessionOK && myBullBias && myVolActive && myBullPullback && myBullBreak;
	const myBearSignalRaw = mySessionOK && myBearBias && myVolActive && myBearPullback && myBearBreak;
	const myBullCooldownOK = myLastBullBar === null || (myIndex - myLastBullBar > myCooldownBars);
	const myBearCooldownOK = myLastBearBar === null || (myIndex - myLastBearBar > myCooldownBars);
	const myBullSignalValue = myBullSignalRaw && myBullCooldownOK && myPosition <= 0;
	const myBearSignalValue = myBearSignalRaw && myBearCooldownOK && myPosition >= 0;

	if (myBullSignalValue) {
		myLastBullBar = myIndex;
	}
	if (myBearSignalValue) {
		myLastBearBar = myIndex;
	}

	// Entries
	if (myBullSignalValue) {
		myPosition = 1;
		myPositionAvgPrice = close[myIndex];
	}
	if (myBearSignalValue) {
		myPosition = -1;
		myPositionAvgPrice = close[myIndex];
	}

	// Exits (stop/target) and emergency VWAP exits, evaluated after entries
	if (myPosition > 0 && myPositionAvgPrice != null && myAtr[myIndex] != null) {
		const myLongStop = myPositionAvgPrice - myAtr[myIndex] * myStopATR;
		const myLongTarget = myPositionAvgPrice + myAtr[myIndex] * myTargetATR;
		if (low[myIndex] <= myLongStop || high[myIndex] >= myLongTarget) {
			myPosition = 0;
			myPositionAvgPrice = null;
		}
		else if (close[myIndex] < myVwapValue[myIndex]) {
			myPosition = 0;
			myPositionAvgPrice = null;
		}
	}
	else if (myPosition < 0 && myPositionAvgPrice != null && myAtr[myIndex] != null) {
		const myShortStop = myPositionAvgPrice + myAtr[myIndex] * myStopATR;
		const myShortTarget = myPositionAvgPrice - myAtr[myIndex] * myTargetATR;
		if (high[myIndex] >= myShortStop || low[myIndex] <= myShortTarget) {
			myPosition = 0;
			myPositionAvgPrice = null;
		}
		else if (close[myIndex] > myVwapValue[myIndex]) {
			myPosition = 0;
			myPositionAvgPrice = null;
		}
	}

	myBullSignal[myIndex] = myBullSignalValue;
	myBearSignal[myIndex] = myBearSignalValue;
	myBullBiasSeries[myIndex] = myBullBias;
	myBearBiasSeries[myIndex] = myBearBias;
	myPositionSizeSeries[myIndex] = myPosition;

	if (myShowLabels && myBullSignalValue) {
		myCallLabelSeries[myIndex] = low[myIndex];
	}
	if (myShowLabels && myBearSignalValue) {
		myPutLabelSeries[myIndex] = high[myIndex];
	}
}

// === Background bias coloring ===
const myCandleColors = for_every(myBullBiasSeries, myBearBiasSeries, (_bull, _bear) => {
	if (!myShowBg) return null;
	if (_bull) return 'rgba(0,128,0,0.12)';
	if (_bear) return 'rgba(255,0,0,0.12)';
	return null;
});
color_candles(myCandleColors);

// === Plots ===
paint(myShowVWAP ? myVwapValue : constants.empty_series, { name: 'VWAP', color: '#FFD500', thickness: 2 });
paint(myShowEMAs ? myFastEma : constants.empty_series, { name: 'Fast EMA', color: '#2ca599', thickness: 1 });
paint(myShowEMAs ? mySlowEma : constants.empty_series, { name: 'Slow EMA', color: '#ee5451', thickness: 1 });
paint(myShowEMAs ? myTrendEma : constants.empty_series, { name: 'Trend EMA', color: '#4DA3FF', thickness: 1 });

// === Labels ===
// Renamed paint() labels to avoid name collisions with register_signal()
// outputs, since both lists of names must be unique across the indicator.
paint(myCallLabelSeries, { name: 'Call Label', style: 'labels_below', color: '#2ca599' });
paint(myPutLabelSeries, { name: 'Put Label', style: 'labels_above', color: '#ee5451' });

// === Signals for scanner/alerts/strategy ===
// Renamed to "Call Signal Event" / "Put Signal Event" since "Call Signal"
// and "Put Signal" were already used as paint() label names above, and
// all series names (paint + register_signal) must be unique.
register_signal(myBullSignal, 'Call Signal Event');
register_signal(myBearSignal, 'Put Signal Event');
register_signal(myBullBiasSeries, 'Bullish Bias');
register_signal(myBearBiasSeries, 'Bearish Bias');