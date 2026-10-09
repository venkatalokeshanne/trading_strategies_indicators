describe_indicator('VuManChu WT Zero Cross Strategy V1.2.2', 'lower');

// ───────────────────────────────────────────────
// INPUTS
// ───────────────────────────────────────────────
const myWtTab = input.tab('WaveTrend');
const myWtChannelLen = myWtTab.number('WT Channel Length', 9, { min: 1, max: 100 });
const myWtAverageLen = myWtTab.number('WT Average Length', 27, { min: 1, max: 200 });
const myWtMALen = myWtTab.number('WT MA Length', 3, { min: 1, max: 100 });
const myWtSource = myWtTab.select('WT Source', 'hlc3', constants.price_source_options);

const myTrendTab = input.tab('Trend Filter');
const myEnableTrendFilter = myTrendTab.boolean('Enable Trend Filter', false);
const myEmaLength = myTrendTab.number('EMA Length', 200, { min: 1, max: 1000 });

const myVisualsTab = input.tab('Visuals');
const myShowEMA = myVisualsTab.boolean('Show EMA', true);
const myShowArrows = myVisualsTab.boolean('Show Entry Arrows', true);
const myShowTPDots = myVisualsTab.boolean('Show TP Dots', true);

// ───────────────────────────────────────────────
// WAVETREND CALCULATION
// ───────────────────────────────────────────────
const mySourceSeries = market[myWtSource];
const myEsa = ema(mySourceSeries, myWtChannelLen);
const myAbsDiff = for_every(mySourceSeries, myEsa, (_src, _esa) => Math.abs(_src - _esa));
const myDe = ema(myAbsDiff, myWtChannelLen);
const myCi = for_every(mySourceSeries, myEsa, myDe, (_src, _esa, _de) => (_src - _esa) / (0.015 * _de));
const myWt1 = ema(myCi, myWtAverageLen);
const myWt2 = sma(myWt1, myWtMALen);

// Zero-line crosses (crossover / crossunder of wt1 vs 0)
const myWt1Prev = shift(myWt1, 1);
const myLongSignal = for_every(myWt1, myWt1Prev, (_cur, _prev) => _cur > 0 && _prev <= 0);
const myShortSignal = for_every(myWt1, myWt1Prev, (_cur, _prev) => _cur < 0 && _prev >= 0);

// WT1/WT2 cross detection (sign change of the difference)
const myDiff = sub(myWt1, myWt2);
const myDiffPrev = shift(myDiff, 1);
const myWtCross = for_every(myDiff, myDiffPrev, (_cur, _prev) => (_cur >= 0 && _prev < 0) || (_cur <= 0 && _prev > 0));
const myBuyCircle = for_every(myWtCross, myWt1, myWt2, (_cross, _w1, _w2) => _cross && _w1 > _w2 && _w1 < -60 && _w2 < -60);
const mySellCircle = for_every(myWtCross, myWt1, myWt2, (_cross, _w1, _w2) => _cross && _w1 < _w2 && _w1 > 60 && _w2 > 60);

// ───────────────────────────────────────────────
// TREND FILTER
// ───────────────────────────────────────────────
const myEmaFilter = ema(close, myEmaLength);
const myLongAllowed = for_every(close, myEmaFilter, (_c, _ema) => !myEnableTrendFilter || _c > _ema);
const myShortAllowed = for_every(close, myEmaFilter, (_c, _ema) => !myEnableTrendFilter || _c < _ema);

// ───────────────────────────────────────────────
// STRATEGY SIMULATION (position sign tracking only,
// since take-profits only reduce size, not sign)
// ───────────────────────────────────────────────
const myLongTP = series_of(false);
const myShortTP = series_of(false);
let myPosition = 0;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myIsLong = myLongSignal[myIndex];
	const myIsShort = myShortSignal[myIndex];
	const myIsLongAllowed = myLongAllowed[myIndex];
	const myIsShortAllowed = myShortAllowed[myIndex];
	const myIsBuyCircle = myBuyCircle[myIndex];
	const myIsSellCircle = mySellCircle[myIndex];

	if (myIsLong && myIsLongAllowed) {
		myPosition = 1;
	}
	else if (myIsShort && myIsShortAllowed) {
		myPosition = -1;
	}
	else if (myIsLong && !myIsLongAllowed && myPosition < 0) {
		myPosition = 0;
	}
	else if (myIsShort && !myIsShortAllowed && myPosition > 0) {
		myPosition = 0;
	}
	else if (myPosition > 0 && myIsSellCircle) {
		myLongTP[myIndex] = true;
	}
	else if (myPosition < 0 && myIsBuyCircle) {
		myShortTP[myIndex] = true;
	}
}

// ───────────────────────────────────────────────
// VISUALS
// ───────────────────────────────────────────────
paint(myShowEMA ? myEmaFilter : constants.empty_series, { name: 'EMA Filter', color: '#f7c948', thickness: 2, forceUsePriceAxis: true });

const myLongArrowSeries = for_every(myLongSignal, _long => (myShowArrows && _long) ? constants.icons.arrow_up : null);
const myShortArrowSeries = for_every(myShortSignal, _short => (myShowArrows && _short) ? constants.icons.arrow_down : null);

// Note: paint() names must be unique across the whole indicator,
// including register_signal() names. Renamed the painted lines to
// avoid clashing with the signal names below.
paint(myLongArrowSeries, { name: 'LongEntryArrow', style: 'labels_below', color: '#26a69a' });
paint(myShortArrowSeries, { name: 'ShortEntryArrow', style: 'labels_above', color: '#ef5350' });

const myLongTPSeries = for_every(myLongTP, _tp => (myShowTPDots && _tp) ? constants.icons.circle : null);
const myShortTPSeries = for_every(myShortTP, _tp => (myShowTPDots && _tp) ? constants.icons.circle : null);

paint(myLongTPSeries, { name: 'LongTPDot', style: 'labels_above', color: '#ef5350' });
paint(myShortTPSeries, { name: 'ShortTPDot', style: 'labels_below', color: '#26a69a' });

// ───────────────────────────────────────────────
// SIGNALS (for scanners, alerts, strategy tester)
// ───────────────────────────────────────────────
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myLongTP, 'Long TP');
register_signal(myShortTP, 'Short TP');