describe_indicator('Automated GEX Levels', 'price');

// User-provided raw GEX levels (from ZeroGEX NDX data)
const myRawCall = input.number('ZeroGEX Raw NDX Call Wall', 0.0, { min: -1000000, max: 1000000 });
const myRawFlip = input.number('ZeroGEX Raw NDX Gamma Flip', 0.0, { min: -1000000, max: 1000000 });

// Fetch NDX 5-minute close data to compute the "basis" (difference
// between the current symbol's price and the NDX index price).
// This mimics Pine's request.security("NASDAQ:NDX", "5", close).
// We wrap this call in try/catch because request.history() can throw
// (not just return an { error } object) when a ticker is invalid or
// unavailable, which is what caused the "[object Object]" crash.
let myNdxData = null;
let myNdxHasError = false;
let myNdxErrorText = '';

try {
	myNdxData = await request.history('NDX', '5');
	myNdxHasError = !!(myNdxData && myNdxData.error);

	if (myNdxHasError) {
		// .error can be a string or an object, so stringify safely
		myNdxErrorText = typeof myNdxData.error === 'string'
			? myNdxData.error
			: JSON.stringify(myNdxData.error);
	}
}
catch (myCaughtError) {
	myNdxHasError = true;
	myNdxErrorText = (myCaughtError && myCaughtError.message) ? myCaughtError.message : String(myCaughtError);
}

if (myNdxHasError) {
	console.log('Error fetching NDX data: ' + myNdxErrorText);
}

// Land NDX close values onto the current chart's time series.
// We use 'constant' interpolation (not 'linear') so the indicator
// does not look into the future and stays backtestable, matching
// Pine's non-repainting intrabar security behavior as closely as
// our engine allows.
const myNdxClose = myNdxHasError
	? series_of(0)
	: interpolate_sparse_series(
		land_points_onto_series(myNdxData.time, myNdxData.close, time, 'le'),
		'constant'
	);

// live_basis = close - NDX close (0 if NDX data could not be fetched)
const myLiveBasis = myNdxHasError ? series_of(0) : sub(close, myNdxClose);

// NQ Call Wall = raw_call + live_basis (only if raw_call > 0)
const myCallWallRaw = add(series_of(myRawCall), myLiveBasis);
const myCallWall = myRawCall > 0 ? myCallWallRaw : series_of(null);

// NQ Gamma Flip = raw_flip + live_basis (only if raw_flip > 0)
const myFlipRaw = add(series_of(myRawFlip), myLiveBasis);
const myFlip = myRawFlip > 0 ? myFlipRaw : series_of(null);

const myCallWallPainted = paint(myCallWall, { name: 'NQ Call Wall', color: 'green', thickness: 2, forceUsePriceAxis: true });
const myFlipPainted = paint(myFlip, { name: 'NQ Gamma Flip', color: 'orange', thickness: 2, forceUsePriceAxis: true });

// Scanning / strategy signals: price crossing above/below each level
const myCloseAboveCallWall = for_every(close, myCallWall, (_c, _lvl) => _lvl != null && _c > _lvl);
const myCloseAboveFlip = for_every(close, myFlip, (_c, _lvl) => _lvl != null && _c > _lvl);
const myCloseBelowCallWall = for_every(close, myCallWall, (_c, _lvl) => _lvl != null && _c < _lvl);
const myCloseBelowFlip = for_every(close, myFlip, (_c, _lvl) => _lvl != null && _c < _lvl);

register_signal(myCloseAboveCallWall, 'Close Above Call Wall');
register_signal(myCloseAboveFlip, 'Close Above Gamma Flip');
register_signal(myCloseBelowCallWall, 'Close Below Call Wall');
register_signal(myCloseBelowFlip, 'Close Below Gamma Flip');