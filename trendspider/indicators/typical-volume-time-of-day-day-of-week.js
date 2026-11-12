<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volume by time of a day + day of week', 'lower');

if (isNaN(constants.resolution)) {
	throw Error('This indicator can only work on intraday charts');
}

const volumeByTime = {};
const lookbackPeriod = input('Lookback', 3, { min: 1, max: 10 });

const averageVolumes = for_every(volume, time, (v, t) => {
	const timeOfDay = time_of(t);
	const timeHash = `${timeOfDay.dayOfWeek}:${timeOfDay.hours}:${timeOfDay.minutes}`;

	if (!volumeByTime[timeHash]) {
		volumeByTime[timeHash] = [];
	}

	const avgVolume = volumeByTime[timeHash].
		slice(-lookbackPeriod).
		reduce((result, value) => result + value, 0) / lookbackPeriod;

	volumeByTime[timeHash].push(v); 

	return volumeByTime[timeHash].length >= lookbackPeriod + 1
		? avgVolume
		: null;
});

const volumeColors = for_every(close, open, averageVolumes, volume, (c, o, avg, vol) => {
	if (vol > avg) {
		return 'orange';
	}
	
	return '#999';
});

fill(
	paint(averageVolumes, { style: 'line', hidden: true }),
	paint(series_of(0), { style: 'line', hidden: true }),
	'#ffffff',
	0.2
);

paint(volume, { style: 'histogram', color: volumeColors });</code>