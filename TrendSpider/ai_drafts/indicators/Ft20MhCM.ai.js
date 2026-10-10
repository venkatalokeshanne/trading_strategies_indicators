// This indicator recreates the TradingView "Volume Ranking by Exchange"
// table using TrendSpider's overlay table feature. It fetches volume
// (and optionally USD-normalized volume) for up to 8 user-defined
// exchange/suffix combinations and ranks them.
//
// NOTE: Pine's `request.security()` with `ignore_invalid_symbol=true`
// has no exact equivalent here. We use `request.history()` for each
// ticker and take the last available candle's close/volume. If a
// ticker is invalid, has no data, or the request throws/rejects, we
// treat its volume as 0 (like Pine's `nz()` fallback). The previous
// version let a rejected request.history() promise bubble up as an
// unhandled error ("history: [object Object]"); this version catches
// per-ticker failures individually so one bad symbol never crashes
// the whole indicator.
describe_indicator('Volume Ranking by Exchange', 'price');

const myGeneralTab = input.tab('General');
const myAutoTicker = myGeneralTab.boolean('Use Chart Base Currency', true);
const myNormalizeUSD = myGeneralTab.boolean('Normalize in USD (volume x price)', true);
const myShowBar = myGeneralTab.boolean('Show Proportion Bar', true);
const myTextSize = myGeneralTab.select('Text Size', 'Small', ['Tiny', 'Small', 'Normal', 'Large']);
const myTablePosition = myGeneralTab.select('Position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);

const myExchangesTab = input.tab('Exchanges');

const myRow1 = myExchangesTab.row();
const myExchange1 = myRow1.text('Exchange 1', 'BINANCE');
const mySuffix1 = myRow1.text('Suffix 1', 'USDT.P');

const myRow2 = myExchangesTab.row();
const myExchange2 = myRow2.text('Exchange 2', 'BYBIT');
const mySuffix2 = myRow2.text('Suffix 2', 'USDT.P');

const myRow3 = myExchangesTab.row();
const myExchange3 = myRow3.text('Exchange 3', 'OKX');
const mySuffix3 = myRow3.text('Suffix 3', 'USDT.P');

const myRow4 = myExchangesTab.row();
const myExchange4 = myRow4.text('Exchange 4', 'BITGET');
const mySuffix4 = myRow4.text('Suffix 4', 'USDT.P');

const myRow5 = myExchangesTab.row();
const myExchange5 = myRow5.text('Exchange 5', 'MEXC');
const mySuffix5 = myRow5.text('Suffix 5', 'USDT.P');

const myRow6 = myExchangesTab.row();
const myExchange6 = myRow6.text('Exchange 6', 'GATEIO');
const mySuffix6 = myRow6.text('Suffix 6', 'USDT.P');

const myRow7 = myExchangesTab.row();
const myExchange7 = myRow7.text('Exchange 7', 'BINGX');
const mySuffix7 = myRow7.text('Suffix 7', 'USDT.P');

const myRow8 = myExchangesTab.row();
const myExchange8 = myRow8.text('Exchange 8', 'COINBASE');
const mySuffix8 = myRow8.text('Suffix 8', 'USD');

const myExchangeList = [
	{ exchange: myExchange1, suffix: mySuffix1 },
	{ exchange: myExchange2, suffix: mySuffix2 },
	{ exchange: myExchange3, suffix: mySuffix3 },
	{ exchange: myExchange4, suffix: mySuffix4 },
	{ exchange: myExchange5, suffix: mySuffix5 },
	{ exchange: myExchange6, suffix: mySuffix6 },
	{ exchange: myExchange7, suffix: mySuffix7 },
	{ exchange: myExchange8, suffix: mySuffix8 }
];

// Determine the base currency, used when "Use Chart Base Currency" is on.
// current.assets_involved[0] is the closest equivalent to syminfo.basecurrency.
const myBaseCurrency = (current.assets_involved && current.assets_involved[0]) || '';

function myBuildTicker(myExchangeEntry) {
	if (myAutoTicker) {
		return `${myExchangeEntry.exchange}:${myBaseCurrency}${myExchangeEntry.suffix}`;
	}
	return `${myExchangeEntry.exchange}:${myExchangeEntry.suffix}`;
}

const myTickers = myExchangeList.map(myBuildTicker);

// Each request.history() call is caught individually. Some tickers may
// not exist (wrong exchange/suffix combo) and request.history() can
// reject the promise rather than resolving with { error }; without a
// per-call catch, that rejection propagated up as an unhandled error
// ("history: [object Object]") and crashed the whole script.
const myHistoryResults = await Promise.all(
	myTickers.map(_myTicker =>
		request.history(_myTicker, current.resolution).catch(_myErr => ({ error: _myErr }))
	)
);

// Format numbers the same way Pine's f_fmt() does: B / M / K suffixes.
function myFormatVolume(myValue) {
	const myAbs = Math.abs(myValue);
	if (myAbs >= 1e9) return (myValue / 1e9).toFixed(2) + 'B';
	if (myAbs >= 1e6) return (myValue / 1e6).toFixed(2) + 'M';
	if (myAbs >= 1e3) return (myValue / 1e3).toFixed(1) + 'K';
	return myValue.toFixed(1);
}

const myVolumes = myHistoryResults.map(_myData => {
	if (!_myData || _myData.error || !_myData.close || _myData.close.length === 0) {
		return 0;
	}

	const myLastIndex = _myData.close.length - 1;
	const myLastVolume = _myData.volume ? _myData.volume[myLastIndex] : 0;
	const myLastClose = _myData.close[myLastIndex];
	const myRawVolume = (myLastVolume === null || myLastVolume === undefined) ? 0 : myLastVolume;

	return myNormalizeUSD ? myRawVolume * (myLastClose || 0) : myRawVolume;
});

const myTotalVolume = myVolumes.reduce((_myAcc, _myVal) => _myAcc + _myVal, 0);

const myRankedEntries = myExchangeList.map((_myEntry, _myIndex) => ({
	name: _myEntry.exchange,
	volume: myVolumes[_myIndex]
})).sort((_myA, _myB) => _myB.volume - _myA.volume);

const mySizeMap = { Tiny: '10px', Small: '12px', Normal: '14px', Large: '16px' };
const myFontSize = mySizeMap[myTextSize] || '12px';
const myRowColors = ['#00E676', '#B2FF59', '#FFFFFF', '#FFFFFF', '#CCCCCC', '#CCCCCC', '#CCCCCC', '#CCCCCC'];

const myTableRows = [{
	cells: [
		{ text: '#', color: 'gray' },
		{ text: 'Exchange', color: 'gray' },
		{ text: myNormalizeUSD ? 'Vol (USD)' : 'Vol', color: 'gray' },
		{ text: myShowBar ? 'Share' : '%', color: 'gray' }
	]
}];

myRankedEntries.forEach((_myEntry, _myIndex) => {
	const myShare = myTotalVolume > 0 ? (_myEntry.volume / myTotalVolume * 100) : 0;
	const myBarLength = Math.max(1, Math.round(myShare / 4));
	const myBarText = myShowBar ? ' ' + '|'.repeat(myBarLength) : '';
	const myColor = myRowColors[_myIndex] || '#CCCCCC';

	myTableRows.push({
		cells: [
			{ text: String(_myIndex + 1), color: 'gray' },
			{ text: _myEntry.name, color: myColor },
			{ text: myFormatVolume(_myEntry.volume), color: myColor },
			{ text: myShare.toFixed(1) + '%' + myBarText, color: myColor }
		]
	});
});

myTableRows.push({
	cells: [
		{ text: '' },
		{ text: 'TOTAL', color: 'white' },
		{ text: myFormatVolume(myTotalVolume), color: 'white' },
		{ text: '100%', color: 'gray' }
	]
});

paint_overlay('VolumeRankingTable', { position: myTablePosition }, {
	rows: myTableRows,
	fontSize: myFontSize
});

// Scanning/Strategy signal: since the original script has no trading
// logic (it's purely a display table), the closest meaningful signal
// is "the top-ranked exchange currently holds more than 50% of total
// tracked volume", exposed so it can be used in Scanners/Alerts.
const myTopShare = myTotalVolume > 0 ? (myRankedEntries[0].volume / myTotalVolume * 100) : 0;
const myDominanceSignal = series_of(myTopShare > 50);
register_signal(myDominanceSignal, 'Top Exchange Dominance Above 50 Percent');