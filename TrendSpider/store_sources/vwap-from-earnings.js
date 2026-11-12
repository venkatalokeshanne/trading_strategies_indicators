<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('VWAP from Earnings', { warmup: 1000 });
const binarySearch = library('binary-search-bounds');

const earnings = await request.earnings(current.ticker);
const result = series_of(null);

const earningsDatesLanded = earnings.map(report => binarySearch.le(time, report.timestamp)).filter(index => index >= 0);

for (let reportIndex = 0; reportIndex < earningsDatesLanded.length; reportIndex += 1) {	
	const fromCandle = earningsDatesLanded[reportIndex];
	const toCandle = earningsDatesLanded[reportIndex + 1] || candles.length - 1;
	const vwapComputed = vwap(fromCandle, toCandle);

	for (let candleIndex = fromCandle; candleIndex <= toCandle; candleIndex += 1) {
		result[candleIndex] = vwapComputed[candleIndex];
	}
}


paint(result, { color: 'grey', name: 'AVWAP/Earnings' });</code>