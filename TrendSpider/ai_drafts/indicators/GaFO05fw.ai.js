describe_indicator('Yield Strength', 'price');

// NOTE: This is a best-effort port of a Pine Script indicator that relies on
// TradingView's `request.security()` multi-timeframe resampling trick and on
// TVC bond-yield tickers. The Custom JS API has no equivalent of resampling
// an "own symbol" series at a different timeframe via request.security, so
// EMAs here are computed directly on the spread series using whatever
// resolution the yield data comes back at (landed onto the chart's time
// axis). See the warnings block for the list of approximations made.
//
// FIX: the previous version could throw "history: [object Object]" because
// a rejected request.history() promise (not just a resolved {error}
// object) was never caught, and Promise.all() propagated the rejection as
// an uncaught object. We now wrap every request in a .catch() so a bad
// symbol always resolves to a safe { error } object instead of rejecting,
// and we never interpolate an error object directly into a string.
const myTab = input.tab('Yields');
const myYieldTf = myTab.select('Yield Timeframe', '60', constants.time_frames);
const myEmaTf = myTab.select('EMA Timeframe (approximated)', '60', constants.time_frames);
const myMaturity = myTab.select('Yield Maturity', '10Y', ['02Y', '05Y', '10Y']);
const myEmaRow = myTab.row();
const myEmaFast = myEmaRow.number('EMA Fast', 120, { min: 1, max: 1000 });
const myEmaSlow = myEmaRow.number('EMA Slow', 216, { min: 1, max: 1000 });

// Mapping currency -> bond root symbol (TVC prefix assumed, see warnings)
const myCurrencyToRoot = {
	USD: 'US', EUR: 'DE', JPY: 'JP', GBP: 'GB',
	CHF: 'CH', AUD: 'AU', NZD: 'NZ', CAD: 'CA'
};
const myCurrencies = Object.keys(myCurrencyToRoot);

function mySymbolFor(_currency) {
	const myRoot = myCurrencyToRoot[_currency];
	return myRoot ? `TVC:${myRoot}${myMaturity}` : '';
}

// Only fetch valid symbols. We never throw directly on a bad/unavailable
// symbol: each request is wrapped in .catch() so a rejected promise (which
// is what actually produced the "[object Object]" error before) turns into
// a normal { error } result instead of crashing Promise.all().
const myValidCurrencies = myCurrencies.filter(_currency => mySymbolFor(_currency) !== '');
const myHistoryPromises = myValidCurrencies.map(_currency => (
	request.history(mySymbolFor(_currency), myYieldTf).catch(_e => ({ error: 'request failed' }))
));
const myHistories = await Promise.all(myHistoryPromises);

const myYieldsByCurrency = {};
myValidCurrencies.forEach((_currency, _index) => {
	const myHistory = myHistories[_index];

	// Fall back to an empty series instead of throwing, so that one
	// bad/unavailable symbol does not break the whole indicator. Error
	// objects are never templated into strings (that is what produced
	// "[object Object]" originally).
	if (!myHistory || myHistory.error || !myHistory.time || myHistory.time.length === 0) {
		myYieldsByCurrency[_currency] = constants.empty_series;
		return;
	}

	const myLanded = land_points_onto_series(myHistory.time, myHistory.close, time, 'le');
	myYieldsByCurrency[_currency] = interpolate_sparse_series(myLanded, 'constant');
});

// Any currency without a valid symbol also gets an empty series
myCurrencies.forEach(_currency => {
	if (!myYieldsByCurrency[_currency]) {
		myYieldsByCurrency[_currency] = constants.empty_series;
	}
});

// Determine base/quote currency from the current ticker (first 3 / next 3 chars)
const myBaseCurrency = current.ticker.substring(0, 3).toUpperCase();
const myQuoteCurrency = current.ticker.substring(3, 6).toUpperCase();

const myYieldBase = myYieldsByCurrency[myBaseCurrency] || constants.empty_series;
const myYieldQuote = myYieldsByCurrency[myQuoteCurrency] || constants.empty_series;

const mySpread = sub(myYieldBase, myYieldQuote);
const myEma1 = ema(mySpread, myEmaFast);
const myEma2 = ema(mySpread, myEmaSlow);

// Crossover / crossunder detection
const myBullCross = for_every(myEma1, myEma2, (_e1, _e2, _prev, _index) => {
	if (_index === 0) return false;
	return _e1 > _e2 && myEma1[_index - 1] <= myEma2[_index - 1];
});

const myBearCross = for_every(myEma1, myEma2, (_e1, _e2, _prev, _index) => {
	if (_index === 0) return false;
	return _e1 < _e2 && myEma1[_index - 1] >= myEma2[_index - 1];
});

// Persistent trend color (like Pine's "var color")
const myTrendColor = for_every(myBullCross, myBearCross, (_bull, _bear, _prev) => {
	if (_bull) return 'lime';
	if (_bear) return 'red';
	return _prev || 'gray';
});

paint(mySpread, { name: 'Spread', color: 'gray' });
paint(myEma1, { name: 'EMA Short', color: myTrendColor, thickness: 2 });
paint(myEma2, { name: 'EMA Long', color: myTrendColor, thickness: 2 });

register_signal(myBullCross, 'Bullish Yield Cross');
register_signal(myBearCross, 'Bearish Yield Cross');

// Pair trend helper: sign of EMA fast vs EMA slow for a given spread series
function myPairTrend(_spreadSeries) {
	const myFast = ema(_spreadSeries, myEmaFast);
	const mySlow = ema(_spreadSeries, myEmaSlow);
	return for_every(myFast, mySlow, (_f, _s) => (_f > _s ? 1 : -1));
}

// Build the 28 cross-currency spreads
const myPairDefs = [
	['EUR', 'USD'], ['EUR', 'GBP'], ['EUR', 'AUD'], ['EUR', 'NZD'], ['EUR', 'CAD'], ['EUR', 'CHF'], ['EUR', 'JPY'],
	['GBP', 'USD'], ['GBP', 'AUD'], ['GBP', 'NZD'], ['GBP', 'CAD'], ['GBP', 'CHF'], ['GBP', 'JPY'],
	['AUD', 'USD'], ['AUD', 'NZD'], ['AUD', 'CAD'], ['AUD', 'CHF'], ['AUD', 'JPY'],
	['NZD', 'USD'], ['NZD', 'CAD'], ['NZD', 'CHF'], ['NZD', 'JPY'],
	['USD', 'CAD'], ['USD', 'CHF'], ['USD', 'JPY'],
	['CAD', 'CHF'], ['CAD', 'JPY'],
	['CHF', 'JPY']
];

const myScores = {};
myCurrencies.forEach(_currency => { myScores[_currency] = series_of(0); });

myPairDefs.forEach(([_plus, _minus]) => {
	const myPairSpread = sub(myYieldsByCurrency[_plus], myYieldsByCurrency[_minus]);
	const myTrend = myPairTrend(myPairSpread);
	myScores[_plus] = add(myScores[_plus], myTrend);
	myScores[_minus] = sub(myScores[_minus], myTrend);
});

const myPairTrendCur = myPairTrend(mySpread);

// Scoreboard overlay, mirrors the Pine table (last-bar snapshot only)
const myLastIndex = close.length - 1;
const myScoreRows = myCurrencies.map(_currency => ({
	cells: [
		{ text: _currency, color: 'var(--text-color)' },
		{ text: String(myScores[_currency][myLastIndex]), color: myScores[_currency][myLastIndex] > 0 ? 'lime' : 'red' }
	]
}));

paint_overlay('YieldStrengthScoreboard', { position: 'top_right' }, {
	rows: [
		{
			cells: [
				{ text: myBaseCurrency + myQuoteCurrency, color: 'yellow' },
				{ text: String(myPairTrendCur[myLastIndex]), color: myPairTrendCur[myLastIndex] > 0 ? 'lime' : 'red' }
			]
		},
		...myScoreRows
	]
});