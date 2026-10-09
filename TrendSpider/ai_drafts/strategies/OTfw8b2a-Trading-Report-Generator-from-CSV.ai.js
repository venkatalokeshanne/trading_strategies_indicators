// This indicator approximates the Pine Script "Trading Report Generator from CSV"
// strategy. The Custom JS API has no strategy engine, no runtime.error, and no
// built-in CSV text-area input matching Pine's input.text_area. We reproduce the
// closest achievable behavior: parse the CSV of trades, match each trade's
// closing time to the chart candle it belongs to, and mark Buy/Sell signals
// on those candles (as labels and as register_signal() outputs usable in
// Scanners/Alerts/Strategy Tester). Actual order execution, position sizing,
// margin and P&L reporting from Pine's `strategy.*` are NOT available here.
describe_indicator('Trading Report From CSV', 'price');

const myCsvInput = input.text(
	'Transactions CSV',
	'Symbol,Side,Qty,Fill Price,Closing Time\n' +
	'CRYPTO:BTCUSD,Buy,200,107900,2025-07-08 01:59:29\n' +
	'CRYPTO:BTCUSD,Sell,100,123000,2025-07-14 07:00:00\n' +
	'CRYPTO:BTCUSD,Sell,100,115000,2025-07-25 07:00:00',
	{ hide_in_legend: true }
);

const mySupportedHeader1 = 'Symbol,Side,Qty,Fill Price,Commission,Closing Time';
const mySupportedHeader2 = 'Symbol,Side,Qty,Fill Price,Closing Time';

// Parses "yyyy-MM-DD hh:mm:ss" into a Unix timestamp (seconds), assuming UTC.
function myParseTimestamp(_timeStampText) {
	const myParts = _timeStampText.trim().split(' ');
	assert(myParts.length === 2, `Bad timestamp format: "${_timeStampText}"`);

	const myDateParts = myParts[0].split('-').map(Number);
	const myTimeParts = myParts[1].split(':').map(Number);

	const myDate = Date.UTC(
		myDateParts[0],
		myDateParts[1] - 1,
		myDateParts[2],
		myTimeParts[0],
		myTimeParts[1],
		myTimeParts[2]
	);

	return myDate / 1000;
}

function myParseTrades(_csvText) {
	const myResult = [];
	const myLines = _csvText.split('\n').filter(_l => _l.trim().length > 0);

	if (myLines.length === 0) {
		return myResult;
	}

	const myHeader = myLines[0].trim();
	const myIsHeader1 = myHeader === mySupportedHeader1;
	const myIsHeader2 = myHeader === mySupportedHeader2;

	if (!myIsHeader1 && !myIsHeader2) {
		throw `Unsupported CSV format. Expecting columns: "${mySupportedHeader1}" or "${mySupportedHeader2}". Found "${myHeader}"`;
	}

	const myMinCount = myIsHeader1 ? 6 : 5;

	for (let myLineIndex = 1; myLineIndex < myLines.length; myLineIndex += 1) {
		const myElems = myLines[myLineIndex].trim().split(',');
		const myTicker = myElems[0];

		if (myTicker === '$CASH') {
			continue;
		}

		assert(myElems.length >= myMinCount, `Bad line ${myLineIndex + 1} in trades CSV`);

		const myQty = Number(myElems[2]);
		const myPrice = Number(myElems[3]);
		const myTimeText = myIsHeader1 ? myElems[5] : myElems[4];
		const myExecTime = myParseTimestamp(myTimeText);
		const myIsBuy = myElems[1].toLowerCase() === 'buy';

		myResult.push({
			tickerId: myTicker,
			isBuy: myIsBuy,
			qty: myQty,
			price: myPrice,
			execTime: myExecTime
		});
	}

	return myResult;
}

// Matches the trade ticker against the current chart ticker. We compare the
// part after the exchange prefix (e.g. "CRYPTO:BTCUSD" -> "BTCUSD"), since
// Pine's ticker.standard() normalization can't be fully reproduced here.
function myNormalizeTicker(_tickerText) {
	const myParts = _tickerText.split(':');
	return (myParts.length > 1 ? myParts[1] : myParts[0]).toUpperCase();
}

let myParsedTrades = [];
let myParseErrorText = null;

try {
	myParsedTrades = myParseTrades(myCsvInput);
} catch (myErr) {
	myParseErrorText = String(myErr);
	myParsedTrades = [];
}

const myCurrentTickerNormalized = myNormalizeTicker(current.ticker);
const myMatchingTrades = myParsedTrades.filter(_t => myNormalizeTicker(_t.tickerId) === myCurrentTickerNormalized);

// Lands each trade onto the candle whose time window contains its execTime.
const myBuyMarks = series_of(null);
const mySellMarks = series_of(null);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

for (const myTrade of myMatchingTrades) {
	let myCandleIndex = -1;

	for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
		const myCandleStart = time[myIndex];
		const myCandleEnd = myIndex + 1 < time.length ? time[myIndex + 1] : Infinity;

		if (myTrade.execTime >= myCandleStart && myTrade.execTime < myCandleEnd) {
			myCandleIndex = myIndex;
			break;
		}
	}

	if (myCandleIndex >= 0) {
		if (myTrade.isBuy) {
			myBuyMarks[myCandleIndex] = low[myCandleIndex];
			myBuySignal[myCandleIndex] = true;
		}
		else {
			mySellMarks[myCandleIndex] = high[myCandleIndex];
			mySellSignal[myCandleIndex] = true;
		}
	}
}

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#EF5350' });

register_signal(myBuySignal, 'Buy Trade');
register_signal(mySellSignal, 'Sell Trade');