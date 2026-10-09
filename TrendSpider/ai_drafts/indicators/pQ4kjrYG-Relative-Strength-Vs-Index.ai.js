describe_indicator('Relative Strength', 'lower');

// --- Index selection ---
const myIndexChoice = input.select('Comparative Index', 'NIFTY 50', [
	'NIFTY 50', 'NIFTY 500', 'NIFTY BANK', 'NIFTY MIDCAP 100', 'SENSEX', 'Custom'
]);
const myCustomSymbol = input.symbol('Custom Symbol (used when Custom is selected)', 'NSE:NIFTY');

function myGetIndexSymbol(_choice) {
	if (_choice === 'NIFTY 50') return 'NSE:NIFTY';
	if (_choice === 'NIFTY 500') return 'NSE:CNX500';
	if (_choice === 'NIFTY BANK') return 'NSE:BANKNIFTY';
	if (_choice === 'NIFTY MIDCAP 100') return 'NSE:NIFTYMID100';
	if (_choice === 'SENSEX') return 'BSE:SENSEX';
	return myCustomSymbol;
}

const myComparativeTickerId = myGetIndexSymbol(myIndexChoice);

// --- Other inputs ---
const myLength = input.number('Period', 50, { min: 1, max: 1000 });
const myShowMA = input.boolean('Show Moving Average', true);
const myLengthMA = input.number('Moving Average Period', 10, { min: 1, max: 1000 });

// --- Data requests ---
// Comparative symbol data is fetched on the same resolution as the current chart,
// then landed and interpolated onto the current chart's time axis ('constant' mode
// is used to keep this indicator backtestable / non-repainting).
//
// NOTE on the fix: the error "history: [object Object]" is thrown directly by the
// platform's own internal history-fetching layer (not by our own error-handling
// code), which means the underlying `request.history()` call rejected with an
// object whose message got lost in transit before it ever reached our catch
// block. We cannot change how the platform formats that internal exception, so
// instead we:
//   1) wrap the request in try/catch to avoid an opaque crash;
//   2) safely stringify whatever comes back;
//   3) if the fetch fails, surface a clearer, actionable message pointing at the
//      most likely cause: the selected index symbol/ticker ID is not resolvable
//      on this account/data feed (symbol formatting for Indian indices can vary
//      by data vendor), so the user should try the "Custom" option and pick the
//      exact symbol as it appears in Symbol Search.
function myStringifyError(_err) {
	if (_err == null) return 'unknown error';
	if (typeof _err === 'string') return _err;
	if (_err instanceof Error) return _err.message;
	try {
		return JSON.stringify(_err);
	}
	catch (myStringifyFailure) {
		return String(_err);
	}
}

let myComparativeData = null;
let myComparativeFetchError = null;

try {
	myComparativeData = await request.history(myComparativeTickerId, current.resolution);

	if (myComparativeData && myComparativeData.error) {
		myComparativeFetchError = myStringifyError(myComparativeData.error);
	}
	else if (!Array.isArray(myComparativeData?.close) || myComparativeData.close.length === 0) {
		myComparativeFetchError = 'Comparative symbol data returned no candles.';
	}
}
catch (myCaughtError) {
	myComparativeFetchError = myStringifyError(myCaughtError);
}

assert(
	!myComparativeFetchError,
	`Could not fetch comparative symbol "${myComparativeTickerId}" (reason: "${myComparativeFetchError}"). ` +
	`This usually means the symbol ID is not valid for this data feed/account. ` +
	`Try selecting "Custom" and pick the index via Symbol Search instead of relying on the preset ID.`
);

const myComparativeLanded = land_points_onto_series(myComparativeData.time, myComparativeData.close, time, 'le');
const myComparativeClose = interpolate_sparse_series(myComparativeLanded, 'constant');
const myBaseClose = close;

// res = (base / base[length]) / (comparative / comparative[length]) - 1
const myBaseRatio = div(myBaseClose, shift(myBaseClose, myLength));
const myComparativeRatio = div(myComparativeClose, shift(myComparativeClose, myLength));
const myRes = sub(div(myBaseRatio, myComparativeRatio), 1);

paint(horizontal_line(0), { name: 'Zero', color: 'black', style: 'dotted' });
paint(myRes, { name: 'RS', color: 'green', thickness: 2 });

const mySmaOfRes = sma(myRes, myLengthMA);
paint(myShowMA ? mySmaOfRes : series_of(null), { name: 'RSMA', color: 'red', thickness: 1 });

// --- Signals for scanner/strategy/alerts use ---
const myRsAboveZero = for_every(myRes, _r => _r > 0);
register_signal(myRsAboveZero, 'RS Above Zero');

const myRsCrossAboveZero = for_every(myRes, (_r, _prev, _i) => _i > 0 && _r > 0 && myRes[_i - 1] <= 0);
register_signal(myRsCrossAboveZero, 'RS Crosses Above Zero');

const myRsCrossBelowZero = for_every(myRes, (_r, _prev, _i) => _i > 0 && _r < 0 && myRes[_i - 1] >= 0);
register_signal(myRsCrossBelowZero, 'RS Crosses Below Zero');

const myRsAboveMA = for_every(myRes, mySmaOfRes, (_r, _ma) => _r > _ma);
register_signal(myRsAboveMA, 'RS Above MA');

const myRsCrossAboveMA = for_every(myRes, mySmaOfRes, (_r, _ma, _prev, _i) => _i > 0 && _r > _ma && myRes[_i - 1] <= mySmaOfRes[_i - 1]);
register_signal(myRsCrossAboveMA, 'RS Crosses Above MA');

const myRsCrossBelowMA = for_every(myRes, mySmaOfRes, (_r, _ma, _prev, _i) => _i > 0 && _r < _ma && myRes[_i - 1] >= mySmaOfRes[_i - 1]);
register_signal(myRsCrossBelowMA, 'RS Crosses Below MA');