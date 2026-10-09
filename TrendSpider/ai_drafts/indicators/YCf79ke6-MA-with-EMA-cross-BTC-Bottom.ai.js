// ============================================================
// EXPERIMENT NOTICE: This indicator ports a complex Pine Script
// that relies on several custom/obscure data feeds (Glassnode,
// Coinmetrics market cap and BTC supply tickers) via
// request.security(). TrendSpider's request.history() may or
// may not have data for these exact ticker strings, since they
// are vendor-specific tickers from TradingView's own data feeds,
// not standard exchange tickers. This port is a best-effort
// approximation: it reproduces the MA/EMA cross logic exactly,
// but the BTC market-cap "fair value" lines are approximate and
// may fail or return nulls if the underlying symbols aren't
// resolvable on TrendSpider's data pipe.
//
// FIX NOTE: the previous version crashed with
// "history: [object Object]" because one (or more) of the
// vendor tickers used below is not resolvable on TrendSpider,
// and request.history() can reject its Promise (not just return
// an {error} object) in that case. Promise.all() rethrows the
// first rejection immediately, which bubbled up as an unhandled
// error whose text was just the stringified error object. Each
// request.history() call below is now wrapped so a failure
// always resolves to a safe { error } object instead of
// rejecting, so the indicator never throws.
// ============================================================
describe_indicator('MA EMA Cross plus BTC Bottom', 'price');

const myTab = input.tab('Main');
const myHideUnnecessary = myTab.boolean('Hide Extra Lines', true);
const myRow = myTab.row();
const myMaLen = myRow.number('MA Length (SMA)', 22, { min: 1, max: 500 });
const myEmaLen = myRow.number('EMA Length', 11, { min: 1, max: 500 });

// Core MA / EMA
const myMaVal = sma(close, myMaLen);
const myEmaVal = ema(close, myEmaLen);

paint(myMaVal, { name: 'MA', color: '#2962ff', thickness: 2 });
paint(myEmaVal, { name: 'EMA', color: '#ff9800', thickness: 2 });

// Crossover / Crossunder logic (ta.crossover / ta.crossunder equivalent)
const myCrossUp = for_every(myEmaVal, myMaVal, (_ema, _ma, _prev, _idx) => {
	if (_idx === 0) return false;
	return _ema > _ma && myEmaVal[_idx - 1] <= myMaVal[_idx - 1];
});
const myCrossDn = for_every(myEmaVal, myMaVal, (_ema, _ma, _prev, _idx) => {
	if (_idx === 0) return false;
	return _ema < _ma && myEmaVal[_idx - 1] >= myMaVal[_idx - 1];
});

const myBuyMarks = for_every(myCrossUp, _up => _up ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myCrossDn, _dn => _dn ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: 'red' });

register_signal(myCrossUp, 'MA EMA Cross Up');
register_signal(myCrossDn, 'MA EMA Cross Down');

// ============================================================
// BTC Market Cap "fair value" lines.
// These rely on vendor tickers which may not resolve on
// TrendSpider. Each request is wrapped in a safe helper that
// never rejects, so the script never throws even if a ticker
// is unresolvable.
// ============================================================
const mySym1 = 'GLASSNODE:BTC_MARKETCAP';
const mySym2 = 'COINMETRICS:BTC_MARKETCAPREAL';
const mySym3 = 'BTC_MARKETCAPREAL';
const mySym4 = 'BTC_SUPPLY';

async function mySafeHistory(_ticker, _resolution) {
	try {
		const myResult = await request.history(_ticker, _resolution);
		if (!myResult || myResult.error) {
			return { error: (myResult && myResult.error) ? String(myResult.error) : `Unable to resolve ${_ticker}` };
		}
		return myResult;
	}
	catch (myException) {
		return { error: `Request failed for ${_ticker}: ${String(myException && myException.message ? myException.message : myException)}` };
	}
}

const [myData1W, myData2W, myData4D, myData3D] = await Promise.all([
	mySafeHistory(mySym1, 'W'),
	mySafeHistory(mySym2, 'W'),
	mySafeHistory(mySym4, 'D'),
	mySafeHistory(mySym3, 'D')
]);

// Expanding (cumulative, "var" accumulated since dataset start)
// mean/stdev of close, replicating f_x1() from the Pine script.
function myExpandingStdev(_closeSeries) {
	const myResult = [];
	let myV1 = 0;
	let myV2 = 0;
	let myV3 = 0;
	for (let myIndex = 0; myIndex < _closeSeries.length; myIndex += 1) {
		const myC = _closeSeries[myIndex];
		if (myC !== null && myC !== undefined && !isNaN(myC)) {
			myV1 += myC;
			myV2 += myC * myC;
			myV3 += 1;
		}
		const myM1 = myV3 > 0 ? myV1 / myV3 : null;
		const myM2 = myV3 > 0 ? (myV2 / myV3) - (myM1 * myM1) : null;
		myResult.push(myM2 !== null ? Math.sqrt(Math.max(0, myM2)) : null);
	}
	return myResult;
}

const myHasData1 = !myData1W.error && !myData2W.error && !myData4D.error;
const myHasData3 = !myData3D.error && !myData4D.error;

let myLine1 = series_of(null);
let myLine2 = series_of(null);
let myLine3 = series_of(null);
let myLine7 = series_of(null);
let myLine8 = series_of(null);
let myLine9 = series_of(null);
let myLine10 = series_of(null);
let myLine11 = series_of(null);
let myLine12 = series_of(null);
let myLine4 = series_of(null);
let myLine5 = series_of(null);
let myLine6 = series_of(null);

if (myHasData1) {
	const myGSeries = myExpandingStdev(myData1W.close); // _g (f_x1 on 1W data)
	const myISeries = myData2W.close; // _i

	// land weekly _g and _i onto their own weekly timestamps first (already aligned),
	// then land onto main chart timeline using "le" (most recent known value)
	const myGLanded = land_points_onto_series(myData1W.time, myGSeries, time, 'le');
	const myILanded = land_points_onto_series(myData2W.time, myISeries, time, 'le');
	const myKLanded = land_points_onto_series(myData4D.time, myData4D.close, time, 'le');

	const myGFilled = interpolate_sparse_series(myGLanded, 'constant');
	const myIFilled = interpolate_sparse_series(myILanded, 'constant');
	const myKFilled = interpolate_sparse_series(myKLanded, 'constant');

	myLine1 = for_every(myGFilled, myIFilled, myKFilled, (_g, _i, _k) => (_k ? ((-0.14 * _g + _i) / _k) : null));
	myLine2 = for_every(myGFilled, myIFilled, myKFilled, (_g, _i, _k) => (_k ? ((-0.17 * _g + _i) / _k) : null));
	myLine3 = for_every(myGFilled, myIFilled, myKFilled, (_g, _i, _k) => (_k ? ((-0.24 * _g + _i) / _k) : null));
}

if (myHasData3) {
	const myMLanded = land_points_onto_series(myData3D.time, myData3D.close, time, 'le');
	const myNLanded = land_points_onto_series(myData4D.time, myData4D.close, time, 'le');
	const myMFilled = interpolate_sparse_series(myMLanded, 'constant');
	const myNFilled = interpolate_sparse_series(myNLanded, 'constant');

	const myOSeries = for_every(myMFilled, myNFilled, (_m, _n) => (_n ? (_m / _n) : null));

	myLine4 = for_every(myOSeries, _o => (_o !== null ? _o * 0.75 : null));
	myLine5 = for_every(myOSeries, _o => (_o !== null ? _o * 0.85 : null));
	myLine6 = for_every(myOSeries, _o => (_o !== null ? _o * 0.90 : null));
	myLine7 = myOSeries;
	myLine8 = for_every(myOSeries, _o => (_o !== null ? _o * 1.5 : null));
	myLine9 = for_every(myOSeries, _o => (_o !== null ? _o * 2.0 : null));
	myLine10 = for_every(myOSeries, _o => (_o !== null ? _o * 3.0 : null));
	myLine11 = for_every(myOSeries, _o => (_o !== null ? _o * 3.5 : null));
	myLine12 = for_every(myOSeries, _o => (_o !== null ? (_o / (1 - (-13.0 / 100))) : null));
}

// Lines 4,5,6 are always shown (not gated by hide_unnecessary in the Pine script)
paint(myLine4, { name: 'Line4', color: 'white', thickness: 1 });
paint(myLine5, { name: 'Line5', color: 'silver', thickness: 1 });
paint(myLine6, { name: 'Line6', color: 'gray', thickness: 1 });

// Lines gated by "hide_unnecessary" toggle - always painted,
// but filled with nulls when hidden, per platform rules.
paint(myHideUnnecessary ? series_of(null) : myLine1, { name: 'Line1', color: '#ff6b6b' });
paint(myHideUnnecessary ? series_of(null) : myLine2, { name: 'Line2', color: '#4d79ff' });
paint(myHideUnnecessary ? series_of(null) : myLine3, { name: 'Line3', color: '#4caf50' });
paint(myHideUnnecessary ? series_of(null) : myLine7, { name: 'Line7', color: 'white', thickness: 2 });
paint(myHideUnnecessary ? series_of(null) : myLine8, { name: 'Line8', color: 'green' });
paint(myHideUnnecessary ? series_of(null) : myLine9, { name: 'Line9', color: 'yellow' });
paint(myHideUnnecessary ? series_of(null) : myLine10, { name: 'Line10', color: 'orange' });
paint(myHideUnnecessary ? series_of(null) : myLine11, { name: 'Line11', color: 'red' });
paint(myHideUnnecessary ? series_of(null) : myLine12, { name: 'Line12', color: '#4caf50', thickness: 3 });