describe_indicator('GLD Lasso Threshold Strategy', 'lower');

// Research indicator reproducing a Pine Script strategy based on
// Lasso-selected moving-average features from OHLCV data.
// Designed for GLD on the Daily timeframe. For research and
// educational purposes only, not investment advice.

const myThreshold = input.number('Threshold', 0.379073202241, { min: -10, max: 10, step: 0.000001 });

// Feature construction (mirrors Pine script exactly)
const myF0 = sma(volume, 2);
const myF1 = sma(sub(open, close), 1);
const myF2 = sma(mult(sub(high, close), sub(low, close)), 1);
const myF3 = mult(sma(sub(open, close), 2), sma(volume, 2));
const myF4 = mult(sma(sub(low, close), 1), sma(volume, 2));

// Linear score computed from standardized features with fixed coefficients
const myScore = for_every(myF0, myF1, myF2, myF3, myF4, (_f0, _f1, _f2, _f3, _f4) => {
	let myScoreLin = 0.5223463687150838;
	myScoreLin += (0.0012444888950145) * ((_f0 - (6735594.9841713225468993)) / (3241843.4822131437249482));
	myScoreLin += (0.0029769186339496) * ((_f1 - (-0.0910537243947856)) / (1.4953030683416331));
	myScoreLin += (0.0061458206471210) * ((_f2 - (-0.9481280302141537)) / (1.4894312820065110));
	myScoreLin += (0.0113005100794886) * ((_f3 - (-603183.3954082156997174)) / (9833879.5778208561241627));
	myScoreLin += (0.0065075254154198) * ((_f4 - (-8826653.8223241623491049)) / (11670853.5754192266613245));
	return myScoreLin;
});

// Long condition: score >= threshold (acts as entry/hold signal)
const myLongCondition = for_every(myScore, _s => _s >= myThreshold);
const myPositionFlag = for_every(myLongCondition, _c => _c ? 1 : 0);

// Register signals for scanners, alerts and strategy testing
register_signal(myLongCondition, 'Long Condition');
register_signal(for_every(myLongCondition, (_c, _p, _i) => _i > 0 && _c && !myLongCondition[_i - 1]), 'Enter Long');
register_signal(for_every(myLongCondition, (_c, _p, _i) => _i > 0 && !_c && myLongCondition[_i - 1]), 'Exit Long');

paint(myScore, { name: 'Score', color: '#00e5ff', thickness: 2 });
paint(horizontal_line(myThreshold), { name: 'Threshold', color: 'orange', style: 'dotted' });
paint(myPositionFlag, { name: 'Position Flag', color: '#26a69a', style: 'column' });