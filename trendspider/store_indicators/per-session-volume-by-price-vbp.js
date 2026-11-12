<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Per-session VbP, combined TF', { warmup: 200 });

const COLUMNS_NUMBER = 20;
const VALUE_AREA_MIN_ACCUMULATED_VOLUME = 0.7;
const NORMAL_COLUMN_COLOR = '#999';

if (isNaN(constants.resolution)) {
	throw Error("Only supported for intraday time frames");
}

const binarySearch = library('binary-search-bounds');

const days = identifyDays();
const resolutionDivisor = constants.resolution < 15
	? 3
	: 2;

const lowerTimeFrameData = await request.history(constants.ticker, Math.min(Math.round(constants.resolution / resolutionDivisor), 4));

const ranges = [...Array(COLUMNS_NUMBER)].map(() => createVerticalRange(0, 0));
const poc = series_of(null);
const valueAreaTop = series_of(null);
const valueAreaBottom = series_of(null);

for (const day of days) {
	const highOfDay = Math.max(...high.slice(day.from, day.to));
	const lowOfDay = Math.min(...low.slice(day.from, day.to));

	const stripHeight = (highOfDay - lowOfDay) / COLUMNS_NUMBER;

	ranges.forEach((range, rangeIndex) => range.setCurrentPriceRange(
		lowOfDay + stripHeight * rangeIndex,
		lowOfDay + stripHeight * (rangeIndex + 1))
	);

	const dayStartTimestamp = time[day.from];
	const useLowTimeFrameData = lowerTimeFrameData && dayStartTimestamp > lowerTimeFrameData.time[0];

	const levels = useLowTimeFrameData
		? computeVbpFromLowerTimeFrameData(ranges, day, highOfDay, lowOfDay)
		: computeVbpFromSameTimeFrameData(ranges, day, highOfDay, lowOfDay);

	if (levels.length === 0) {
		continue;
	}

	const maxVolume = Math.max(...levels.map(({ volume }) => volume));
	let pointofControl
	levels.forEach(({ range, volume }, rangeIndex) => {
		range.setCurrentPriceRange(
			lowOfDay + stripHeight * rangeIndex,
			lowOfDay + stripHeight * (rangeIndex + 1)
		);

		range.setStripProgress(day.from, day.to, volume / maxVolume);
	});

	const valueArea = findValueArea(levels, maxVolume);

	for (let candleIndex = day.from; candleIndex < day.to; candleIndex += 1) {
		valueAreaTop[candleIndex] = valueArea.topPrice;
		valueAreaBottom[candleIndex] = valueArea.bottomPrice;
		poc[candleIndex] = valueArea.pointOfControl;
	}

}


const chartHighestHigh = Math.max(...high);
const chartLowestLow = Math.min(...low);

const verticalMargin = (chartHighestHigh - chartLowestLow) / (90 * COLUMNS_NUMBER);

ranges.forEach((range, rangeIndex) => range.render(verticalMargin, NORMAL_COLUMN_COLOR, `Level${rangeIndex + 1}`));
paint(poc, { name: 'PoC', style: 'ladder', color: '#8b1cff' });

fill(
	paint(valueAreaTop, { name: 'Value/Top', style: 'ladder', color: '#1cc1ff' }),
	paint(valueAreaBottom, { name: 'Value/Bot', style: 'ladder', color: '#1cc1ff' }),
	'#1cc1ff',
	0.1,
	`Value area`
);

//	------------------------------------------------------------------------------------
//	God bless hoisting, functions go below
//	------------------------------------------------------------------------------------

//	BEWARE: this one behaves like a state machine, in a sense that it
//	has current price range (assigned via setCurrentPriceRange()) persisting
//	until it gets overwritten
function createVerticalRange(initialBottomPrice, initialTopPrice) {
	const top = series_of(null);
	const bottom = series_of(null);

	let bottomPrice = initialBottomPrice;
	let topPrice = initialTopPrice;

	return {
		setCurrentPriceRange(newBottomPrice, newTopPrice) {
			bottomPrice = newBottomPrice;
			topPrice = newTopPrice;
		},


		priceRange() {
			return {
				bottomPrice,
				topPrice
			};
		},


		setStripProgress(leftIndex, rightValuePointIndex, value) {
			let filledLength = Math.round(value * (rightValuePointIndex - leftIndex));

			if (filledLength <= 0) {
				return;
			}

			if (filledLength == rightValuePointIndex - leftIndex && rightValuePointIndex != time.length - 1) {
				filledLength -= 1;
			}

			top.splice(leftIndex, filledLength, ...[...Array(filledLength)].map(() => topPrice));
			bottom.splice(leftIndex, filledLength, ...[...Array(filledLength)].map(() => bottomPrice));
		},


		render(verticalMargin, color, title) {
			fill(
				paint(sub(top, verticalMargin), { hidden: true }),
				paint(add(bottom, verticalMargin), { hidden: true }),
				color,
				0.3,
				title
			);
		}
	};
}


function identifyDays() {
	const days = [];
	let dayStartIndex = 0;

	for (let candleIndex = 0; candleIndex < time.length; candleIndex +=1) {
		if (time_of(time[dayStartIndex]).dayOfYear != time_of(time[candleIndex]).dayOfYear) {
			days.push({
				from: dayStartIndex,
				to: candleIndex
			});

			dayStartIndex = candleIndex;
		}
	}

	if (dayStartIndex != time.length) {
		days.push({
			from: dayStartIndex,
			to: time.length
		});
	}

	return days;
}


//	BEWARE: cloned from pkg__volume-profile
function volumeAtPriceRange(timeFrameData, fromCandleIndex, toCandleIndex, bottomPrice, topPrice) {
	let result = 0;

	for (let candleIndex = fromCandleIndex; candleIndex < toCandleIndex; candleIndex += 1) {
		const candleLow = timeFrameData.low[candleIndex];
		const candleHigh = timeFrameData.high[candleIndex];

		if (candleLow == candleHigh) {
			continue;
		}

		const overlappingLength = (() => {
			if (candleLow == candleHigh || bottomPrice == topPrice) {
				return 0;
			}

			if (bottomPrice > candleHigh || topPrice < candleLow) {
				return 0;
			}

			if (topPrice <= candleHigh && bottomPrice >= candleLow) {
				return topPrice - bottomPrice;
			}

			if (candleHigh <= topPrice && candleLow >= bottomPrice) {
				return candleHigh - candleLow;
			}

			if (topPrice >= candleHigh && bottomPrice >= candleLow && bottomPrice <= candleHigh) {
				return candleHigh - bottomPrice;
			}

			if (bottomPrice <= candleLow && topPrice >= candleLow && topPrice <= candleHigh) {
				return topPrice - candleLow;
			}
		})();

 		const volumeFraction = overlappingLength / (candleHigh - candleLow);
 		result += timeFrameData.volume[candleIndex] * volumeFraction;
	}

	return result;
}


//	BEWARE: level go like [lowestPrice, lowerPrice, ...., higherPrice, highesPrrice]
//	so levels[0] is the level at the bottom of a range
function findValueArea(levels, maxVolume) {
	const totalVolume = levels.reduce((result, level) => result + level.volume, 0);
	let volumeAccumulated = maxVolume;

	let pointOfControlIndex = levels.findIndex(level => level.volume == maxVolume);
	let valueAreaTop = pointOfControlIndex;
	let valueAreaBottom = pointOfControlIndex;

	let steps = 0;

	do {
		const twoLevelsAboveVolume = levels.slice(valueAreaTop + 1, valueAreaTop + 3).reduce((result, level) => result + level.volume, 0);
		const twoLevelsBelowVolume = levels.slice(valueAreaBottom - 2, valueAreaBottom).reduce((result, level) => result + level.volume, 0);

		if (twoLevelsAboveVolume > twoLevelsBelowVolume) {
			volumeAccumulated += twoLevelsAboveVolume;
			valueAreaTop = Math.min(levels.length - 1, valueAreaTop + 2);
		}
		else {
			volumeAccumulated += twoLevelsBelowVolume;
			valueAreaBottom = Math.max(0, valueAreaBottom - 2);
		}

		steps += 1;

		if (steps > 10) {
			break;
		}
	}
	while (volumeAccumulated < VALUE_AREA_MIN_ACCUMULATED_VOLUME * totalVolume);

	return {
		topPrice: levels[valueAreaTop].range.priceRange().topPrice,
		pointOfControl: (levels[pointOfControlIndex].range.priceRange().bottomPrice + levels[pointOfControlIndex].range.priceRange().topPrice) / 2,
		bottomPrice: levels[valueAreaBottom].range.priceRange().bottomPrice
	};
}


function computeVbpFromLowerTimeFrameData(ranges, day, highOfDay, lowOfDay) {
	const dayStartTimestamp = time[day.from];
	const dayEndTimestamp = time[day.to];

	const levels = [];

	for (const range of ranges) {
		if (range.priceRange().bottomPrice > lowOfDay && range.priceRange().bottomPrice < highOfDay) {
			const volumeAtRange = volumeAtPriceRange(
				lowerTimeFrameData,
				binarySearch.lt(lowerTimeFrameData.time, dayStartTimestamp),
				binarySearch.ge(lowerTimeFrameData.time, dayEndTimestamp),
				range.priceRange().bottomPrice,
				range.priceRange().topPrice
			);

			levels.push({ range, volume: volumeAtRange });
		}
	}

	return levels;
}


function computeVbpFromSameTimeFrameData(ranges, day, highOfDay, lowOfDay) {
	const levels = [];

	for (const range of ranges) {
		if (range.priceRange().bottomPrice > lowOfDay && range.priceRange().bottomPrice < highOfDay) {
			levels.push({
				range,
				volume: volumeAtPriceRange(prices, day.from, day.to, range.priceRange().bottomPrice, range.priceRange().topPrice)
			});
		}
	}

	return levels;
}
</code>