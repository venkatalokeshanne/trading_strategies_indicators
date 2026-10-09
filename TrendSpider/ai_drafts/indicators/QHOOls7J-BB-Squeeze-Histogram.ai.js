describe_indicator('BB Squeeze Histogram', 'lower');

// Experiment note: this is a best-effort translation of a Pine Script v6
// indicator into TrendSpider Custom JS. Some Pine primitives (ta.vwap on a
// custom "length as bool" trick, ta.percentrank, ta.swma, histogram
// histbase) have no exact 1:1 equivalent in this engine, so approximations
// were used. Values should be close but may not match TradingView bar for bar.

const myTab = input.tab('Settings');
const mySource = myTab.select('Source', 'ohlc4', constants.price_source_options);
const myLength = myTab.number('Length', 20, { min: 1, max: 500 });

const myMultRow = myTab.row();
// Shortened title below (was too long and caused an input() error)
const myMult = myMultRow.number('Band SD Mult', 3.0, { min: 0.001, max: 50 });
const myOffset = myMultRow.number('ALMA offset', 0.89, { min: 0, max: 1 });

const mySigma = myTab.number('ALMA sigma', 5, { min: 1, max: 50 });
const myNormalize = myTab.boolean('Normalize to 0 100 scale', false);
const myNormLen = myTab.number('Normalize rank lookback', 200, { min: 10, max: 2000 });
const mySqueezeLen = myTab.number('Squeeze lookback', 100, { min: 10, max: 2000 });
const myAvgLen = myTab.number('Column average lookback', 100, { min: 10, max: 2000 });
const myMaType = myTab.select('MA Type', 'VWMA', ['SMA', 'EMA', 'RMA', 'WMA', 'VWMA', 'VWAP', 'HMA', 'SWMA', 'ALMA']);

const myPrice = market[mySource];

// compute basis MA according to the selected MA type
function computeMA(_src, _length, _type) {
	if (_type === 'SMA') return sma(_src, _length);
	if (_type === 'EMA') return ema(_src, _length);
	if (_type === 'RMA') return wildma(_src, _length);
	if (_type === 'WMA') return wma(_src, _length);
	if (_type === 'VWMA') return vwma(_src, _length);
	if (_type === 'VWAP') return vwap();
	if (_type === 'HMA') return hullma(_src, _length);
	if (_type === 'SWMA') return custwma(_src, [1, 2, 2, 1]);
	if (_type === 'ALMA') return alma(_src, _length, myOffset, mySigma);
	return sma(_src, _length);
}

const myBasis = computeMA(myPrice, myLength, myMaType);
const myDev = stdev(myPrice, myLength);

// gap between +mult SD and -mult SD bands, raw price units
const myWidth = mult(myDev, 2 * myMult);
const myNeutral = myNormalize ? series_of(50) : series_of(0);

// percent rank of current width against its own trailing history
const myRank = sliding_window_function(myWidth, myNormLen, _values => {
	const myCurrent = _values[_values.length - 1];
	const myCountLower = _values.filter(_v => _v < myCurrent).length;
	return (100 * myCountLower) / (_values.length - 1 || 1);
});

const myMag = myNormalize ? div(myRank, 2) : myWidth;

const myAbove = for_every(myPrice, myBasis, (_p, _b) => _p >= _b);
const myHist = for_every(myAbove, myMag, myNeutral, (_above, _mag, _neutral) => _above ? _neutral + _mag : _neutral - _mag);

const myExpanding = for_every(myWidth, (_w, _prev, _i) => _i === 0 ? true : _w >= myWidth[_i - 1]);

const myHistColor = for_every(myAbove, myExpanding, (_above, _expanding) => {
	if (_above) return _expanding ? '#26a69a' : '#b2dfdb';
	return _expanding ? '#ff5252' : '#ffcdd2';
});

paint(myHist, { name: 'BBWidthHistogram', style: 'column', color: myHistColor });
paint(myNeutral, { name: 'Neutral', color: 'gray', thickness: 1 });
paint(myNormalize ? series_of(100) : series_of(null), { name: 'TopRail', color: 'gray' });
paint(myNormalize ? series_of(0) : series_of(null), { name: 'BottomRail', color: 'gray' });

// rolling averages of positive and negative columns
const myPosVal = for_every(myAbove, myHist, (_above, _h) => _above ? _h : 0);
const myPosCnt = for_every(myAbove, _above => _above ? 1 : 0);
const myNegVal = for_every(myAbove, myHist, (_above, _h) => _above ? 0 : _h);
const myNegCnt = for_every(myAbove, _above => _above ? 0 : 1);

const myAvgPos = for_every(sum(myPosVal, myAvgLen), sum(myPosCnt, myAvgLen), (_s, _c) => _s / Math.max(_c, 1));
const myAvgNeg = for_every(sum(myNegVal, myAvgLen), sum(myNegCnt, myAvgLen), (_s, _c) => _s / Math.max(_c, 1));

paint(myAvgPos, { name: 'AvgPositiveColumn', color: '#ff0202', thickness: 1 });
paint(myAvgNeg, { name: 'AvgNegativeColumn', color: '#3cfe12', thickness: 1 });

// squeeze marker: raw width at its tightest over the lookback
const myLowestWidth = lowest(myWidth, mySqueezeLen);
const myInSqueeze = for_every(myWidth, myLowestWidth, (_w, _low) => _w === _low);
const mySqueezeMarker = for_every(myInSqueeze, myNeutral, (_sq, _n) => _sq ? _n : null);

paint(mySqueezeMarker, { name: 'Squeeze', style: 'dotted', color: 'yellow', thickness: 4 });

// signals for scanners, alerts and strategies
register_signal(myAbove, 'Price Above Basis');
register_signal(myInSqueeze, 'In Squeeze');
register_signal(myExpanding, 'Band Width Expanding');
register_signal(for_every(myAbove, myExpanding, (_a, _e) => _a && _e), 'Bullish Expansion');
register_signal(for_every(myAbove, myExpanding, (_a, _e) => !_a && _e), 'Bearish Expansion');