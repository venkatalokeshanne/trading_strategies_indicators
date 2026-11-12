<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Expected Move from Options');

if (current.resolution != 'D') {
	throw "This indicator is only applicable to Daily time frame";
}

const myNumberOfExpirations = input.number('Number of Expirations', 10, { min: 1, max: 30 });

// Get the options schedule to find the nearest expirations
const mySchedule = await request.options_schedule(current.ticker);
assert(!mySchedule.error && mySchedule.length > 0, 'No options data available for this ticker');

// Sort expirations by DTE
const mySortedExpirations = mySchedule.sort((a, b) => a.expiration.dte - b.expiration.dte);

// Find expirations closest to the desired DTE
const myTargetExpirations = [];
for (const myExp of mySortedExpirations) {
	if (myTargetExpirations.length < myNumberOfExpirations) {
		myTargetExpirations.push(myExp);
	}
}

assert(myTargetExpirations.length > 0, 'Could not find suitable expirations');

// Fetch options data for all expirations and strikes at once
const myAllOptionsData = await request.options_data_for_all_expirations(
	current.ticker,
	6,
	['l', 'a', 'b'],
	'all'
);

assert(!myAllOptionsData.error, 'Error fetching options data: ' + myAllOptionsData.error);

const myCurrentPrice = myAllOptionsData.underlyingSymbolQuote.lastPrice;

// Load binary-search-bounds library for efficient strike lookup
const binarySearch = library('binary-search-bounds');

// Calculate expected move for each target expiration
const myExpectedMoves = [];
for (const myExpiration of myTargetExpirations) {
	const myExpirationCode = myExpiration.expiration.code;
	const myExpirationData = myAllOptionsData.resultByExpiration[myExpirationCode];
	
	if (!myExpirationData) {
		continue;
	}
	
	// Get sorted array of strikes
	const myStrikes = Object.keys(myExpirationData).map(Number).sort((a, b) => a - b);
	
	// Use binary search to find the first strike above the current price (ATM strike)
	const myAtmIndex = binarySearch.gt(myStrikes, myCurrentPrice);
	
	// If no strike is greater than current price, use the highest strike
	// Otherwise use the strike found by binary search
	const myAtmStrike = myAtmIndex >= myStrikes.length ? myStrikes[myStrikes.length - 1] : myStrikes[myAtmIndex];
	
	// Get the ATM straddle price (call premium + put premium)
	const myAtmData = myExpirationData[myAtmStrike];
	const myCallPrice = myAtmData?.C?.l || myAtmData?.C?.a || myAtmData?.C?.b || 0;
	const myPutPrice = myAtmData?.P?.l || myAtmData?.P?.a || myAtmData?.P?.b || 0;
	
	if (myCallPrice > 0 && myPutPrice > 0) {
		const myExpectedMove = myCallPrice + myPutPrice;
		myExpectedMoves.push({
			dte: myExpiration.expiration.dte,
			move: myExpectedMove
		});
	}
}

assert(myExpectedMoves.length > 0, 'Could not calculate expected moves from available options');

// Paint the current price as reference
const myCurrentClose = close[close.length - 1];
const myCurrentPriceLine = paint(series_of(myCurrentClose), { style: 'dotted', color: 'gray', name: 'Current Price' });

// Find the maximum DTE to determine projection length
const myMaxDte = Math.max(...myExpectedMoves.map(m => m.dte));

// Create projection arrays up to the maximum DTE
let myExpectedMoveHigh = series_of(null);
let myExpectedMoveLow = series_of(null);
myExpectedMoveHigh[0] = myCurrentClose;
myExpectedMoveLow[0] = myCurrentClose;

// For each expiration, set the expected move at its specific DTE
for (const myMoveData of myExpectedMoves) {
	const myDteIndex = myMoveData.dte;
	
	if (myDteIndex >= 0 && myDteIndex <= myMaxDte) {
		myExpectedMoveHigh[myDteIndex] = myCurrentClose + myMoveData.move;
		myExpectedMoveLow[myDteIndex] = myCurrentClose - myMoveData.move;
	}
}

myExpectedMoveLow = interpolate_sparse_series(myExpectedMoveLow);
myExpectedMoveHigh = interpolate_sparse_series(myExpectedMoveHigh);

// Create a horizontal line at current price for projection fills
const myCurrentPriceProjection = series_of(myCurrentClose);

// Paint the projections with separate fills above and below current price
const myUpperLine = paint_projection(myExpectedMoveHigh, { color: '#81ce6f', name: 'Upper Expected Move' });
const myLowerLine = paint_projection(myExpectedMoveLow, { color: '#d13232', name: 'Lower Expected Move' });
const myMiddleLine = paint_projection(myCurrentPriceProjection, { color: 'gray', style: 'dotted', hidden: true });

// Fill above current price in green
fill(
	myUpperLine,
	myMiddleLine,
	'#81ce6f',
	0.15
);

// Fill below current price in red
fill(
	myMiddleLine,
	myLowerLine,
	'#d13232',
	0.15
);</code>