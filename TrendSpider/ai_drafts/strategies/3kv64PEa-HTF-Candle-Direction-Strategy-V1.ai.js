// This is a conversion of a TradingView Pine Script strategy into a
// TrendSpider Custom JS indicator. Strategy order execution (entries,
// pyramiding, broker simulation) is not available in Custom JS API,
// so this script reproduces the SIGNAL LOGIC only, exposed via
// register_signal() so it can be used in Scanners, Alerts and the
// Strategy Tester.
describe_indicator('HTF Candle Direction Signals', 'lower');

const myHtfTab = input.tab('HTF Settings');
// Fixed: '720' is not a member of constants.time_frames, which caused
// the "default value must be available in a list of options" error.
// Using 'D' (Daily) as a valid default higher time frame instead.
const myHtfResolution = myHtfTab.select('Higher Timeframe', 'D', constants.time_frames);

const mySignalsTab = input.tab('Signals');
const myEnableSignals = mySignalsTab.boolean('Enable Signal Generation', true);
const myEnableBuy = mySignalsTab.boolean('Enable BUY Signals', true);
const myEnableSell = mySignalsTab.boolean('Enable SELL Signals', true);

const myFiltersTab = input.tab('Filters');
const myUseEmaFilter = myFiltersTab.boolean('Enable EMA Filter', true);
const myEmaLength = myFiltersTab.number('EMA Length', 50, { min: 1, max: 500 });
const myVolRow = myFiltersTab.row();
const myUseVolFilter = myVolRow.boolean('Enable Volume Filter', false);
const myVolMultiplier = myVolRow.number('Volume Multiplier', 1.0, { min: 0.1, max: 10, step: 0.1 });

// Fetch Higher Timeframe candle data.
const myHtfData = await request.history(current.ticker, myHtfResolution);
assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);

// Land HTF close/open onto the current chart's candles using
// non-repainting, constant ("le": landing to the last known closed HTF
// candle) interpolation. This is the equivalent of Pine's
// `lookahead=barmerge.lookahead_off`, which does not use future data.
const myClosedHtfOpenSparse = land_points_onto_series(myHtfData.time, myHtfData.open, time, 'le');
const myClosedHtfCloseSparse = land_points_onto_series(myHtfData.time, myHtfData.close, time, 'le');

const myHtfOpen = interpolate_sparse_series(myClosedHtfOpenSparse, 'constant');
const myHtfClose = interpolate_sparse_series(myClosedHtfCloseSparse, 'constant');

const myLongCondition = for_every(myHtfClose, myHtfOpen, (_c, _o) => _c != null && _o != null && _c > _o);
const myShortCondition = for_every(myHtfClose, myHtfOpen, (_c, _o) => _c != null && _o != null && _c < _o);

// EMA / Volume filters.
const myEmaValue = ema(close, myEmaLength);
const myVolAvg = sma(volume, 20);

const myEmaLong = for_every(close, myEmaValue, (_c, _e) => _c > _e);
const myEmaShort = for_every(close, myEmaValue, (_c, _e) => _c < _e);
const myVolOk = for_every(volume, myVolAvg, (_v, _va) => _v > _va * myVolMultiplier);

const myFilterLong = for_every(myEmaLong, myVolOk, (_el, _vo) => (!myUseEmaFilter || _el) && (!myUseVolFilter || _vo));
const myFilterShort = for_every(myEmaShort, myVolOk, (_es, _vo) => (!myUseEmaFilter || _es) && (!myUseVolFilter || _vo));

// Day-of-session identifier, used to implement "one trade per day".
const mySessionId = time.map(_t => bar_at(_t).session);

// Compute signalActive state + raw entry conditions in a single pass,
// since the "one signal per day" rule depends on previous candle state.
const myEnterLong = series_of(false);
const myEnterShort = series_of(false);
let mySignalActiveState = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myIsNewDay = myIndex > 0 && mySessionId[myIndex] != mySessionId[myIndex - 1];

	if (myIsNewDay) {
		mySignalActiveState = false;
	}

	const myLongRaw = myEnableSignals && myEnableBuy && myLongCondition[myIndex] && myFilterLong[myIndex] && !mySignalActiveState;
	const myShortRaw = myEnableSignals && myEnableSell && myShortCondition[myIndex] && myFilterShort[myIndex] && !mySignalActiveState;

	myEnterLong[myIndex] = myLongRaw;
	myEnterShort[myIndex] = myShortRaw;

	if (myLongRaw || myShortRaw) {
		mySignalActiveState = true;
	}
}

register_signal(myEnterLong, 'BUY Signal');
register_signal(myEnterShort, 'SELL Signal');

// Visual markers for the signals on the chart.
const myBuyMarks = for_every(myEnterLong, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(myEnterShort, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green', thickness: 3 });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red', thickness: 3 });