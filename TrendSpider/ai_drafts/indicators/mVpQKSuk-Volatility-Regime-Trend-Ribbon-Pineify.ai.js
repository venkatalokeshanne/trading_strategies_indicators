describe_indicator('Volatility Regime Trend Ribbon', 'price');

// NOTE: TrendSpider does not expose a distinct "barstate.isconfirmed" flag the
// way Pine does for the realtime bar. All bars are treated as confirmed/closed,
// which is the standard assumption for historical analysis in this engine.

// ───── Volatility Regime ─────
const regimeTab = input.tab('Volatility Regime');
const myAtrLength = regimeTab.number('ATR Length', 14, { min: 5, max: 100 });
const myPercentileLookback = regimeTab.number('ATR Percentile Lookback', 100, { min: 30, max: 500 });
const myLowThreshold = regimeTab.number('Low Volatility Threshold', 33.0, { min: 5.0, max: 45.0 });
const myHighThreshold = regimeTab.number('High Volatility Threshold', 67.0, { min: 55.0, max: 95.0 });

// ───── Adaptive Trend ─────
const trendTab = input.tab('Adaptive Trend');
const mySourceInput = trendTab.select('Trend Source', 'hlc3', constants.price_source_options);
const myLowVolLength = trendTab.number('Low Volatility Length', 18, { min: 2, max: 100 });
const myNormalVolLength = trendTab.number('Normal Volatility Length', 28, { min: 3, max: 150 });
const myHighVolLength = trendTab.number('High Volatility Length', 42, { min: 5, max: 250 });

// ───── Confidence Band ─────
const bandTab = input.tab('Confidence Band');
const myBandMultiplier = bandTab.number('Base ATR Multiplier', 1.0, { min: 0.1, max: 5.0, step: 0.1 });
const myLowVolBandScale = bandTab.number('Low Volatility Band Scale', 0.75, { min: 0.25, max: 3.0, step: 0.05 });
const myNormalVolBandScale = bandTab.number('Normal Volatility Band Scale', 1.0, { min: 0.25, max: 3.0, step: 0.05 });
const myHighVolBandScale = bandTab.number('High Volatility Band Scale', 1.35, { min: 0.25, max: 3.0, step: 0.05 });

// ───── Display ─────
const displayTab = input.tab('Display');
const myShowRibbon = displayTab.boolean('Show Confidence Band', true);
const myShowMarkers = displayTab.boolean('Show Confirmed Direction Markers', true);
const myColorBars = displayTab.boolean('Color Bars by Direction', false);

const mySource = market[mySourceInput];

// ATR
const myAtrValue = atr(high, low, close, myAtrLength);

// ta.percentrank(src, length): over a window of (length + 1) bars (current + length
// previous), percentage of bars whose value is strictly less than the current value.
const myAtrPercentile = sliding_window_function(myAtrValue, myPercentileLookback + 1, _values => {
	const myCurrent = _values[_values.length - 1];
	if (myCurrent === null || myCurrent === undefined) {
		return null;
	}
	const myPrior = _values.slice(0, -1);
	const myCount = myPrior.filter(_v => _v !== null && _v !== undefined && _v < myCurrent).length;
	return (myCount / myPercentileLookback) * 100;
});

// volatility regime: 0 = low, 1 = normal, 2 = high
const myVolatilityRegime = for_every(myAtrPercentile, _p => {
	if (_p === null || _p === undefined) {
		return 1;
	}
	if (_p <= myLowThreshold) {
		return 0;
	}
	if (_p >= myHighThreshold) {
		return 2;
	}
	return 1;
});

const myAdaptiveLength = for_every(myVolatilityRegime, _r => _r === 0 ? myLowVolLength : (_r === 2 ? myHighVolLength : myNormalVolLength));
const myRegimeBandScale = for_every(myVolatilityRegime, _r => _r === 0 ? myLowVolBandScale : (_r === 2 ? myHighVolBandScale : myNormalVolBandScale));
const mySmoothingAlpha = for_every(myAdaptiveLength, _len => 2.0 / (_len + 1.0));

// recursive adaptive EMA with per-bar dynamic alpha
const myAdaptiveTrend = for_every(mySource, mySmoothingAlpha, (_src, _alpha, _prev) => {
	if (_prev === null || _prev === undefined) {
		return _src;
	}
	return _prev + _alpha * (_src - _prev);
});

const myBandWidth = for_every(myAtrValue, myRegimeBandScale, (_atr, _scale) => (_atr === null || _atr === undefined) ? null : _atr * myBandMultiplier * _scale);

const myUpperBandRaw = for_every(myAdaptiveTrend, myBandWidth, (_t, _w) => (_w === null || _w === undefined) ? null : _t + _w);
const myLowerBandRaw = for_every(myAdaptiveTrend, myBandWidth, (_t, _w) => (_w === null || _w === undefined) ? null : _t - _w);

// recursive trend direction
const myTrendDirection = for_every(close, myUpperBandRaw, myLowerBandRaw, (_c, _u, _l, _prev) => {
	const myPrevDir = (_prev === null || _prev === undefined) ? 0 : _prev;
	if (_u === null || _u === undefined || _l === null || _l === undefined) {
		return myPrevDir;
	}
	if (_c > _u) {
		return 1;
	}
	if (_c < _l) {
		return -1;
	}
	return myPrevDir;
});

const myPrevTrendDirection = shift(myTrendDirection, 1);
const myPrevVolatilityRegime = shift(myVolatilityRegime, 1);

const myBullishSwitch = for_every(myTrendDirection, myPrevTrendDirection, (_d, _pd) => _d === 1 && _pd !== 1);
const myBearishSwitch = for_every(myTrendDirection, myPrevTrendDirection, (_d, _pd) => _d === -1 && _pd !== -1);
const myRegimeSwitch = for_every(myAtrPercentile, myVolatilityRegime, myPrevVolatilityRegime, (_p, _r, _pr) => (_p !== null && _p !== undefined) && (_pr !== null && _pr !== undefined) && _r !== _pr);

register_signal(myBullishSwitch, 'Bullish Trend Direction Switch');
register_signal(myBearishSwitch, 'Bearish Trend Direction Switch');
register_signal(myRegimeSwitch, 'Volatility Regime Switch');

// Ribbon shown/hidden while keeping line count constant
const myUpperBand = myShowRibbon ? myUpperBandRaw : constants.empty_series;
const myLowerBand = myShowRibbon ? myLowerBandRaw : constants.empty_series;

const myCenterLinePainted = paint(myAdaptiveTrend, { name: 'Adaptive Trend', color: '#5c7cfa', thickness: 2 });
const myUpperLinePainted = paint(myUpperBand, { name: 'Upper Confidence Band', color: '#ffa94d', thickness: 1 });
const myLowerLinePainted = paint(myLowerBand, { name: 'Lower Confidence Band', color: '#ffa94d', thickness: 1 });
fill(myUpperLinePainted, myLowerLinePainted, '#ffa94d', 0.12);

// markers
const myBullishMarkers = for_every(myBullishSwitch, _b => myShowMarkers && _b ? constants.icons.triangle_up : null);
const myBearishMarkers = for_every(myBearishSwitch, _b => myShowMarkers && _b ? constants.icons.triangle_down : null);
paint(myBullishMarkers, { name: 'Up', style: 'labels_below', color: '#2fdc8f' });
paint(myBearishMarkers, { name: 'Dn', style: 'labels_above', color: '#ff5c5c' });

// optional bar coloring by trend direction
const myBarColors = for_every(myTrendDirection, _d => {
	if (!myColorBars) {
		return null;
	}
	if (_d === 1) {
		return '#2fdc8f';
	}
	if (_d === -1) {
		return '#ff5c5c';
	}
	return '#9aa0a6';
});
color_candles(myBarColors);