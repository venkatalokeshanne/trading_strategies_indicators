describe_indicator('Williams Vix Fix - Fear and Euphoria', 'lower');

// ─────────────────────────────────────────────────────────────────────────
// INPUTS
// ─────────────────────────────────────────────────────────────────────────
const mainTab = input.tab('Main');
// shortened titles below, since the platform rejects overly long input names
const myPd = mainTab.number('StdDev Lookback', 22, { min: 1, max: 500 });
const myBbl = mainTab.number('BB Length', 20, { min: 1, max: 500 });
const myMult = mainTab.number('BB StdDev Mult', 2.0, { min: 1, max: 5 });
const myLb = mainTab.number('Percentile Lookback', 50, { min: 1, max: 500 });
const myPh = mainTab.number('Highest Percentile', 0.85, { min: 0, max: 2, step: 0.01 });
const myPl = mainTab.number('Lowest Percentile', 1.01, { min: 0, max: 2, step: 0.01 });

const linesTab = input.tab('Lines');
const myShowPercentileLines = linesTab.boolean('Show Percentile Lines', false);
const myShowStdevLines = linesTab.boolean('Show Stdev Lines', false);

// ─────────────────────────────────────────────────────────────────────────
// WVF (ORIGINAL) — measures panic/strong drop -> FEAR signal -> positive histogram
// ─────────────────────────────────────────────────────────────────────────
const myHighestCloseBottom = highest(close, myPd);
const myWvf = mult(div(sub(myHighestCloseBottom, low), myHighestCloseBottom), 100);
// fixed: first argument of mult_() must be a series, so stdev() goes first
// and the numeric multiplier (myMult) goes second
const mySDevBottom = mult_(stdev(myWvf, myBbl), myMult);
const myMidLineBottom = sma(myWvf, myBbl);
const myUpperBandBottom = add(myMidLineBottom, mySDevBottom);
const myRangeHighBottom = mult_(highest(myWvf, myLb), myPh);
const myRangeLowBottom = mult_(lowest(myWvf, myLb), myPl);

// ─────────────────────────────────────────────────────────────────────────
// INVERSE WVF — measures euphoria/strong rally -> EUPHORIA signal -> negative histogram
// ─────────────────────────────────────────────────────────────────────────
const myLowestCloseTop = lowest(close, myPd);
const myInvWvf = mult(div(sub(high, myLowestCloseTop), myLowestCloseTop), 100);
// fixed: same swap as above, series first, number second
const mySDevTop = mult_(stdev(myInvWvf, myBbl), myMult);
const myMidLineTop = sma(myInvWvf, myBbl);
const myUpperBandTop = add(myMidLineTop, mySDevTop);
const myRangeHighTop = mult_(highest(myInvWvf, myLb), myPh);
const myRangeLowTop = mult_(lowest(myInvWvf, myLb), myPl);

// ─────────────────────────────────────────────────────────────────────────
// SIGNALS: fear/euphoria conditions
// ─────────────────────────────────────────────────────────────────────────
const myFearSignal = for_every(myWvf, myUpperBandBottom, myRangeHighBottom, (_wvf, _upper, _rangeHigh) => (_wvf >= _upper) || (_wvf >= _rangeHigh));
const myEuphoriaSignal = for_every(myInvWvf, myUpperBandTop, myRangeHighTop, (_invWvf, _upper, _rangeHigh) => (_invWvf >= _upper) || (_invWvf >= _rangeHigh));

const myColorBottom = for_every(myFearSignal, _fear => _fear ? '#00e676' : '#9e9e9e');
const myColorTop = for_every(myEuphoriaSignal, _euph => _euph ? '#ef5350' : '#bdbdbd');

const myNegInvWvf = mult_(myInvWvf, -1);
const myNegRangeHighTop = mult_(myRangeHighTop, -1);
const myNegUpperBandTop = mult_(myUpperBandTop, -1);

// ─────────────────────────────────────────────────────────────────────────
// PAINT
// ─────────────────────────────────────────────────────────────────────────
paint(myWvf, { name: 'WVF Fear', style: 'column', color: myColorBottom, thickness: 4 });
paint(myNegInvWvf, { name: 'Inverse WVF Euphoria', style: 'column', color: myColorTop, thickness: 4 });
paint(horizontal_line(0), { name: 'Zero Line', color: '#424242', thickness: 1, style: 'dotted' });
paint(myShowPercentileLines ? myRangeHighBottom : constants.empty_series, { name: 'Range High Fear', color: 'orange', thickness: 2 });
paint(myShowStdevLines ? myUpperBandBottom : constants.empty_series, { name: 'Upper Band Fear', color: 'aqua', thickness: 2 });
paint(myShowPercentileLines ? myNegRangeHighTop : constants.empty_series, { name: 'Range High Euphoria', color: 'orange', thickness: 2 });
paint(myShowStdevLines ? myNegUpperBandTop : constants.empty_series, { name: 'Upper Band Euphoria', color: 'aqua', thickness: 2 });

// ─────────────────────────────────────────────────────────────────────────
// SIGNALS for scanners/alerts/backtests
// ─────────────────────────────────────────────────────────────────────────
register_signal(myFearSignal, 'Fear Spike');
register_signal(myEuphoriaSignal, 'Euphoria Spike');

// helper used above since "mult" built-in sometimes used with constants too;
// defining a small wrapper to keep naming consistent with "mult" built-in usage.
// NOTE: first argument must always be a series, second a series or a number.
function mult_(mySeriesOrNumber, myFactor) {
	return mult(mySeriesOrNumber, myFactor);
}