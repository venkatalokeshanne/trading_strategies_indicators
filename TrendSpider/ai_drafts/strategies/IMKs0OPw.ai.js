describe_indicator('Volatility Reversion Scalper', 'price');

// NOTE: ta.percentile_linear_interpolation is not a built in TrendSpider
// function, so it is reimplemented manually below using
// sliding_window_function with the exact same linear-interpolation
// method Pine Script uses (based on rank interpolation).
// Also, Pine's "barstate.isconfirmed" always refers to a closed candle,
// which is assumed to always be true for historical candles here.
// input.time() is not available, so start/end dates are exposed as
// plain unix timestamp number inputs (defaults match the original script).
// Input titles were shortened because the engine rejects overly long
// input names (fixes the "input(): name is too lengthy" error).
const myPd = input.number('StdDev Lookback', 11, { min: 1, max: 200 });
const myBbl = input.number('BB Length', 10, { min: 1, max: 200 });
const myMult = input.number('BB StdDev Mult', 5.0, { min: 1, max: 5 });
const myLb = input.number('Percentile Lookback', 25, { min: 1, max: 500 });
const myPh = input.number('Highest Percentile', 0.99, { min: 0, max: 2 });
const myPl = input.number('Lowest Percentile', 1.01, { min: 0, max: 2 });
const myLength = input.number('BB Fib Length', 10, { min: 1, max: 500 });
const myMultFib = input.number('BB Fib Mult', 0.618, { min: 0, max: 10 });
const myStartDate = input.number('Start Date', 1577836800);
const myEndDate = input.number('End Date', 1735689600);

// percentile with linear interpolation, replicating ta.percentile_linear_interpolation
function myPercentileLinear(mySeries, myWindowLength, myPercentage) {
	return sliding_window_function(mySeries, myWindowLength, myValues => {
		const mySorted = [...myValues].sort((_a, _b) => _a - _b);
		const myN = mySorted.length;
		let myRank = (myPercentage / 100) * (myN - 1);
		if (myRank < 0) myRank = 0;
		if (myRank > myN - 1) myRank = myN - 1;
		const myLow = Math.floor(myRank);
		const myHigh = Math.ceil(myRank);
		if (myLow === myHigh) return mySorted[myLow];
		return mySorted[myLow] + (mySorted[myHigh] - mySorted[myLow]) * (myRank - myLow);
	});
}

// CM_Williams_Vix_Fix calculation
const myHighestClose = highest(close, myPd);
const myWvf = mult(
	div(sub(myHighestClose, low), myHighestClose),
	100
);

// percentage params are truncated toward zero, as Pine's int() does
const myPhInt = Math.trunc(myPh * 100);
const myPlInt = Math.trunc(myPl * 100);

const myRangeHigh = myPercentileLinear(myWvf, myLb, myPhInt);
const myRangeLow = myPercentileLinear(myWvf, myLb, myPlInt);

const myVixFix = for_every(myWvf, myRangeHigh, myRangeLow, (_wvf, _rangeHigh, _rangeLow) => {
	if (_wvf >= _rangeHigh) return 1;
	if (_wvf <= _rangeLow) return -1;
	return 0;
});

// Bollinger Bands Fibonacci ratios
const myBasis = sma(close, myLength);
const myDev = mult(stdev(close, myLength), myMultFib);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

// Buy conditions
const myCondition1 = for_every(close, open, myLower, (_close, _open, _lower) => (_close <= _lower) || (_open <= _lower));
const myCondition2 = for_every(myVixFix, _vixFix => _vixFix === 1);
const myCondition3 = for_every(close, open, (_close, _open, _prev, _index) => {
	if (_index < 1) return false;
	return (_close > _open) && (close[_index - 1] < open[_index - 1]);
});
const myInDateRange = for_every(time, _time => (_time >= myStartDate) && (_time <= myEndDate));
const myBuyCondition = for_every(myCondition1, myCondition2, myCondition3, myInDateRange, (_c1, _c2, _c3, _c4) => _c1 && _c2 && _c3 && _c4);

// Visualization
paint(myBasis, { name: 'Basis', color: '#2962FF' });
paint(myUpper, { name: 'Upper', color: '#EF5350' });
paint(myLower, { name: 'Lower', color: '#26A69A' });

const myVixFixShape = for_every(myVixFix, _vixFix => _vixFix === 1 ? true : null);
paint(myVixFixShape, { name: 'VixFixSignal', style: 'labels_below', color: '#26A69A' });

// Signals for scanner, alerts and strategy tester
register_signal(myBuyCondition, 'Buy Condition');
register_signal(myCondition2, 'Vix Fix Signal');