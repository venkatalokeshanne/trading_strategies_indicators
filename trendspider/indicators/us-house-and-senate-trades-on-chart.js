<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Congress Trades On Chart');

const party = input.select("Party", "Any", ["Any", "R", "D"]);
const side = input.select("Side", "Any", ["Any", "Buy", "Sell"]);

const binarySearch = library('binary-search-bounds');
const data = await request.congress_trading(current.ticker);

const buySignals = series_of(null);
const buys = series_of(null);

const sellSignals = series_of(null);
const sells = series_of(null);


for (const report of data) {
	const candleIndex = binarySearch.ge(time, report.timestamp);

	if (candleIndex < 0) {
		continue;
	}

	if (party != 'Any' && report.party != party) {
		continue;
	}

	if (side == "Buy" && report.transaction != 'purchase') {
		continue;
	}

	if (side == "Sell" && report.transaction == 'purchase') {
		continue;
	}
	
	if (report.transaction == 'purchase') {
		buys[candleIndex] = `[${report.party}] ${report.representative}<br/>buy`;
		buySignals[candleIndex] = true;
	}
	else {
		sells[candleIndex] = `[${report.party}]${report.representative}<br/>sell`;
		sellSignals[candleIndex] = true;
	}
}

paint(buys, { style: 'labels_below', backgroundColor: 'green', color: 'green', verticalOffset: 20 });
paint(sells, { style: 'labels_above', backgroundColor: 'red', color: 'red' });
register_signal(buySignals, 'Buys');
register_signal(sellSignals, 'Sells');</code>