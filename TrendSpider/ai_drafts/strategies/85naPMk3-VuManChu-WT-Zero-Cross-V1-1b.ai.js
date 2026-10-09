// This indicator paints price overlays (EMA, HTF PSAR) and WaveTrend
// zero-cross arrows, converted from a TradingView Pine Script strategy.
// NOTE: Only the "indicator"-side logic (signals, visuals) can be
// reproduced here. Strategy order management (strategy.entry,
// strategy.close, strategy.exit, pyramiding, position sizing) does not
// exist in the Custom JS API, so it is approximated via register_signal()
// outputs (Long Entry / Short Entry) that scanners, alerts and the
// Strategy Tester can consume instead.
describe_indicator('VuManChu WT Zero Cross V1.1b', 'price');

const myWtTab = input.tab('WaveTrend');
const myWtChannelLen = myWtTab.number('WT Channel Length', 9, { min: 1, max: 200 });
const myWtAverageLen = myWtTab.number('WT Average Length', 27, { min: 1, max: 200 });
const myWtMALen = myWtTab.number('WT MA Length', 3, { min: 1, max: 200 });
const myWtSourceName = myWtTab.select('WT Source', 'hlc3', constants.price_source_options);

const myTrendTab = input.tab('Trend Filter');
const myEnableTrendFilter = myTrendTab.boolean('Enable EMA Filter', false);
const myEmaLength = myTrendTab.number('EMA Length', 200, { min: 1, max: 1000 });

const myVisualsTab = input.tab('Visuals');
const myVisualsRow = myVisualsTab.row();
const myShowEMA = myVisualsRow.boolean('Show EMA', true);
const myShowPSAR = myVisualsRow.boolean('Show HTF PSAR', true);
const myShowArrows = myVisualsRow.boolean('Show Entry Arrows', true);

const myPsarTab = input.tab('PSAR');
const myPsarRow1 = myPsarTab.row();
const myPsarStart = myPsarRow1.number('PSAR Start', 0.0075, { min: 0.0001, max: 1, step: 0.0001 });
const myPsarInc = myPsarRow1.number('PSAR Increment', 0.0075, { min: 0.0001, max: 1, step: 0.0001 });
const myPsarMax = myPsarRow1.number('PSAR Maximum', 0.075, { min: 0.0001, max: 1, step: 0.0001 });
const myPsarTF = myPsarTab.select('PSAR Timeframe', 'Auto', ['Auto', '5', '10', '15', '30', '60', '120', '240', '480', 'D']);

// Resolve "Auto" PSAR timeframe based on current chart resolution,
// mirroring the Pine script's mapping table.
function myResolveAutoPsarTF() {
	const myRes = current.resolution;
	if (myRes == '1') return '2';
	if (myRes == '5') return '10';
	if (myRes == '15') return '30';
	if (myRes == '30') return '60';
	if (myRes == '60') return '120';
	if (myRes == '240') return '480';
	if (myRes == 'D') return '2D';
	return '120';
}

const mySelectedPsarTF = myPsarTF != 'Auto' ? myPsarTF : myResolveAutoPsarTF();

const myWtSource = market[myWtSourceName];

// WaveTrend math
const myEsa = ema(myWtSource, myWtChannelLen);
const myDe = ema(for_every(myWtSource, myEsa, (_s, _e) => Math.abs(_s - _e)), myWtChannelLen);
const myCi = for_every(myWtSource, myEsa, myDe, (_s, _e, _d) => (_s - _e) / (0.015 * _d));
const myWt1 = ema(myCi, myWtAverageLen);
const myWt2 = sma(myWt1, myWtMALen);

// Crossover / crossunder of WT1 vs zero
const myWt1Prev = shift(myWt1, 1);
const myLongSignalRaw = for_every(myWt1, myWt1Prev, (_w, _pw) => _w > 0 && _pw <= 0);
const myShortSignalRaw = for_every(myWt1, myWt1Prev, (_w, _pw) => _w < 0 && _pw >= 0);

// Trend filter
const myEmaFilter = ema(close, myEmaLength);
const myLongAllowed = for_every(close, myEmaFilter, (_c, _e) => !myEnableTrendFilter || _c > _e);
const myShortAllowed = for_every(close, myEmaFilter, (_c, _e) => !myEnableTrendFilter || _c < _e);

const myLongSignal = for_every(myLongSignalRaw, myLongAllowed, (_l, _a) => _l && _a);
const myShortSignal = for_every(myShortSignalRaw, myShortAllowed, (_s, _a) => _s && _a);

// HTF PSAR, fetched via request.history and computed off custom high/low
const myHtfDataPromise = request.history(current.ticker, mySelectedPsarTF);

async function myComputeHtfPsar() {
	const myHtfData = await myHtfDataPromise;
	assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);
	const myPsarHTFRaw = psar(myHtfData.high, myHtfData.low, myPsarMax, myPsarInc, myPsarStart);
	const myLanded = land_points_onto_series(myHtfData.time, myPsarHTFRaw, time, 'ge');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myPsarHTF = await myComputeHtfPsar();

// Visuals
paint(myShowEMA ? myEmaFilter : constants.empty_series, { name: 'EMA Filter', color: '#4DA3FF', thickness: 2 });
paint(myShowPSAR ? myPsarHTF : constants.empty_series, { name: 'HTF PSAR', color: '#9E9E9E', style: 'dotted', thickness: 1 });

const myLongArrowSeries = for_every(myLongSignalRaw, _l => (myShowArrows && _l) ? constants.icons.arrow_up : null);
const myShortArrowSeries = for_every(myShortSignalRaw, _s => (myShowArrows && _s) ? constants.icons.arrow_down : null);

paint(myLongArrowSeries, { name: 'Long Arrow', style: 'labels_below', color: 'green' });
paint(myShortArrowSeries, { name: 'Short Arrow', style: 'labels_above', color: 'red' });

// Signals for scanners / alerts / strategy tester
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');