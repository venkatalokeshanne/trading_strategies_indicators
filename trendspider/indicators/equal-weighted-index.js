<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Equal weighted index', 'lower');

//	type your symbols here
const SYMBOLS = input.text("Symbols", "AAPL,AMGN,AMZN,AXP,BA,CAT,CRM,CSCO,CVX,DIS,GS,HD,HON,IBM,JNJ,JPM,KO,MCD,MMM,MRK,MSFT,NKE,NVDA,PG,SHW,TRV,UNH,V,VZ,WMT", { hide_in_legend: true }).
	split(',').
	map(value => value.trim());

//	do not increase these 2 numbers, it won't work
const BATCH_SIZE_SYMBOLS = 9;
const MAX_HISTORY_CALLS = 6;

const totalSymbols = SYMBOLS.length;
assert(SYMBOLS.length < BATCH_SIZE_SYMBOLS * MAX_HISTORY_CALLS, `Too many symbols requested`);

const getSymbolInputs = batchIndex => SYMBOLS.slice(batchIndex * BATCH_SIZE_SYMBOLS, batchIndex * BATCH_SIZE_SYMBOLS + BATCH_SIZE_SYMBOLS);

const fetchBatchData = async symbols => {
	const symbolString = symbols.join(' + ');
	const data = await request.history(`=${symbolString}`, current.resolution);
	assert(!data.error, `Error fetching data: ${data.error}`);
	
	return interpolate_sparse_series(land_points_onto_series(data.time, data.close, time), 'constant');
};

const numberOfBatches = Math.ceil(totalSymbols / BATCH_SIZE_SYMBOLS);
const batchesData = [];

for (let batchIndex = 0; batchIndex < numberOfBatches; batchIndex += 1) {
	const symbols = getSymbolInputs(batchIndex);
	const batchData = await fetchBatchData(symbols);
	batchesData.push(batchData);
}

const indexValues = close.map((dummy, candleIndex) => {
	const allValueAtThatIndex = batchesData.reduce((acc, partialSeries) => acc + partialSeries[candleIndex], 0);
	return allValueAtThatIndex;
});

paint(indexValues, { color: 'grey' });
</code>