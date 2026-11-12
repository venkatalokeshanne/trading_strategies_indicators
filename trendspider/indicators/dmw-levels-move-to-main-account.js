<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('DMW Levels');

const showMonthly = input.boolean('Monthly', true);
const showWeekly = input.boolean('Weekly', true);
const showDaily = input.boolean('Daily', true);
const showPremarket = input.boolean('Pre.M', true);
const labelColor = input.color('Labels', 'blue');

const M_TITLE = 'M.Close';
const W_TITLE = 'W.Close';
const D_TITLE = 'D.Close';
const EXT_HIGH_TITLE = 'Pre.High';
const EXT_LOW_TITLE = 'Pre.Low';

if (showMonthly) {
	const monthly = await request.history(current.ticker, "M");
	lineWithLabel(
		monthly.close[monthly.close.length - 2],
		monthly.time[monthly.time.length - 1],
		M_TITLE
	);
}
else {
	paint(series_of(null), { name: M_TITLE  });
}

if (showWeekly) {
	const weekly = await request.history(current.ticker, "W");
	
	lineWithLabel(
		weekly.close[weekly.close.length - 2],
		weekly.time[weekly.time.length - 1],
		W_TITLE
	);
}
else {
	paint(series_of(null), { name: W_TITLE  });
}


if (showDaily) {
	const daily = await request.history(current.ticker, "D");
	
	lineWithLabel(
		daily.close[daily.close.length - 2],
		daily.time[daily.time.length - 1],
		D_TITLE
	);
}
else {
	paint(series_of(null), { name: D_TITLE  });
}


if (showPremarket) {
	const intradayExt = await request.history(current.ticker, "30", { ext_session: true });

	const lastKnownExtSessionCandles = [];
	let lastKnownMarkerCandleTimestamp = null;
	let anyExtSessionCandleFaced = false;

	const extSession = current.ext_session;
	const marketSession = current.session;

	for (let index = 0; index < intradayExt.time.length; index += 1) {
		const indexNormalized = intradayExt.time.length - 1 - index;

		const candleTime = intradayExt.time[indexNormalized];
		const timeParsed = time_of(candleTime);

		const isExtSession = 
			(timeParsed.hours > extSession.start.hours || (timeParsed.hours == extSession.start.hours && timeParsed.minutes >= extSession.start.minutes)) &&
			(timeParsed.hours < marketSession.start.hours || (timeParsed.hours == marketSession.start.hours && timeParsed.minutes < marketSession.start.minutes));

		if (isExtSession) {
			anyExtSessionCandleFaced = true;

			lastKnownExtSessionCandles.push({
				high: intradayExt.high[indexNormalized],
				low: intradayExt.low[indexNormalized],
				time: candleTime
			});
		}
		else {
			if (anyExtSessionCandleFaced) {
				break;
			}

			lastKnownMarkerCandleTimestamp = intradayExt.time[indexNormalized];
		}
	}
	
	const premarketHigh = Math.max(...lastKnownExtSessionCandles.map(candle => candle.high));
	const premarketLow = Math.min(...lastKnownExtSessionCandles.map(candle => candle.low));

	fill(
		lineWithLabel(premarketHigh, lastKnownMarkerCandleTimestamp, EXT_HIGH_TITLE, "eq"),
		lineWithLabel(premarketLow, lastKnownMarkerCandleTimestamp, EXT_LOW_TITLE, "eq"),
		'orange'
	);
}
else {
	paint(series_of(null), { name: D_TITLE  });
}


function lineWithLabel(level, dataPointTime, label, landingMechanic = "lt") {
	const seriesLanded = dataPointTime > market.time[0]
		? interpolate_sparse_series(land_points_onto_series([dataPointTime], [level], market.time, landingMechanic), "constant")
		: series_of(level);

	const series = [
		...seriesLanded.slice(0, -1),
		{ y: level, dataLabels: { enabled: true, color: labelColor, format: label }}
	];

	return paint(series, { name: label, color: 'white', ignoreWhenScaling: true });
}</code>