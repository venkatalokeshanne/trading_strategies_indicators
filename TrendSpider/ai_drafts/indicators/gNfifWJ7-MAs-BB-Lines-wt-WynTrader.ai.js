describe_indicator('MAs BB Lines wt WynTrader', 'price');

// Moving average period/type inputs, organized in rows
const ma1Row = input.row();
const i_ma1Len = ma1Row.number('MA1 Period', 8, { min: 1, max: 500 });
const i_ma1Type = ma1Row.select('MA1 Type', 'EMA', ['SMA', 'EMA', 'RMA', 'VWMA', 'HMA']);

const ma2Row = input.row();
const i_ma2Len = ma2Row.number('MA2 Period', 21, { min: 1, max: 500 });
const i_ma2Type = ma2Row.select('MA2 Type', 'SMA', ['SMA', 'EMA', 'RMA', 'VWMA', 'HMA']);

const ma3Row = input.row();
const i_ma3Len = ma3Row.number('MA3 Period', 50, { min: 1, max: 500 });
const i_ma3Type = ma3Row.select('MA3 Type', 'SMA', ['SMA', 'EMA', 'RMA', 'VWMA', 'HMA']);

const ma4Row = input.row();
const i_ma4Len = ma4Row.number('MA4 Period', 100, { min: 1, max: 500 });
const i_ma4Type = ma4Row.select('MA4 Type', 'SMA', ['SMA', 'EMA', 'RMA', 'VWMA', 'HMA']);

const ma5Row = input.row();
const i_ma5Len = ma5Row.number('MA5 Period', 200, { min: 1, max: 500 });
const i_ma5Type = ma5Row.select('MA5 Type', 'SMA', ['SMA', 'EMA', 'RMA', 'VWMA', 'HMA']);

// Projection inputs
const projGroup = input.group('Projections');
const i_projEnabled = projGroup.boolean('Activate Projection Lines', true);
const projRow = projGroup.row();
const i_projLookback = projRow.number('Lookback Bars', 3, { min: 3, max: 10 });
const i_projBars = projRow.number('Forward bars', 20, { min: 5, max: 30 });

// Maps a Pine-style MA type name to the matching built-in function
function myComputeMA(_type, _src, _length) {
	if (_type === 'SMA') return sma(_src, _length);
	if (_type === 'EMA') return ema(_src, _length);
	if (_type === 'RMA') return wildma(_src, _length);
	if (_type === 'VWMA') return vwma(_src, _length);
	if (_type === 'HMA') return hullma(_src, _length);
	return sma(_src, _length);
}

const mySource = close;

const myMa1 = myComputeMA(i_ma1Type, mySource, i_ma1Len);
const myMa2 = myComputeMA(i_ma2Type, mySource, i_ma2Len);
const myMa3 = myComputeMA(i_ma3Type, mySource, i_ma3Len);
const myMa4 = myComputeMA(i_ma4Type, mySource, i_ma4Len);
const myMa5 = myComputeMA(i_ma5Type, mySource, i_ma5Len);

paint(myMa1, { name: 'MA1', color: 'aqua', style: 'line', thickness: 1 });
paint(myMa2, { name: 'MA2', color: 'red', style: 'line', thickness: 1 });
paint(myMa3, { name: 'MA3', color: '#60F629', style: 'line', thickness: 1 });
paint(myMa4, { name: 'MA4', color: 'blue', style: 'line', thickness: 1 });
paint(myMa5, { name: 'MA5', color: 'orange', style: 'line', thickness: 1 });

// Bollinger Bands, fixed length/mult as in the original Pine script
const myBbLength = 18;
const myBbMult = 2.0;

const myBasis = sma(mySource, myBbLength);
const myDeviation = stdev(mySource, myBbLength);
const myUpperBand = add(myBasis, mult(myDeviation, myBbMult));
const myLowerBand = sub(myBasis, mult(myDeviation, myBbMult));

paint(myBasis, { name: 'BollingerBasis', color: 'red', thickness: 2 });
paint(myUpperBand, { name: 'BollUpperBand', color: 'white', thickness: 1 });
paint(myLowerBand, { name: 'BollLowerBand', color: 'white', thickness: 1 });

// Projections: extrapolate MA2..MA5 forward using slope measured over
// the lookback window, mirroring the Pine script's line.new logic.
function myBuildProjection(_maSeries) {
	const myLastIndex = _maSeries.length - 1;
	const myLastValue = _maSeries[myLastIndex];
	const myPastValue = _maSeries[myLastIndex - i_projLookback];
	const mySlope = (myLastValue - myPastValue) / i_projLookback;

	const myProjectionValues = [];
	for (let myStep = 0; myStep <= i_projBars; myStep += 1) {
		myProjectionValues.push(myLastValue + mySlope * myStep);
	}
	return myProjectionValues;
}

const myProj2 = i_projEnabled ? myBuildProjection(myMa2) : [];
const myProj3 = i_projEnabled ? myBuildProjection(myMa3) : [];
const myProj4 = i_projEnabled ? myBuildProjection(myMa4) : [];
const myProj5 = i_projEnabled ? myBuildProjection(myMa5) : [];

paint_projection(myProj2, { name: 'MA2Projection', color: 'red', style: 'dotted', thickness: 1 });
paint_projection(myProj3, { name: 'MA3Projection', color: '#60F629', style: 'dotted', thickness: 1 });
paint_projection(myProj4, { name: 'MA4Projection', color: 'blue', style: 'dotted', thickness: 1 });
paint_projection(myProj5, { name: 'MA5Projection', color: 'orange', style: 'dotted', thickness: 1 });

// Signals for scanners/alerts/backtesting: MA crossovers and
// price/MA crosses, plus Bollinger Band breakouts.
const myCloseAboveMa1 = for_every(close, myMa1, (_c, _m) => _c > _m);
const myCloseAboveMa2 = for_every(close, myMa2, (_c, _m) => _c > _m);
const myCloseAboveMa3 = for_every(close, myMa3, (_c, _m) => _c > _m);
const myCloseAboveMa4 = for_every(close, myMa4, (_c, _m) => _c > _m);
const myCloseAboveMa5 = for_every(close, myMa5, (_c, _m) => _c > _m);

register_signal(myCloseAboveMa1, 'Close Above MA1');
register_signal(myCloseAboveMa2, 'Close Above MA2');
register_signal(myCloseAboveMa3, 'Close Above MA3');
register_signal(myCloseAboveMa4, 'Close Above MA4');
register_signal(myCloseAboveMa5, 'Close Above MA5');

const myMa1CrossMa2Up = for_every(myMa1, myMa2, (_a, _b, _prev, _i) => _i > 0 && myMa1[_i - 1] <= myMa2[_i - 1] && _a > _b);
const myMa1CrossMa2Down = for_every(myMa1, myMa2, (_a, _b, _prev, _i) => _i > 0 && myMa1[_i - 1] >= myMa2[_i - 1] && _a < _b);

register_signal(myMa1CrossMa2Up, 'MA1 Cross Above MA2');
register_signal(myMa1CrossMa2Down, 'MA1 Cross Below MA2');

const myCloseAboveUpperBand = for_every(close, myUpperBand, (_c, _u) => _c > _u);
const myCloseBelowLowerBand = for_every(close, myLowerBand, (_c, _l) => _c < _l);

register_signal(myCloseAboveUpperBand, 'Close Above Upper Band');
register_signal(myCloseBelowLowerBand, 'Close Below Lower Band');