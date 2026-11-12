<code x-ref="code" class="hljs" data-clipboard-text>// This script had been cloned from "Earnings-to-Earnings VbP" at 28 Jun 2025, 22:11
describe_indicator('VbP from Earnings', { warmup: 200 });

const COLUMNS_NUMBER = 20;
const VALUE_AREA_MIN_ACCUMULATED_VOLUME = 0.7;
const NORMAL_COLUMN_COLOR = '#999';

const binarySearch = library('binary-search-bounds');

// Fetch earnings data
const earningsData = await request.earnings(current.ticker);
assert(!earningsData.error, `Error fetching earnings data: ${earningsData.error}`);

// Sort earnings data by timestamp in descending order
const sortedEarnings = earningsData.sort((a, b) => b.timestamp - a.timestamp);

// Find the most recent earnings date and the next upcoming one
const mostRecentEarnings = sortedEarnings.find(e => e.timestamp <= time[time.length - 1]);
const nextEarnings = sortedEarnings.find(e => e.timestamp > time[time.length - 1]);

assert(mostRecentEarnings, "No recent earnings data found");

const startIndex = binarySearch.ge(time, mostRecentEarnings.timestamp);
const endIndex = nextEarnings ? binarySearch.ge(time, nextEarnings.timestamp) : time.length;

const ranges = [...Array(COLUMNS_NUMBER)].map(() => createVerticalRange(0, 0));
const poc = series_of(null);
const valueAreaTop = series_of(null);
const valueAreaBottom = series_of(null);

const highOfPeriod = Math.max(...high.slice(startIndex, endIndex));
const lowOfPeriod = Math.min(...low.slice(startIndex, endIndex));
const stripHeight = (highOfPeriod - lowOfPeriod) / COLUMNS_NUMBER;

ranges.forEach((range, rangeIndex) => range.setCurrentPriceRange(
    lowOfPeriod + stripHeight * rangeIndex,
    lowOfPeriod + stripHeight * (rangeIndex + 1)
));

const levels = computeVbpFromSameTimeFrameData(ranges, { from: startIndex, to: endIndex }, highOfPeriod, lowOfPeriod);

if (levels.length > 0) {
    const maxVolume = Math.max(...levels.map(({ volume }) => volume));
    levels.forEach(({ range, volume }, rangeIndex) => {
        range.setCurrentPriceRange(
            lowOfPeriod + stripHeight * rangeIndex,
            lowOfPeriod + stripHeight * (rangeIndex + 1)
        );
        range.setStripProgress(startIndex, endIndex, volume / maxVolume);
    });

    const valueArea = findValueArea(levels, maxVolume);
    for (let candleIndex = startIndex; candleIndex < endIndex; candleIndex += 1) {
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

//  ------------------------------------------------------------------------------------
//  God bless hoisting, functions go below
//  ------------------------------------------------------------------------------------

//  BEWARE: this one behaves like a state machine, in a sense that it
//  has current price range (assigned via setCurrentPriceRange()) persisting
//  until it gets overwritten
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

//  BEWARE: cloned from pkg__volume-profile
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

//  BEWARE: level go like [lowestPrice, lowerPrice, ...., higherPrice, highesPrrice]
//  so levels[0] is the level at the bottom of a range
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
}</code>