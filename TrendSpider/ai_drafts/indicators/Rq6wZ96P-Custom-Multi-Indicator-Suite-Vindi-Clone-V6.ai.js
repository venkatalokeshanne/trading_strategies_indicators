describe_indicator('Custom Multi Indicator Suite Vindi Clone V6', 'price');

// ==========================================
// 1. DYNAMIC TREND RIBBON (THE CLOUD)
// ==========================================
const myCloudTab = input.tab('Trend Ribbon Settings');
const myFastLen = myCloudTab.number('Fast Length', 20, { min: 1, max: 500 });
const mySlowLen = myCloudTab.number('Slow Length', 50, { min: 1, max: 500 });

const myMaFast = ema(close, myFastLen);
const myMaSlow = ema(close, mySlowLen);

// Dynamic colors depending on trend direction
const myTrendBullish = for_every(myMaFast, myMaSlow, (_f, _s) => _f > _s);
const myFastColor = for_every(myTrendBullish, _b => _b ? 'green' : 'red');
const mySlowColor = for_every(myTrendBullish, _b => _b ? 'lime' : 'maroon');

const myFastLinePainted = paint(myMaFast, { name: 'Fast Ribbon Line', color: myFastColor, thickness: 2 });
const mySlowLinePainted = paint(myMaSlow, { name: 'Slow Ribbon Line', color: mySlowColor, thickness: 1 });

// Fill the cloud, green/red depending on trend, matching the ~85% transparency look
color_cloud(myMaFast, myMaSlow, '#00ff0026', '#ff000026', 'Bullish Cloud', 'Bearish Cloud', 0.15);

// ==========================================
// 2. AUTOMATED BUY/SELL ALERTS (UT BOT STYLE)
// ==========================================
const myAlertsTab = input.tab('Signal Settings');
const myPriceSource = myAlertsTab.select('Signal Source', 'close', constants.price_source_options);
// Shortened input name to avoid "name is too lengthy" error
const myKeyValue = myAlertsTab.number('Key Value', 2.0, { min: 0.1, max: 20, step: 0.5 });
const myAtrPeriod = myAlertsTab.number('ATR Period', 10, { min: 1, max: 100 });

const mySrc = market[myPriceSource];
const myXAtr = atr(high, low, close, myAtrPeriod);
const myNLoss = mult(myXAtr, myKeyValue);

// Recursive trailing stop, replicating Pine's `x_atr_trailing_stop` logic
const myTrailingStop = for_every(mySrc, myNLoss, (_s, _nl, _prev, _i) => {
	const myPrevStop = _i === 0 ? 0 : (_prev === null || _prev === undefined ? 0 : _prev);
	if (_s > myPrevStop && _s > myPrevStop) {
		return Math.max(myPrevStop, _s - _nl);
	}
	else if (_s < myPrevStop && _s < myPrevStop) {
		return Math.min(myPrevStop, _s + _nl);
	}
	else if (_s > myPrevStop) {
		return _s - _nl;
	}
	else {
		return _s + _nl;
	}
});

const myPrevTrailingStop = shift(myTrailingStop, 1);

// Position state tracking, replicating Pine's `pos` variable
const myPos = for_every(mySrc, myTrailingStop, myPrevTrailingStop, (_s, _ts, _pts, _prevPos, _i) => {
	const myPrevStopVal = _i === 0 ? 0 : (_pts === null || _pts === undefined ? 0 : _pts);
	if (_s > myPrevStopVal && _s <= myPrevStopVal) {
		return 1;
	}
	else if (_s < myPrevStopVal && _s >= myPrevStopVal) {
		return -1;
	}
	else {
		return _prevPos === null || _prevPos === undefined ? 0 : _prevPos;
	}
});

// ema with length 1 is just the source itself (kept for fidelity with the Pine script)
const myEmaFastSignal = ema(mySrc, 1);
const myDiff = sub(myEmaFastSignal, myTrailingStop);
const myPrevDiff = shift(myDiff, 1);

const myCrossover = for_every(myDiff, myPrevDiff, (_d, _pd) => _d > 0 && _pd <= 0);
const myCrossunder = for_every(myDiff, myPrevDiff, (_d, _pd) => _d < 0 && _pd >= 0);

const myBuySignal = for_every(myCrossover, myPos, (_co, _p) => _co && _p === 1);
const mySellSignal = for_every(myCrossunder, myPos, (_cu, _p) => _cu && _p === -1);

const myBuyMarks = for_every(myBuySignal, _b => _b ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Early Buy Alert Marker', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Early Sell Alert Marker', style: 'labels_above', color: 'red' });

// Renamed signal names so they don't collide with the paint() line names above,
// which was the cause of the "signal already exists" error.
register_signal(myBuySignal, 'Early Buy Signal');
register_signal(mySellSignal, 'Early Sell Signal');

// ==========================================
// 3. HORIZONTAL SUPPORT & RESISTANCE (LIQUIDITY LEVELS)
// ==========================================
const mySrTab = input.tab('Support and Resistance Levels');
// Shortened input name to avoid "name is too lengthy" error
const myPivotLen = mySrTab.number('Pivot Strength', 15, { min: 1, max: 200 });

const myPivotHighs = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLows = pivot_low(low, myPivotLen, myPivotLen);

// Carry each pivot value forward (like Pine's line.set_x2 extending the line to the right)
const myResistanceLine = series_of(null);
const mySupportLine = series_of(null);
let myCurrentRes = null;
let myCurrentSup = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPivotHighs[myIndex] !== null && myPivotHighs[myIndex] !== undefined) {
		myCurrentRes = myPivotHighs[myIndex];
	}
	if (myPivotLows[myIndex] !== null && myPivotLows[myIndex] !== undefined) {
		myCurrentSup = myPivotLows[myIndex];
	}
	myResistanceLine[myIndex] = myCurrentRes;
	mySupportLine[myIndex] = myCurrentSup;
}

paint(myResistanceLine, { name: 'Resistance Level', style: 'ladder', color: 'red', thickness: 1 });
paint(mySupportLine, { name: 'Support Level', style: 'ladder', color: 'blue', thickness: 1 });