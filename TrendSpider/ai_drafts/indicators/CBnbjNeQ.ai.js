describe_indicator('Volume and Range Contraction Scanner V3', 'lower');

// Volume parameters
const myVolGroup = input.group('Volume');
const myShortVolLen = myVolGroup.number('Short Vol Avg Length', 10, { min: 1, max: 200 });
const myLongVolLen = myVolGroup.number('Long Vol Avg Length', 50, { min: 1, max: 300 });
const myVolRatioMax = myVolGroup.number('Volume Ratio Max', 0.70, { min: 0.01, max: 5, step: 0.01 });

// Range parameters
const myRangeGroup = input.group('Range');
const myRangeLen = myRangeGroup.number('Range Lookback Length', 10, { min: 1, max: 200 });
const myRangeMaxPct = myRangeGroup.number('Max Range Percent', 10.0, { min: 0.1, max: 100, step: 0.1 });
const myCompareBars = myRangeGroup.number('Range Compare Bars Ago', 20, { min: 1, max: 300 });

// 52 week high parameters
const myHighGroup = input.group('52 Week High');
const myNewHighLookback = myHighGroup.number('New High Lookback', 40, { min: 1, max: 300 });
const myYearBars = myHighGroup.number('Year Bars', 252, { min: 10, max: 500 });

// Volume dry up computation
const myShortVol = sma(volume, myShortVolLen);
const myLongVol = sma(volume, myLongVolLen);
const myVolRatio = for_every(myShortVol, myLongVol, (_s, _l) => (_l > 0 ? (_s / _l) : null));
const myVolumeDryUp = for_every(myVolRatio, _r => (_r !== null && _r <= myVolRatioMax));

// Range contraction computation
const myRangeHigh = highest(high, myRangeLen);
const myRangeLow = lowest(low, myRangeLen);
const myRangePct = for_every(myRangeHigh, myRangeLow, close, (_h, _l, _c) => (_c !== 0 ? ((_h - _l) / _c * 100) : null));

const myRangeTight = for_every(myRangePct, _p => (_p !== null && _p <= myRangeMaxPct));

const myPreviousRangePct = shift(myRangePct, myCompareBars);
const myRangeContracting = for_every(myRangePct, myPreviousRangePct, (_cur, _prev) => (_prev !== null && _cur !== null && _cur < _prev));

// 52 week new high computation
// previous52wHigh uses the high series shifted by 1 bar (i.e. excludes current bar),
// then takes the highest over "myYearBars" bars (approximates ta.highest(high[1], yearBars))
const myShiftedHigh = shift(high, 1);
const myPrevious52wHigh = highest(myShiftedHigh, myYearBars);

const myNewHigh = for_every(high, myPrevious52wHigh, (_h, _prevHigh) => (_prevHigh !== null && _h > _prevHigh));

const myNewHighNumeric = for_every(myNewHigh, _n => (_n ? 1 : 0));
const myRecentNewHighHighest = highest(myNewHighNumeric, myNewHighLookback);
const myRecentNewHigh = for_every(myRecentNewHighHighest, _v => (_v > 0));

// Bars since the last new high (equivalent of ta.barssince)
const myBarsSinceNewHigh = for_every(myNewHigh, (_isNewHigh, _prevValue, _index) => {
	if (_isNewHigh) {
		return 0;
	}
	const myPrev = (_prevValue === null || _prevValue === undefined) ? null : _prevValue;
	return (myPrev === null) ? null : (myPrev + 1);
});

// 200 day MA computation
const myMa200 = sma(close, 200);
const myMa200Shifted20 = shift(myMa200, 20);
const myMa200SlopePct = for_every(myMa200, myMa200Shifted20, (_m, _mPrev) => (_mPrev !== null && _mPrev !== 0 ? ((_m - _mPrev) / _mPrev * 100) : null));
const myMa200SlopeOK = for_every(myMa200SlopePct, _s => (_s !== null && _s >= 1.0));

const myMa200Shift5 = shift(myMa200, 5);
const myMa200Shift10 = shift(myMa200, 10);
const myMa200Shift15 = shift(myMa200, 15);
const myMa200Shift20 = shift(myMa200, 20);

const myMa200Rising = for_every(
	myMa200, myMa200Shift5, myMa200Shift10, myMa200Shift15, myMa200Shift20,
	(_m0, _m5, _m10, _m15, _m20) => (
		_m0 !== null && _m5 !== null && _m10 !== null && _m15 !== null && _m20 !== null &&
		_m0 > _m5 && _m5 > _m10 && _m10 > _m15 && _m15 > _m20
	)
);

// 50 day MA computation
const myMa50 = sma(close, 50);
const myAboveMa50 = for_every(close, myMa50, (_c, _m) => (_m !== null && _c > _m));
const myAboveMa200 = for_every(close, myMa200, (_c, _m) => (_m !== null && _c > _m));

// Final scanner condition
const myScannerMatch = for_every(
	myVolumeDryUp, myRangeTight, myRangeContracting, myRecentNewHigh,
	myMa200SlopeOK, myMa200Rising, myAboveMa50, myAboveMa200,
	(_a, _b, _c, _d, _e, _f, _g, _h) => (_a && _b && _c && _d && _e && _f && _g && _h)
);

// Output plots (mapped from Pine plot() calls)
paint(myVolRatio, { name: 'VolumeRatio', color: '#4DA3FF', style: 'line' });
paint(myRangePct, { name: 'RangePercent', color: '#EF5350', style: 'line' });
paint(for_every(myRangeTight, _v => (_v ? 1 : 0)), { name: 'RangeTight', color: '#26A69A', style: 'line' });
paint(for_every(myRangeContracting, _v => (_v ? 1 : 0)), { name: 'RangeContracting', color: '#AB47BC', style: 'line' });
paint(for_every(myRecentNewHigh, _v => (_v ? 1 : 0)), { name: 'Recent52WHigh', color: '#FFA726', style: 'line' });
paint(myBarsSinceNewHigh, { name: 'DaysSince52WHigh', color: '#78909C', style: 'line' });
paint(myMa200SlopePct, { name: 'MA200SlopePercent', color: '#26C6DA', style: 'line' });
paint(for_every(myMa200Rising, _v => (_v ? 1 : 0)), { name: 'MA200Rising', color: '#9CCC65', style: 'line' });
paint(for_every(myAboveMa50, _v => (_v ? 1 : 0)), { name: 'AboveMA50', color: '#FFD54F', style: 'line' });
paint(for_every(myAboveMa200, _v => (_v ? 1 : 0)), { name: 'AboveMA200', color: '#FF8A65', style: 'line' });
paint(for_every(myScannerMatch, _v => (_v ? 1 : 0)), { name: 'Scanner', color: '#00E676', style: 'column' });

// Register signals for use in scanners, alerts and strategy tester
register_signal(myVolumeDryUp, 'Volume Dry Up');
register_signal(myRangeTight, 'Range Tight');
register_signal(myRangeContracting, 'Range Contracting');
register_signal(myRecentNewHigh, 'Recent 52 Week High');
register_signal(myMa200SlopeOK, 'MA200 Slope OK');
register_signal(myMa200Rising, 'MA200 Rising');
register_signal(myAboveMa50, 'Above MA50');
register_signal(myAboveMa200, 'Above MA200');
register_signal(myScannerMatch, 'Scanner Match');