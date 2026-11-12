<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('News per day');

/*
	This script paints the amount of News records per day as a label above candles.
	Big news days (days which had more-than-average amount of news records) have labels
	painted in a different color. 
*/

if (constants.resolution != 'D') {
	throw Error('This script works on Daily time frame only');
}

const moment = library('moment-timezone');

const BIG_DAY_RECORDS_MULTIPLIER = 2;

const dayAtTimestamp = timestamp => moment(timestamp * 1e3).format('DD MMM YYYY');

const news = await request.news(constants.ticker);
const newsByDay = {};

for (const newsRecord of news) {
	const day = dayAtTimestamp(newsRecord.timestamp);

	if (!newsByDay[day]) {
		newsByDay[day] = 0;
	}

	newsByDay[day] += 1;
}


const averageNewsPerDay = Object.values(newsByDay).reduce((result, records) => result + records, 0) / Object.values(newsByDay).length;
const bigDayMinNews = BIG_DAY_RECORDS_MULTIPLIER * averageNewsPerDay;

const bigNewsDays = for_every(time, timestamp => {
	const newsThatDay = newsByDay[dayAtTimestamp(timestamp)];

	if (newsThatDay > bigDayMinNews) {
		return newsThatDay;
	}
});

const normalNewsDays = for_every(time, timestamp => {
	const newsThatDay = newsByDay[dayAtTimestamp(timestamp)];

	if (newsThatDay <= bigDayMinNews) {
		return newsThatDay;
	}
});

paint(bigNewsDays, { style: 'labels_above', backgroundColor: 'blue', color: 'blue'});
paint(normalNewsDays, { style: 'labels_above' });</code>