// This indicator reproduces the Pine Script "Nonparametric Relative
// Momentum" by BackQuant. Percentile rank is computed via a manual
// sliding-window loop (not a built-in function), matching the Pine
// prank() logic exactly (mid-rank handling of ties).
describe_indicator('Nonparametric Relative Momentum', 'lower');

const oscTab = input.tab('Oscillator');
const myMode = oscTab.select('Rank Target', 'Momentum', ['Price', 'Momentum']);
const myLen = oscTab.number('Rank Window', 50, { min: 3, max: 300 });
const myMomLen = oscTab.number('Momentum Length', 32, { min: 1, max: 100 });
const mySmooth = oscTab.number('Output Smoothing', 1, { min: 1, max: 50 });

const sigTab = input.tab('Signal and Levels');
const mySigLen = sigTab.number('Signal Length', 9, { min: 1, max: 50 });
const myObLvl = sigTab.number('Overbought Zone', 90, { min: 50, max: 100 });
const myOsLvl = sigTab.number('Oversold Zone', 10, { min: 0, max: 50 });

const uiTab = input.tab('UI Settings');
const myShowOsc = uiTab.boolean('Show Oscillator', true);
const myShowMa = uiTab.boolean('Show Moving Average', true);
const myShowStatic = uiTab.boolean('Show OB OS Zones', true);
const myPaintBar = uiTab.boolean('Color Bars', true);

// Target series: raw source, or its rate-of-change (momentum)
const mySrc = close;
const myTarget = myMode === 'Momentum' ? sub(mySrc, shift(mySrc, myMomLen)) : mySrc;

// Manual percentile rank computation (mid-rank ties), matching Pine's
// prank(): for each candle, rank the current value against the
// previous `myLen` values (strictly historical, no look-ahead).
const myRank = series_of(null);
for (let myI = 0; myI < myTarget.length; myI += 1) {
	if (myI < myLen || myTarget[myI] === null || myTarget[myI] === undefined || isNaN(myTarget[myI])) {
		myRank[myI] = null;
		continue;
	}
	let myLess = 0.0;
	let myEq = 0.0;
	const myCurrent = myTarget[myI];
	let myValid = true;
	for (let myOffset = 1; myOffset <= myLen; myOffset += 1) {
		const myV = myTarget[myI - myOffset];
		if (myV === null || myV === undefined || isNaN(myV)) {
			myValid = false;
			break;
		}
		if (myCurrent > myV) {
			myLess += 1.0;
		}
		else if (myCurrent === myV) {
			myEq += 1.0;
		}
	}
	myRank[myI] = myValid ? (100.0 * (myLess + 0.5 * myEq) / myLen) : null;
}

const myPlotOsc = ema(myRank, mySmooth);
const mySigMa = ema(myPlotOsc, mySigLen);

// Conditional column color, stepped per Pine thresholds
const myOscColor = for_every(myPlotOsc, _o => {
	if (_o === null || _o === undefined) return '#1dcaff4d';
	if (_o > 50) {
		if (_o > 99) return '#33ff00fc';
		if (_o > 90) return '#00ff0080';
		if (_o > 75) return '#00ff003d';
		if (_o > 62.5) return '#1e9b254d';
		return '#1dcaff4d';
	}
	else if (_o < 50) {
		if (_o < 1) return '#ff0000';
		if (_o < 10) return '#ff000080';
		if (_o < 25) return '#ff00004d';
		if (_o < 37.5) return '#7715154d';
		return '#e651004d';
	}
	return '#1dcaff4d';
});

// NOTE: Pine uses histbase=50 for the column plot (bars grow from the
// 50 midline). TrendSpider column style has no histbase parameter, so
// we approximate by plotting the value minus 50 as a column (visually
// centered on 0 instead of 50) while keeping the underlying numeric
// value series itself unshifted for signals/scanners.
const myOscForColumn = myShowOsc ? sub(myPlotOsc, 50) : constants.empty_series;
paint(myOscForColumn, { name: 'PercentileRank', style: 'column', color: myOscColor });

paint(myShowMa ? mySigMa : constants.empty_series, { name: 'MovingAverage', color: 'white', thickness: 1 });

const myObUpper = paint(myShowStatic ? series_of(100) : constants.empty_series, { name: 'OBUpper', color: '#ff0000fc', style: 'line' });
const myObLower = paint(myShowStatic ? series_of(myObLvl) : constants.empty_series, { name: 'OBLower', color: '#ff0000fc', style: 'line' });
const myOsUpper = paint(myShowStatic ? series_of(myOsLvl) : constants.empty_series, { name: 'OSUpper', color: '#00ff00fc', style: 'line' });
const myOsLower = paint(myShowStatic ? series_of(0) : constants.empty_series, { name: 'OSLower', color: '#00ff00fc', style: 'line' });

fill(myObUpper, myObLower, '#7715154d', 0.3, 'OBFill');
fill(myOsUpper, myOsLower, '#1e9b254d', 0.3, 'OSFill');

paint(series_of(50), { name: 'MidLine', color: '#ffffff4d', style: 'dotted' });

// Trend candle coloring from oscillator side (price panel)
const myTrendColor = for_every(myPlotOsc, _o => (_o !== null && _o >= 50) ? '#33ff00fc' : '#ff0000fc');
color_candles(myPaintBar ? myTrendColor : constants.empty_series);

// Signals (crossовers), matching Pine alertcondition() logic
const myCrossUp50 = for_every(myPlotOsc, (_o, _prev, _i) => {
	const myPrevOsc = _i > 0 ? myPlotOsc[_i - 1] : null;
	return myPrevOsc !== null && _o !== null && myPrevOsc <= 50 && _o > 50;
});
const myCrossDown50 = for_every(myPlotOsc, (_o, _prev, _i) => {
	const myPrevOsc = _i > 0 ? myPlotOsc[_i - 1] : null;
	return myPrevOsc !== null && _o !== null && myPrevOsc >= 50 && _o < 50;
});
const myCrossUpMa = for_every(myPlotOsc, mySigMa, (_o, _ma, _prev, _i) => {
	const myPrevOsc = _i > 0 ? myPlotOsc[_i - 1] : null;
	const myPrevMa = _i > 0 ? mySigMa[_i - 1] : null;
	return myPrevOsc !== null && myPrevMa !== null && _o !== null && _ma !== null && myPrevOsc <= myPrevMa && _o > _ma;
});
const myCrossDownMa = for_every(myPlotOsc, mySigMa, (_o, _ma, _prev, _i) => {
	const myPrevOsc = _i > 0 ? myPlotOsc[_i - 1] : null;
	const myPrevMa = _i > 0 ? mySigMa[_i - 1] : null;
	return myPrevOsc !== null && myPrevMa !== null && _o !== null && _ma !== null && myPrevOsc >= myPrevMa && _o < _ma;
});

register_signal(myCrossUp50, 'Cross Up 50');
register_signal(myCrossDown50, 'Cross Down 50');
register_signal(myCrossUpMa, 'Bull Cross MA');
register_signal(myCrossDownMa, 'Bear Cross MA');