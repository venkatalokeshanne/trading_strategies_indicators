<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Analyst Price Targets');

input.number('offset', 30, { hidden: true });

const BUCKETS = 20;
const STRIP_WIDTH_CANDLES = 25;

const ratings = await request.analyst_ratings(constants.ticker);

const lastReportsByAnalyst = ratings.reduce((result, report) => {
	if (!parseFloat(report.pTarget)) {
		return result;
	}

	result[report.analystCompany] = report;
	return result;
}, {});

const lastReports = Object.values(lastReportsByAnalyst);

const priceTargets = lastReports.map(report => +report.pTarget);
const maxTarget = Math.max(...priceTargets);
const minTarget = Math.min(...priceTargets);

const bucketSize = (maxTarget - minTarget) / BUCKETS;

const reportsByBucket = {};

for (const report of lastReports) {
	const bucketIndex = Math.round((report.pTarget - minTarget) / bucketSize);

	if (!reportsByBucket[bucketIndex]) {
		reportsByBucket[bucketIndex] = 0
	}

	reportsByBucket[bucketIndex] += 1;
}

const maxReportsAtBucket = Math.max(...Object.values(reportsByBucket));

for (let bucketIndex = 0; bucketIndex < BUCKETS; bucketIndex += 1) {
	if (!reportsByBucket.hasOwnProperty(bucketIndex)) {
		fill(paint(series_of(null), { hidden: true }), paint(series_of(null), { hidden: true }), '#00dcff');
		continue;
	}

	const levelValueNormalized = reportsByBucket[bucketIndex] / maxReportsAtBucket;
	const progressLengthInCandles = Math.round(STRIP_WIDTH_CANDLES * levelValueNormalized);
	
	if (progressLengthInCandles === 0) {
		fill(paint(series_of(null), { hidden: true }), paint(series_of(null), { hidden: true }), '#00dcff');
		continue;
	}

	const margin = bucketSize / 20;

	const topPrice = minTarget + (bucketIndex + 1) * bucketSize;
	const top = series_of(null).slice(0, -progressLengthInCandles);
	top.push(...[...Array(progressLengthInCandles)].map(() => topPrice));

	const bottomPrice = minTarget + margin + bucketIndex * bucketSize;
	const bottom = series_of(null).slice(0, -progressLengthInCandles);
	bottom.push(...[...Array(progressLengthInCandles)].map(() => bottomPrice));

	fill(
		paint(top, { hidden: true }),
		paint(bottom, { hidden: true }),
		'#00dcff'
	);
}


const wick = series_of(null);
wick[wick.length - 1] = { high: maxTarget, low: minTarget };
paint(wick, { color: 'blue', style: 'columnrange', editorHidden: true });</code>