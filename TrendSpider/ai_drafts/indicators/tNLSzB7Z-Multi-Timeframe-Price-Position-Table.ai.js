describe_indicator('Multi Timeframe Price Position Table', 'price');

// ============================================================
// INPUTS
// ============================================================
const myTablePosition = input.select('Table Position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left', 'middle_right']);
const myShowCurrentPriceRow = input.boolean('Show Current Price Row', true);

// ============================================================
// FETCH OTHER TIME FRAMES DATA
// ============================================================
const [myDailyData, myWeeklyData, myMonthlyData, myH1Data, myM30Data, myM15Data] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'W'),
	request.history(current.ticker, 'M'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '30'),
	request.history(current.ticker, '15')
]);

assert(!myDailyData.error, 'Error fetching Daily data: ' + myDailyData.error);
assert(!myWeeklyData.error, 'Error fetching Weekly data: ' + myWeeklyData.error);
assert(!myMonthlyData.error, 'Error fetching Monthly data: ' + myMonthlyData.error);
assert(!myH1Data.error, 'Error fetching 1H data: ' + myH1Data.error);
assert(!myM30Data.error, 'Error fetching 30M data: ' + myM30Data.error);
assert(!myM15Data.error, 'Error fetching 15M data: ' + myM15Data.error);

// Builds a "previous completed bar close" series, shifted by 1,
// to mimic Pine's close[1] on each requested time frame.
function myPreviousCloseLanded(_data) {
	const myShiftedClose = shift(_data.close, 1);
	const myLanded = land_points_onto_series(_data.time, myShiftedClose, time, 'le');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myDayClose = myPreviousCloseLanded(myDailyData);
const myWeekClose = myPreviousCloseLanded(myWeeklyData);
const myMonthClose = myPreviousCloseLanded(myMonthlyData);
const myH1Close = myPreviousCloseLanded(myH1Data);
const myM30Close = myPreviousCloseLanded(myM30Data);
const myM15Close = myPreviousCloseLanded(myM15Data);

const myCurrentPrice = close;

// ============================================================
// SIGNALS (for scanners / alerts / strategies)
// ============================================================
register_signal(for_every(myCurrentPrice, myDayClose, (_c, _r) => _c > _r), 'Above Daily Close');
register_signal(for_every(myCurrentPrice, myDayClose, (_c, _r) => _c < _r), 'Below Daily Close');
register_signal(for_every(myCurrentPrice, myWeekClose, (_c, _r) => _c > _r), 'Above Weekly Close');
register_signal(for_every(myCurrentPrice, myWeekClose, (_c, _r) => _c < _r), 'Below Weekly Close');
register_signal(for_every(myCurrentPrice, myMonthClose, (_c, _r) => _c > _r), 'Above Monthly Close');
register_signal(for_every(myCurrentPrice, myMonthClose, (_c, _r) => _c < _r), 'Below Monthly Close');
register_signal(for_every(myCurrentPrice, myH1Close, (_c, _r) => _c > _r), 'Above 1H Close');
register_signal(for_every(myCurrentPrice, myH1Close, (_c, _r) => _c < _r), 'Below 1H Close');
register_signal(for_every(myCurrentPrice, myM30Close, (_c, _r) => _c > _r), 'Above 30M Close');
register_signal(for_every(myCurrentPrice, myM30Close, (_c, _r) => _c < _r), 'Below 30M Close');
register_signal(for_every(myCurrentPrice, myM15Close, (_c, _r) => _c > _r), 'Above 15M Close');
register_signal(for_every(myCurrentPrice, myM15Close, (_c, _r) => _c < _r), 'Below 15M Close');

// ============================================================
// TABLE
// ============================================================
const myLastIndex = myCurrentPrice.length - 1;
const myCurPriceValue = myCurrentPrice[myLastIndex];

function myRowDefinition(_label, _refCloseValue) {
	const myIsAbove = myCurPriceValue > _refCloseValue;
	const myStatusText = myIsAbove ? 'Above' : 'Below';
	const mySignalText = myIsAbove ? 'BUY' : 'SELL';
	const myRowBg = myIsAbove ? 'rgba(0,128,0,0.3)' : 'rgba(255,0,0,0.3)';
	const mySigBg = myIsAbove ? 'rgba(0,128,0,0.85)' : 'rgba(255,0,0,0.85)';

	return {
		cells: [
			{ text: _label, color: 'white', background_color: 'rgba(0,0,0,0.6)' },
			{ text: String(_refCloseValue), color: 'white', background_color: 'rgba(0,0,0,0.6)' },
			{ text: myStatusText, color: 'white', background_color: myRowBg },
			{ text: mySignalText, color: 'white', background_color: mySigBg }
		]
	};
}

const myHeaderRow = {
	cells: [
		{ text: 'Timeframe', color: 'white', background_color: 'rgba(0,0,255,0.7)' },
		{ text: 'Ref Close', color: 'white', background_color: 'rgba(0,0,255,0.7)' },
		{ text: 'Status', color: 'white', background_color: 'rgba(0,0,255,0.7)' },
		{ text: 'Signal', color: 'white', background_color: 'rgba(0,0,255,0.7)' }
	]
};

const myCurrentPriceRow = {
	cells: [
		{ text: 'Current Price', color: 'white', background_color: 'rgba(128,128,128,0.6)' },
		{ text: String(myCurPriceValue), color: 'white', background_color: 'rgba(128,128,128,0.6)' },
		{ text: '-', color: 'white', background_color: 'rgba(128,128,128,0.6)' },
		{ text: '-', color: 'white', background_color: 'rgba(128,128,128,0.6)' }
	]
};

const myTableRows = [myHeaderRow];

// Keep the row count constant regardless of the input value,
// so paint_overlay() always receives the same shape of content.
myTableRows.push(myShowCurrentPriceRow ? myCurrentPriceRow : { cells: [] });

myTableRows.push(myRowDefinition('Last Day Close', myDayClose[myLastIndex]));
myTableRows.push(myRowDefinition('Last Week Close', myWeekClose[myLastIndex]));
myTableRows.push(myRowDefinition('Last Month Close', myMonthClose[myLastIndex]));
myTableRows.push(myRowDefinition('Last 1H Close', myH1Close[myLastIndex]));
myTableRows.push(myRowDefinition('Last 30M Close', myM30Close[myLastIndex]));
myTableRows.push(myRowDefinition('Last 15M Close', myM15Close[myLastIndex]));

paint_overlay('PricePositionTable', { position: myTablePosition }, {
	rows: myTableRows
});