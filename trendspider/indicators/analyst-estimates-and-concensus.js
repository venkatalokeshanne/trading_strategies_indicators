<code x-ref="code" class="hljs" data-clipboard-text>/*
	This indicator paints distribtuion of Analysts rankings for a given market
	over time. There are 3 areas on the distribution chart: green ("Buy" ranks),
	red (for "Sell") and gray ("Hold"). At every point in time, you can see what the
	prevailing ranking is.

	In case if you're seeing dark red area, this means that "Sell" is the prevailing rank
	at a given time. Dark green areas stand for "Buys prevailing" and no dark areas means
	that neither Buy nor Sell prevail.  
*/

describe_indicator('Analyst Estimates: Analyst Consensus', 'lower');

const COLOR_BUY_DOMINATING = '#22ab94';
const COLOR_BUY = '#a0dcd2';
const COLOR_SELL_DOMINATING = '#e31d1d';
const COLOR_SELL = '#d8a2a2';
const COLOR_HOLD = '#a9a9a9';


const ratingSeries = {
	buy: series_of(0),
	sell: series_of(0),
	hold: series_of(0)
}

const ratings = await request.analyst_ratings(constants.ticker);

const ratingsLanded = land_points_onto_series(
	ratings.map(item => item.timestamp),
	ratings.map(rating => [rating]),
	time,
	'ge',
	(existingRatings, newRating) => [...existingRatings, newRating[0]]
);

const analystsAlreadyPainted = [];

for (let candleIndex = 1; candleIndex < close.length; candleIndex++) {
	ratingSeries.buy[candleIndex] = ratingSeries.buy[candleIndex - 1];
	ratingSeries.sell[candleIndex] = ratingSeries.sell[candleIndex - 1];
	ratingSeries.hold[candleIndex] = ratingSeries.hold[candleIndex - 1];

	const ratings = ratingsLanded[candleIndex] || [];
	
	ratings.forEach(rating => {
		ratingSeries[rating.ratingCurrent][candleIndex]++;

		//	if a given analyst's previos rating was never painted on this chart
		//	then decreasing the previous rank results in a confusing picture
		if (rating.ratingPrior && analystsAlreadyPainted.includes(rating.analystCompany)) {
			ratingSeries[rating.ratingPrior][candleIndex]--;
		}

		analystsAlreadyPainted.push(rating.analystCompany);
	});
};


const buyColors = for_every(ratingSeries.buy, ratingSeries.sell, (buys, sells) => buys > sells ? COLOR_BUY_DOMINATING : COLOR_BUY);
paint(ratingSeries.buy, { style: 'stacked_histogram', name: 'Buy', stacking: 'percent', padding: 0, color: buyColors });

const sellColors = for_every(ratingSeries.buy, ratingSeries.sell, (buys, sells) => sells > buys ? COLOR_SELL_DOMINATING : COLOR_SELL);
paint(ratingSeries.sell, { style: 'stacked_histogram', name: 'Sell', stacking: 'percent', padding: 0, color: sellColors });

paint(ratingSeries.hold, { style: 'stacked_histogram', name: 'Hold', color: COLOR_HOLD, stacking: 'percent', padding: 0 });</code>