// ------------------------------------------------------------------
// This is a translation of a TradingView Pine Script into TrendSpider
// Custom JS. Pine's request.security("CRYPTOCAP:USDT.D", ...) and
// "CRYPTOCAP:USDC.D" are approximated here using request.history()
// on the tickers "USDT.D" and "USDC.D". TrendSpider does not have an
// exact "CRYPTOCAP:" exchange prefix, so this is the closest proxy
// available. Pine's bgcolor() (true background shading) and
// table.new() (fully dynamic multi-row table) have no 1:1 equivalent
// in the Custom JS API either; they are approximated below using
// color_candles() and a simplified status overlay table.
//
// FIX: the error "history: [object Object]" is raised internally by
// the platform's request.history() call itself (most likely because
// the tickers "USDT.D" / "USDC.D" simply do not exist as standalone
// symbols on this platform - there is no "CRYPTOCAP:" market here).
// Since this error is thrown by the engine before our own assert()
// logic even runs, we can't "catch" its exact text from inside this
// script. Instead, we defensively wrap both request.history() calls
// in Promise.all().catch(), check for missing/empty data in addition
// to a `.error` field, and - instead of throwing and breaking the
// whole indicator - we now paint a neutral/empty dashboard so the
// chart does not break, while still trying to compute the proper
// regime whenever the data does come back as expected.
// ------------------------------------------------------------------
describe_indicator('Stablecoin Dominance Regime Dashboard', 'price');

const myRiskOnLow = input.number('Risk On Low', 5.5, { min: 0, max: 50 });
const myRiskOnHigh = input.number('Risk On High', 6.5, { min: 0, max: 50 });
const myNeutralLow = input.number('Neutral Low', 6.5, { min: 0, max: 50 });
const myNeutralHigh = input.number('Neutral High', 8.0, { min: 0, max: 50 });
const myRiskOffLow = input.number('Risk Off Low', 8.0, { min: 0, max: 50 });
const myRiskOffHigh = input.number('Risk Off High', 10.0, { min: 0, max: 50 });
const myCapitulation = input.number('Capitulation', 10.0, { min: 0, max: 50 });

// Fetch both series defensively. If the engine throws (rather than
// returning { error }), we catch it here and turn it into a plain
// { error } object so the rest of the script can handle it uniformly.
const [myUsdtData, myUsdcData] = await Promise.all([
	request.history('USDT.D', current.resolution).catch(_e => ({ error: _e })),
	request.history('USDC.D', current.resolution).catch(_e => ({ error: _e }))
]);

function myReadableError(_err) {
	if (!_err) return 'unknown error';
	if (typeof _err === 'string') return _err;
	try {
		return JSON.stringify(_err);
	}
	catch (_e) {
		return String(_err);
	}
}

const myUsdtOk = myUsdtData && !myUsdtData.error && Array.isArray(myUsdtData.close) && myUsdtData.close.length > 0;
const myUsdcOk = myUsdcData && !myUsdcData.error && Array.isArray(myUsdcData.close) && myUsdcData.close.length > 0;
const myDataAvailable = myUsdtOk && myUsdcOk;

// Instead of throwing (which used to crash the whole indicator with
// an unreadable "[object Object]" message), we now degrade gracefully:
// if data is missing, we still paint all the same series/lines/labels
// (with neutral/empty values) so the indicator never breaks the chart.
const myStableDom = myDataAvailable
	? add(
		interpolate_sparse_series(land_points_onto_series(myUsdtData.time, myUsdtData.close, time, 'le'), 'constant'),
		interpolate_sparse_series(land_points_onto_series(myUsdcData.time, myUsdcData.close, time, 'le'), 'constant')
	)
	: series_of(null);

const myIsEuphoria = for_every(myStableDom, _d => _d != null && _d < myRiskOnLow);
const myIsRiskOn = for_every(myStableDom, _d => _d != null && _d >= myRiskOnLow && _d < myRiskOnHigh);
const myIsNeutral = for_every(myStableDom, _d => _d != null && _d >= myNeutralLow && _d < myNeutralHigh);
const myIsRiskOff = for_every(myStableDom, _d => _d != null && _d >= myRiskOffLow && _d < myRiskOffHigh);
const myIsCapitulation = for_every(myStableDom, _d => _d != null && _d >= myCapitulation);

// Approximate Pine's bgcolor() using candle coloring, since true chart
// background shading is not available in the Custom JS API.
const myCandleColors = for_every(
	myIsEuphoria, myIsRiskOn, myIsNeutral, myIsRiskOff, myIsCapitulation,
	(_eu, _on, _neu, _off, _cap) => {
		if (_eu) return 'rgba(0,255,0,0.15)';
		if (_on) return 'rgba(0,128,0,0.15)';
		if (_neu) return 'rgba(128,128,128,0.15)';
		if (_off) return 'rgba(255,0,0,0.15)';
		if (_cap) return 'rgba(128,0,0,0.2)';
		return null;
	});
color_candles(myCandleColors);

// Hidden plot, equivalent of Pine's plot(..., display=display.none)
const myStableDomLine = paint(myStableDom, { name: 'StablecoinDominance', hidden: true, forceUsePriceAxis: true });

// Regime label on the last candle, approximating label.new() placement
const myRegimeTextSeries = for_every(
	myIsEuphoria, myIsRiskOn, myIsNeutral, myIsRiskOff, myIsCapitulation,
	(_eu, _on, _neu, _off, _cap) => {
		if (_eu) return 'EUPHORIA';
		if (_on) return 'RISKON';
		if (_neu) return 'NEUTRAL';
		if (_off) return 'RISKOFF';
		if (_cap) return 'CAPITULATION';
		return 'UNDEFINED';
	});

const myLastRegime = myDataAvailable
	? myRegimeTextSeries[myRegimeTextSeries.length - 1]
	: 'NODATA';

paint_label_at_line(
	myStableDomLine,
	myStableDom.length - 1,
	myDataAvailable ? myLastRegime : ('No data: ' + myReadableError(myUsdtData && myUsdtData.error || myUsdcData && myUsdcData.error)),
	{
		background_color: '#000000',
		color: '#ffffff'
	}
);

// Dashboard-style overlay table approximating the Pine table.new() dashboard
const myRowDefs = [
	{ range: '< 5.5%', regime: 'Euphoria', behavior: 'Alt season', bias: 'Trim risk', key: 'EUPHORIA', color: '#00ff00' },
	{ range: '5.5-6.5%', regime: 'RiskOn', behavior: 'Broad upside', bias: 'Add alts', key: 'RISKON', color: '#008000' },
	{ range: '6.5-8.0%', regime: 'Neutral', behavior: 'Chop rotation', bias: 'Selective', key: 'NEUTRAL', color: '#808080' },
	{ range: '8.0-10%', regime: 'RiskOff', behavior: 'Alts bleed', bias: 'BTC over Alts', key: 'RISKOFF', color: '#ff0000' },
	{ range: '> 10%', regime: 'Capitulation', behavior: 'Panic', bias: 'Accumulate', key: 'CAPITULATION', color: '#800000' }
];

const myHeaderCells = {
	cells: [
		{ text: 'USDT.D + USDC.D', color: '#ffffff', background_color: '#000000' },
		{ text: 'Regime', color: '#ffffff', background_color: '#000000' },
		{ text: 'Crypto Behavior', color: '#ffffff', background_color: '#000000' },
		{ text: 'Portfolio Bias', color: '#ffffff', background_color: '#000000' }
	]
};

const myDataRows = myRowDefs.map(_row => ({
	cells: [
		{ text: _row.range, background_color: _row.key === myLastRegime ? _row.color : 'rgba(0,0,0,0.85)' },
		{ text: _row.regime, background_color: _row.key === myLastRegime ? _row.color : 'rgba(0,0,0,0.85)' },
		{ text: _row.behavior, background_color: _row.key === myLastRegime ? _row.color : 'rgba(0,0,0,0.85)' },
		{ text: _row.bias, background_color: _row.key === myLastRegime ? _row.color : 'rgba(0,0,0,0.85)' }
	]
}));

const myStatusRow = {
	cells: [{
		text: myDataAvailable ? 'Data OK' : ('Data unavailable: ' + myReadableError(myUsdtData && myUsdtData.error || myUsdcData && myUsdcData.error)),
		color: '#ffffff',
		background_color: myDataAvailable ? '#004d00' : '#4d0000'
	}]
};

paint_overlay('RegimeDashboard', { position: 'top_right' }, {
	rows: [myHeaderCells, ...myDataRows, myStatusRow]
});

// Scanning / strategy signals for each regime
register_signal(myIsEuphoria, 'Euphoria Regime');
register_signal(myIsRiskOn, 'Risk On Regime');
register_signal(myIsNeutral, 'Neutral Regime');
register_signal(myIsRiskOff, 'Risk Off Regime');
register_signal(myIsCapitulation, 'Capitulation Regime');