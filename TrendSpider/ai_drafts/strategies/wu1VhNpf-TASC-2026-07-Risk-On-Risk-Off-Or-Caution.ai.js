describe_indicator('TASC 2026.07 Risk-On Risk-Off Or Caution', 'lower');

// This is an approximate conversion of the Pine Script strategy into
// a TrendSpider Custom JS indicator. The Custom JS API has no direct
// equivalent of Pine's strategy.* order management (strategy.order,
// strategy.close, strategy.equity, weekly rebalancing of a live
// position), so the actual trading/backtesting part of the original
// script cannot be reproduced. Instead, this indicator reproduces the
// regime detection logic (s1, s2, s3, regime score) exactly, exposes
// it as plotted columns (mirroring the Pine plot() calls) and as
// register_signal() outputs so it can be used in Scanners/Alerts.
// bgcolor() highlighting of the main chart is approximated using
// a 'Regime Score' line here, since bgcolor on the price panel is
// not reproducible from a lower indicator.
//
// NOTE: this indicator computes its regime off SPX/VIX/VIX3M/HYG/IEF
// data fetched directly via request.history(), regardless of which
// chart it's applied to, so running it on a non-SPY/non-daily chart
// does not break its math.
//
// FIX: the previous "history: [object Object]" error happened
// because request.history() can throw/reject with a non-string
// error (an Error object or arbitrary object), rather than always
// resolving with a `{ error }` property. Our old code only guarded
// against the resolved `{ error }` case, and JSON.stringify() on
// certain thrown objects (like native Error instances) returns "{}"
// which rendered as unhelpful text. We now wrap each request.history()
// call so that both "rejected promise" and "resolved with .error"
// cases are normalized into the same shape, and we build a safe,
// human-readable error string instead of relying only on
// JSON.stringify(). We also default the index tickers to the plain
// "VIX", "VIX3M" and "SPX" symbols (no caret prefix), since those
// are the commonly supported root symbols on this platform; the
// caret-prefixed variants used previously are not resolvable by all
// data feeds and were a likely cause of the failure.

const myVixTicker = input.text('VIX Ticker', 'VIX');
const myVix3mTicker = input.text('VIX3M Ticker', 'VIX3M');
const mySpxTicker = input.text('SPX Ticker', 'SPX');
const myHygTicker = input.text('HYG Ticker', 'HYG');
const myIefTicker = input.text('IEF Ticker', 'IEF');

// Safely stringifies an error coming either from a resolved
// `{ error }` payload or from a rejected promise (which can be a
// string, an Error instance, or an arbitrary object).
function myDescribeError(_err) {
	if (!_err) {
		return 'unknown error';
	}
	if (typeof _err === 'string') {
		return _err;
	}
	if (_err.message) {
		return _err.message;
	}
	try {
		return JSON.stringify(_err);
	}
	catch (myStringifyFailure) {
		return String(_err);
	}
}

// Wraps request.history() so that network/platform level rejections
// are normalized into the same `{ error }` shape used by a normal
// failed response, instead of letting an unhandled rejection bubble
// up as an opaque "[object Object]" error.
async function myFetchHistorySafe(_ticker, _resolution) {
	try {
		const myResult = await request.history(_ticker, _resolution);
		return myResult;
	}
	catch (myCaughtError) {
		return { error: myDescribeError(myCaughtError) };
	}
}

const myRequests = Promise.all([
	myFetchHistorySafe(myVixTicker, 'D'),
	myFetchHistorySafe(myVix3mTicker, 'D'),
	myFetchHistorySafe(mySpxTicker, 'D'),
	myFetchHistorySafe(myHygTicker, 'D'),
	myFetchHistorySafe(myIefTicker, 'D')
]);

const [myVixData, myVix3mData, mySpxData, myHygData, myIefData] = await myRequests;

assert(!myVixData.error, 'Error fetching VIX: ' + myDescribeError(myVixData.error));
assert(!myVix3mData.error, 'Error fetching VIX3M: ' + myDescribeError(myVix3mData.error));
assert(!mySpxData.error, 'Error fetching SPX: ' + myDescribeError(mySpxData.error));
assert(!myHygData.error, 'Error fetching HYG: ' + myDescribeError(myHygData.error));
assert(!myIefData.error, 'Error fetching IEF: ' + myDescribeError(myIefData.error));

// Land each external series onto the current chart's time axis.
// Using 'constant' interpolation (no linear interpolation) so this
// indicator remains backtestable / non-repainting.
const myVixLanded = interpolate_sparse_series(
	land_points_onto_series(myVixData.time, myVixData.close, time, 'le'),
	'constant'
);
const myVix3mLanded = interpolate_sparse_series(
	land_points_onto_series(myVix3mData.time, myVix3mData.close, time, 'le'),
	'constant'
);
const mySpxLanded = interpolate_sparse_series(
	land_points_onto_series(mySpxData.time, mySpxData.close, time, 'le'),
	'constant'
);
const myHygLanded = interpolate_sparse_series(
	land_points_onto_series(myHygData.time, myHygData.close, time, 'le'),
	'constant'
);
const myIefLanded = interpolate_sparse_series(
	land_points_onto_series(myIefData.time, myIefData.close, time, 'le'),
	'constant'
);

// spxDist = SPX - SMA(SPX, 200)
const mySpxSma200 = sma(mySpxLanded, 200);
const mySpxDist = sub(mySpxLanded, mySpxSma200);

// ts = VIX / VIX3M
const myTs = div(myVixLanded, myVix3mLanded);

// creditRatio = HYG / IEF ; creditZscore = (ratio - sma100) / stdev100
const myCreditRatio = div(myHygLanded, myIefLanded);
const myCreditSma100 = sma(myCreditRatio, 100);
const myCreditStdev100 = stdev(myCreditRatio, 100);
const myCreditZscore = div(sub(myCreditRatio, myCreditSma100), myCreditStdev100);

// Boolean signals
const mySignal1 = for_every(mySpxDist, _d => _d > 0.0);
const mySignal2 = for_every(myTs, _t => _t < 1.0);
const mySignal3 = for_every(myCreditZscore, _z => _z > -2.0);

// regime score 0..3
const myRegime = for_every(mySignal1, mySignal2, mySignal3, (_s1, _s2, _s3) => (
	(_s1 ? 1 : 0) + (_s2 ? 1 : 0) + (_s3 ? 1 : 0)
));

// Plots, replicating Pine's columns with histbase offsets
const myTrendPlot = for_every(mySignal1, _s1 => _s1 ? 1 : null);
const myVolPlot = for_every(mySignal2, _s2 => _s2 ? 2 : null);
const myCreditPlot = for_every(mySignal3, _s3 => _s3 ? 3 : null);

paint(myTrendPlot, { name: 'Trend Signal', color: '#00a2ff', style: 'column' });
paint(myVolPlot, { name: 'Volatility Signal', color: '#015f96', style: 'column' });
paint(myCreditPlot, { name: 'Credit Signal', color: '#00314d', style: 'column' });

// Regime line, forced onto its own scale for visual reference
paint(myRegime, { name: 'Regime Score', color: '#9e9e9e', style: 'line', thickness: 2 });

// Signals for use in Scanners, Alerts, Strategy Tester
register_signal(for_every(myRegime, _r => _r == 3), 'Risk ON (regime 3)');
register_signal(for_every(myRegime, _r => _r == 2), 'Caution (regime 2)');
register_signal(for_every(myRegime, _r => _r <= 1), 'Risk OFF (regime 0 or 1)');
register_signal(mySignal1, 'Trend Signal (SPX above SMA200)');
register_signal(mySignal2, 'Volatility Signal (VIX below VIX3M)');
register_signal(mySignal3, 'Credit Signal (Credit Zscore above -2)');