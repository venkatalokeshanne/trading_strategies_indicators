describe_indicator('AnPhat May', 'price');

// ===== INPUTS =====
const tabMain = input.tab('Main');

const emaFastLen = tabMain.number('EMA Fast Length', 9, { min: 1, max: 500 });
const emaSlowLen = tabMain.number('EMA Slow Length', 21, { min: 1, max: 500 });
const emaTrendLen = tabMain.number('EMA Trend Length', 34, { min: 1, max: 500 });
const mySrcName = tabMain.select('Price Source', 'close', constants.price_source_options);

const tabCloud = input.tab('Cloud');
const myGreenCloudColor = tabCloud.color('Green Cloud Color', 'rgba(0,255,0,0.2)');
const myRedCloudColor = tabCloud.color('Red Cloud Color', 'rgba(255,0,0,0.2)');
const myGreenLineColor = tabCloud.color('Green Line Color', 'lime');
const myRedLineColor = tabCloud.color('Red Line Color', 'red');

const tabTrend = input.tab('Trend EMA');
const myShowEma34 = tabTrend.boolean('Show EMA Trend', true);
const myEma34GreenColor = tabTrend.color('EMA Trend Green Color', 'lime');
const myEma34RedColor = tabTrend.color('EMA Trend Red Color', 'red');

const tabSignals = input.tab('Signals');
const myShowCrossSignal = tabSignals.boolean('Show Cross Signals', true);

const mySrc = market[mySrcName];

// ===== EMA CALCULATIONS =====
const myEmaFast = ema(mySrc, emaFastLen);
const myEmaSlow = ema(mySrc, emaSlowLen);
const myEmaTrend = ema(mySrc, emaTrendLen);

// isGreenCloud = emaFast >= emaSlow
const myIsGreenCloud = for_every(myEmaFast, myEmaSlow, (_fast, _slow) => _fast >= _slow);

const myLineColor = for_every(myIsGreenCloud, _isGreen => _isGreen ? myGreenLineColor : myRedLineColor);
const myCloudColor = myIsGreenCloud ? myGreenCloudColor : myRedCloudColor;

// EMA Fast / Slow lines with dynamic coloring, filled cloud between them
const myFastLinePainted = paint(myEmaFast, { name: 'EMA Fast', color: myLineColor, thickness: 2 });
const mySlowLinePainted = paint(myEmaSlow, { name: 'EMA Slow', color: myLineColor, thickness: 2 });

fill(myFastLinePainted, mySlowLinePainted, 'green', 0.2, 'AnPhat Cloud');

// EMA Trend line, colored based on whether close is above or below it
const myEma34Color = for_every(close, myEmaTrend, (_c, _t) => _c >= _t ? myEma34GreenColor : myEma34RedColor);
const myEma34ToPaint = myShowEma34 ? myEmaTrend : constants.empty_series;

paint(myEma34ToPaint, { name: 'EMA Trend', color: myEma34Color, thickness: 2 });

// ===== CROSS SIGNALS =====
// crossover: fast crosses above slow; crossunder: fast crosses below slow
const myBuySignalRaw = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return _fast > _slow && myEmaFast[_idx - 1] <= myEmaSlow[_idx - 1];
});

const mySellSignalRaw = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return _fast < _slow && myEmaFast[_idx - 1] >= myEmaSlow[_idx - 1];
});

const myBuySignal = myShowCrossSignal ? myBuySignalRaw : for_every(myBuySignalRaw, () => false);
const mySellSignal = myShowCrossSignal ? mySellSignalRaw : for_every(mySellSignalRaw, () => false);

const myBuyMarks = for_every(myBuySignal, _b => _b ? 1 : null);
const mySellMarks = for_every(mySellSignal, _s => _s ? 1 : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: 'lime' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// Signals usable for scanners, alerts, strategy tester
register_signal(myBuySignalRaw, 'EMA Fast crosses above EMA Slow (Buy)');
register_signal(mySellSignalRaw, 'EMA Fast crosses below EMA Slow (Sell)');