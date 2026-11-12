<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Current Market Cap Multi-ticker', 'lower');

const quarters = input.number('Quarters', 40, { min: 1, max: 40 });

// Allow users to specify additional tickers to compare
// These inputs let you easily change which tickers to display alongside the current one
const myTicker2 = input.symbol('Ticker 2', 'NVDA');
const myTicker3 = input.symbol('Ticker 3', 'GOOG');
const myTicker4 = input.symbol('Ticker 4', 'MSFT');
const myTicker5 = input.symbol('Ticker 5', 'AMZN');

// Helper function to compute market cap for a given ticker
// This avoids code duplication since we'll calculate the same thing for multiple tickers
const computeMarketCap = async (myTickerSymbol) => {
	const myFundamentalData = await request.fundamental(myTickerSymbol, ['shares_basic_bs'], quarters);
	
	if (myFundamentalData.error) {
		return { error: myFundamentalData.error };
	}
	
	const mySharesData = myFundamentalData.shares_basic_bs || [];
	
	if (mySharesData.length === 0) {
		return { error: 'No shares outstanding data available' };
	}
	
	const mySharesTimestamps = mySharesData.map(r => r.reportdate);
	const mySharesValues = mySharesData.map(r => r.value);
	
	const myHistoryData = await request.history(myTickerSymbol, current.resolution);
	
	if (myHistoryData.error) {
		return { error: myHistoryData.error };
	}
	
	const mySharesLanded = land_points_onto_series(
		mySharesTimestamps,
		mySharesValues,
		myHistoryData.time,
		'le'
	);
	
	const mySharesInterpolated = interpolate_sparse_series(mySharesLanded, 'constant');
	
	const myMarketCapOnOtherTF = for_every(myHistoryData.close, mySharesInterpolated, (c, s) => {
		if (s === null || s === undefined) {
			return null;
		}
		return c * s;
	});
	
	const myMarketCapLanded = land_points_onto_series(
		myHistoryData.time,
		myMarketCapOnOtherTF,
		time,
		'ge'
	);
	
	return { marketCap: interpolate_sparse_series(myMarketCapLanded, 'constant') };
};

// Compute market cap for the current ticker using the helper function
// current.ticker automatically updates when you switch charts, so Ticker 1 will always match your chart
const myResult1 = await computeMarketCap(current.ticker);

// Paint the current ticker's market cap, or empty series if there was an error
// The line name now uses a fixed string instead of including the ticker symbol
// This ensures the line parameters remain constant across different tickers
const myLine1 = paint(
	myResult1.error ? series_of(null) : myResult1.marketCap,
	{ name: 'Market Cap (Ticker 1)', color: '#2E86DE', thickness: 3 }
);

// Compute and paint market cap for additional tickers
const myResult2 = await computeMarketCap(myTicker2);
const myResult3 = await computeMarketCap(myTicker3);
const myResult4 = await computeMarketCap(myTicker4);
const myResult5 = await computeMarketCap(myTicker5);

// Paint the second ticker's market cap, or empty series if there was an error
const myLine2 = paint(
	myResult2.error ? series_of(null) : myResult2.marketCap,
	{ name: 'Market Cap (Ticker 2)', color: '#10AC84', thickness: 3 }
);

// Paint the third ticker's market cap, or empty series if there was an error
const myLine3 = paint(
	myResult3.error ? series_of(null) : myResult3.marketCap,
	{ name: 'Market Cap (Ticker 3)', color: '#EE5A6F', thickness: 3 }
);

// Paint the fourth ticker's market cap, or empty series if there was an error
const myLine4 = paint(
	myResult4.error ? series_of(null) : myResult4.marketCap,
	{ name: 'Market Cap (Ticker 4)', color: '#F79F1F', thickness: 3 }
);

// Paint the fifth ticker's market cap, or empty series if there was an error
const myLine5 = paint(
	myResult5.error ? series_of(null) : myResult5.marketCap,
	{ name: 'Market Cap (Ticker 5)', color: '#A3CB38', thickness: 3 }
);

// Paint labels at the end of each line with improved readability
// Labels are positioned to the right and vertically spaced to prevent overlap
const myLastIndex = close.length - 1;

// Collect all valid market cap values at the last index to determine spacing
const myValidLabels = [];

if (!myResult1.error && myResult1.marketCap[myLastIndex] !== null && myResult1.marketCap[myLastIndex] !== undefined) {
	myValidLabels.push({
		line: myLine1,
		ticker: current.ticker,
		value: myResult1.marketCap[myLastIndex],
		color: '#2E86DE'
	});
}

if (!myResult2.error && myResult2.marketCap[myLastIndex] !== null && myResult2.marketCap[myLastIndex] !== undefined) {
	myValidLabels.push({
		line: myLine2,
		ticker: myTicker2,
		value: myResult2.marketCap[myLastIndex],
		color: '#10AC84'
	});
}

if (!myResult3.error && myResult3.marketCap[myLastIndex] !== null && myResult3.marketCap[myLastIndex] !== undefined) {
	myValidLabels.push({
		line: myLine3,
		ticker: myTicker3,
		value: myResult3.marketCap[myLastIndex],
		color: '#EE5A6F'
	});
}

if (!myResult4.error && myResult4.marketCap[myLastIndex] !== null && myResult4.marketCap[myLastIndex] !== undefined) {
	myValidLabels.push({
		line: myLine4,
		ticker: myTicker4,
		value: myResult4.marketCap[myLastIndex],
		color: '#F79F1F'
	});
}

if (!myResult5.error && myResult5.marketCap[myLastIndex] !== null && myResult5.marketCap[myLastIndex] !== undefined) {
	myValidLabels.push({
		line: myLine5,
		ticker: myTicker5,
		value: myResult5.marketCap[myLastIndex],
		color: '#A3CB38'
	});
}

// Sort labels by value (descending) to stack them properly
myValidLabels.sort((a, b) => b.value - a.value);

// Paint labels with smart vertical alignment based on their relative positions
const myVerticalAlignments = ['top', 'middle', 'bottom', 'top', 'middle'];

for (let i = 0; i < myValidLabels.length; i += 1) {
	const myLabel = myValidLabels[i];
	const myAlignment = myVerticalAlignments[i] || 'middle';
	
	paint_label_at_line(myLabel.line, myLastIndex, myLabel.ticker, {
		color: myLabel.color,
		vertical_align: myAlignment,
		background_color: 'rgba(0, 0, 0, 0.7)',
		border_radius: 3,
		halo: true
	});
}</code>