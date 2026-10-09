describe_indicator('SHFE Ag Au Ratio', 'lower', { decimals: 4 });

// NOTE: TrendSpider has no exact equivalent of Pine's `request.security()`
// with `gaps_on` / `lookahead_off` merge semantics, and no `table.new()`.
// This is a best-effort reproduction: SHFE closes are fetched on their own
// time grid, the ratio is computed there, then landed onto the current
// chart's time axis using "last known value" (<=) and forward-filled
// (constant interpolation), which recreates Pine's "only updates on a new
// SHFE bar, otherwise holds last ratio" behavior. The on-chart table is
// replaced with a paint_overlay() table showing the latest values.

const myXagSymbol = input.symbol('International Silver (XAG)', 'OANDA:XAGUSD');
const myAgSymbol = input.symbol('SHFE Silver (AG)', 'SHFE:AG1!');
const myXauSymbol = input.symbol('International Gold (XAU)', 'OANDA:XAUUSD');
const myAuSymbol = input.symbol('SHFE Gold (AU)', 'SHFE:AU1!');

// Safely stringifies any error value (string, object, Error instance, etc).
// Raw request.history() rejections can carry a nested object/Error whose
// own message is already something like "history: [object Object]" - this
// is generated internally by the platform when a symbol/history request
// fails (e.g. invalid or unsupported ticker), and we can't change that
// text ourselves. We just make sure we never re-stringify an object badly
// on our own end, and we try to dig into common shapes to extract a
// readable message when possible.
function myStringifyError(_err) {
	if (_err == null) return 'unknown error';
	if (typeof _err === 'string') return _err;
	if (_err instanceof Error) return _err.message || String(_err);
	if (typeof _err === 'object') {
		if (typeof _err.message === 'string') return _err.message;
		if (typeof _err.error === 'string') return _err.error;
		try {
			return JSON.stringify(_err);
		}
		catch (_e) {
			return String(_err);
		}
	}
	return String(_err);
}

// Using Promise.allSettled instead of Promise.all so a single failing
// request.history() call (i.e., invalid/unsupported symbol) does not
// bubble up as an opaque rejection that kills the whole script before
// our own asserts can run. Instead we fall back to an empty series for
// that particular symbol, so the rest of the indicator still renders.
const myHistoryResults = await Promise.allSettled([
	request.history(myXagSymbol, current.resolution),
	request.history(myAgSymbol, current.resolution),
	request.history(myXauSymbol, current.resolution),
	request.history(myAuSymbol, current.resolution)
]);

const myHistoryLabels = ['XAG', 'SHFE AG', 'XAU', 'SHFE AU'];
const myEmptyHistory = { time: [], close: [] };

const [myXagData, myAgData, myXauData, myAuData] = myHistoryResults.map((_result, _i) => {
	if (_result.status === 'rejected') {
		// Instead of throwing (which crashes the whole indicator), fall
		// back to an empty data set for this symbol only. The resulting
		// ratio/price lines for this leg will simply be "na" everywhere.
		console.log('Error fetching ' + myHistoryLabels[_i] + ' data: ' + myStringifyError(_result.reason));
		return myEmptyHistory;
	}
	if (_result.value && _result.value.error) {
		console.log('Error fetching ' + myHistoryLabels[_i] + ' data: ' + myStringifyError(_result.value.error));
		return myEmptyHistory;
	}
	return _result.value;
});

// land XAG/XAU onto SHFE's own time grid so ratio is computed per SHFE bar
const myXagOnAgGrid = interpolate_sparse_series(
	land_points_onto_series(myXagData.time, myXagData.close, myAgData.time, 'le'),
	'constant'
);
const myXauOnAuGrid = interpolate_sparse_series(
	land_points_onto_series(myXauData.time, myXauData.close, myAuData.time, 'le'),
	'constant'
);

// raw ratio per SHFE bar: SHFE price / international price
const myAgRatioRaw = myAgData.close.map((_v, _i) => (myXagOnAgGrid[_i] ? myAgData.close[_i] / myXagOnAgGrid[_i] : null));
const myAuRatioRaw = myAuData.close.map((_v, _i) => (myXauOnAuGrid[_i] ? myAuData.close[_i] / myXauOnAuGrid[_i] : null));

// land ratios (and last SHFE prices) onto the main chart time, forward-filled
const myAgRatioLanded = interpolate_sparse_series(
	land_points_onto_series(myAgData.time, myAgRatioRaw, time, 'le'),
	'constant'
);
const myAuRatioLanded = interpolate_sparse_series(
	land_points_onto_series(myAuData.time, myAuRatioRaw, time, 'le'),
	'constant'
);

const myLastAgPrice = interpolate_sparse_series(
	land_points_onto_series(myAgData.time, myAgData.close, time, 'le'),
	'constant'
);
const myLastAuPrice = interpolate_sparse_series(
	land_points_onto_series(myAuData.time, myAuData.close, time, 'le'),
	'constant'
);

// land international prices onto the main chart time
const myXagLanded = interpolate_sparse_series(
	land_points_onto_series(myXagData.time, myXagData.close, time, 'le'),
	'constant'
);
const myXauLanded = interpolate_sparse_series(
	land_points_onto_series(myXauData.time, myXauData.close, time, 'le'),
	'constant'
);

const myXagToShfe = mult(myXagLanded, myAgRatioLanded);
const myXauToShfe = mult(myXauLanded, myAuRatioLanded);

// === main ratio lines (lower panel) ===
paint(myAgRatioLanded, { name: 'SHFE Silver Ratio', color: '#f58c3b', thickness: 2, style: 'line' });
paint(myAuRatioLanded, { name: 'SHFE Gold Ratio', color: '#2b2b2b', thickness: 2, style: 'line', forceUsePriceAxis: true });

// === auxiliary prices (forced onto price axis, equivalent to Pine's "data window" plots) ===
paint(myXagToShfe, { name: 'XAG Converted To SHFE', color: '#4DA3FF', thickness: 1, style: 'dotted', forceUsePriceAxis: true });
paint(myLastAgPrice, { name: 'Last SHFE Silver Price', color: '#888888', thickness: 1, style: 'dotted', forceUsePriceAxis: true });
paint(myXauToShfe, { name: 'XAU Converted To SHFE', color: '#2ca599', thickness: 1, style: 'dotted', forceUsePriceAxis: true });
paint(myLastAuPrice, { name: 'Last SHFE Gold Price', color: '#aaaaaa', thickness: 1, style: 'dotted', forceUsePriceAxis: true });

// === scanning/strategy signals ===
const myAgRatioRising = for_every(myAgRatioLanded, (_v, _p, _i) => _i > 0 && myAgRatioLanded[_i - 1] != null && _v != null && _v > myAgRatioLanded[_i - 1]);
const myAgRatioFalling = for_every(myAgRatioLanded, (_v, _p, _i) => _i > 0 && myAgRatioLanded[_i - 1] != null && _v != null && _v < myAgRatioLanded[_i - 1]);
const myAuRatioRising = for_every(myAuRatioLanded, (_v, _p, _i) => _i > 0 && myAuRatioLanded[_i - 1] != null && _v != null && _v > myAuRatioLanded[_i - 1]);
const myAuRatioFalling = for_every(myAuRatioLanded, (_v, _p, _i) => _i > 0 && myAuRatioLanded[_i - 1] != null && _v != null && _v < myAuRatioLanded[_i - 1]);

register_signal(myAgRatioRising, 'SHFE Silver Ratio Rising');
register_signal(myAgRatioFalling, 'SHFE Silver Ratio Falling');
register_signal(myAuRatioRising, 'SHFE Gold Ratio Rising');
register_signal(myAuRatioFalling, 'SHFE Gold Ratio Falling');

// === real time summary table (replaces Pine's table.new) ===
const myLastIndex = close.length - 1;
const myAgRatioText = myAgRatioLanded[myLastIndex] != null ? myAgRatioLanded[myLastIndex].toFixed(4) : 'na';
const myXagText = myXagLanded[myLastIndex] != null ? myXagLanded[myLastIndex].toFixed(3) : 'na';
const myXagToShfeText = myXagToShfe[myLastIndex] != null ? myXagToShfe[myLastIndex].toFixed(2) : 'na';
const myLastAgPriceText = myLastAgPrice[myLastIndex] != null ? myLastAgPrice[myLastIndex].toFixed(2) : 'na';
const myAuRatioText = myAuRatioLanded[myLastIndex] != null ? myAuRatioLanded[myLastIndex].toFixed(4) : 'na';
const myXauText = myXauLanded[myLastIndex] != null ? myXauLanded[myLastIndex].toFixed(3) : 'na';
const myXauToShfeText = myXauToShfe[myLastIndex] != null ? myXauToShfe[myLastIndex].toFixed(2) : 'na';
const myLastAuPriceText = myLastAuPrice[myLastIndex] != null ? myLastAuPrice[myLastIndex].toFixed(2) : 'na';

paint_overlay('SHFEAgAuTable', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'SHFE Silver Ratio: ' + myAgRatioText, color: '#f58c3b' }] },
		{ cells: [{ text: 'XAGUSD: ' + myXagText, color: '#4DA3FF' }] },
		{ cells: [{ text: 'Converted SHFE Silver: ' + myXagToShfeText, color: '#2ca599' }] },
		{ cells: [{ text: 'Last SHFE Silver: ' + myLastAgPriceText, color: '#888888' }] },
		{ cells: [{ text: 'SHFE Gold Ratio: ' + myAuRatioText, color: '#d4af37' }] },
		{ cells: [{ text: 'XAUUSD: ' + myXauText, color: '#4DA3FF' }] },
		{ cells: [{ text: 'Converted SHFE Gold: ' + myXauToShfeText, color: '#2ca599' }] },
		{ cells: [{ text: 'Last SHFE Gold: ' + myLastAuPriceText, color: '#888888' }] }
	]
});