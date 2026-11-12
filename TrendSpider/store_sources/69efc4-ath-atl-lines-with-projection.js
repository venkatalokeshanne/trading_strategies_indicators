<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ATH/ATL Levels');

const moment = library('moment-timezone');

// Fetch monthly data instead of daily
const monthlyData = await request.history(current.ticker, 'M');
assert(!monthlyData.error, `Error fetching history: "${monthlyData.error}"`);

let athValue = null;
let athIndex = null;
let atlValue = null;
let atlIndex = null;

for (let candleIndex = 0; candleIndex < monthlyData.high.length; candleIndex += 1) {
	if (athValue === null || monthlyData.high[candleIndex] > athValue) {
		athValue = monthlyData.high[candleIndex];
		athIndex = candleIndex;
	}
	if (atlValue === null || monthlyData.low[candleIndex] < atlValue) {
		atlValue = monthlyData.low[candleIndex];
		atlIndex = candleIndex;
	}
}

// Corrected formatTimeDifference function to show months ago or "less than a month ago"
const formatTimeDifference = timestampSeconds => {
	const now = moment(Date.now());
	const past = moment(timestampSeconds * 1000);
	const months = now.diff(past, 'months');
	
	if (months < 1) {
		return 'less than a month ago';
	}
	
	return `${months} months ago`;
};

const athTimestamp = monthlyData.time[athIndex];
const atlTimestamp = monthlyData.time[atlIndex];
const athTimeAgo = formatTimeDifference(athTimestamp);
const atlTimeAgo = formatTimeDifference(atlTimestamp);

const athLine = paint(horizontal_line(athValue), { name: 'ATH', style: 'dotted', color: 'green', thickness: 1, ignoreWhenScaling: 1 });
const atlLine = paint(horizontal_line(atlValue), { name: 'ATL', style: 'dotted', color: 'red', thickness: 1, ignoreWhenScaling: 1 });

const PROJECTION_LENGTH = 50;
const athProjectionValues = [];
const atlProjectionValues = [];
const currentCloseProjection = [];
const currentClose = close[close.length - 1];

for (let i = 0; i < PROJECTION_LENGTH; i += 1) {
	athProjectionValues.push(athValue);
	atlProjectionValues.push(atlValue);
	currentCloseProjection.push(currentClose);
}

const athProjection = paint_projection(athProjectionValues, { name: 'ATH Projection', style: 'dotted', color: 'green', thickness: 1, ignoreWhenScaling: 1 });
const atlProjection = paint_projection(atlProjectionValues, { name: 'ATL Projection', style: 'dotted', color: 'red', thickness: 1, ignoreWhenScaling: 1 });
const currentCloseProjectionLine = paint_projection(currentCloseProjection, { name: 'Last', style: 'dotted', color: 'blue', thickness: 1 });

paint_label_at_line(
	athProjection,
	PROJECTION_LENGTH - 1,
	`ATH $${athValue.toFixed(2)} (${athTimeAgo})`,
	{ color: 'white', background_color: 'green', border_radius: 3 }
);

paint_label_at_line(
	atlProjection,
	PROJECTION_LENGTH - 1,
	`ATL $${atlValue.toFixed(2)} (${atlTimeAgo})`,
	{ color: 'white', background_color: 'red', border_radius: 3 }
);

const percentFromATH = ((currentClose - athValue) / athValue * 100).toFixed(1);
const percentFromATL = ((currentClose - atlValue) / atlValue * 100).toFixed(1);
const athLabel = percentFromATH >= 0 ? `+${percentFromATH}%` : `${percentFromATH}%`;
const atlLabel = percentFromATL >= 0 ? `+${percentFromATL}%` : `${percentFromATL}%`;

paint_label_at_line(
	currentCloseProjectionLine,
	PROJECTION_LENGTH - 1,
	`${athLabel} ATH, ${atlLabel} ATL`,
	{ color: 'white', background_color: 'blue', border_radius: 3 }
);
</code>