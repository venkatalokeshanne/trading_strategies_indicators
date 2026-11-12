<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Global Market Session Indicator');
const markets = [
    { name: 'Sydney', opening: 16, closing: 1 },
    { name: 'Tokyo', opening: 19, closing: 4 },
    { name: 'London', opening: 2, closing: 11 },
    { name: 'NY', opening: 8, closing: 17 }
].map(market => { return { ...market, enabled: input.boolean(market.name, true) } });
const marketsNames = markets.map(market => market.name);
const priceLevelsMarketIndex = marketsNames.indexOf(input.select('Levels of', 'None', ['None', ...marketsNames]));
const labels = series_of(null);
const openingTop = series_of(null);
const openingBottom = series_of(null);
const closingTop = series_of(null);
const closingBottom = series_of(null);
const newDayTop = series_of(null);
const newDayBottom = series_of(null);
const areaTop = 1e+3 * close[close.length - 1];
const checkTimeAndUpdateLines = (currentIndex, targetTime, name, topSeries, bottomSeries) => {
    if (
        time_of(time[currentIndex]).hours == targetTime &&
        time_of(time[currentIndex - 1]).hours != targetTime
    ) {
        labels[currentIndex] = name;
        topSeries[currentIndex - 1] = areaTop;
        topSeries[currentIndex] = areaTop;
        topSeries[currentIndex + 1] = areaTop;
        bottomSeries[currentIndex - 1] = -areaTop;
        bottomSeries[currentIndex] = -areaTop;
        bottomSeries[currentIndex + 1] = -areaTop;
        return true;
    }
    return false;
}
for (let candleIndex = 1; candleIndex < close.length - 1; candleIndex++) {
    for (let marketIndex = 0; marketIndex < markets.length; marketIndex++) {
        const { name, opening, closing, enabled } = markets[marketIndex];
        if (enabled) {
            if (checkTimeAndUpdateLines(candleIndex, opening, `${name}_O`, openingTop, openingBottom)) {
                markets[marketIndex].isOpen = true;
                markets[marketIndex].openIndex = candleIndex;
                markets[marketIndex].highIndex = candleIndex;
                markets[marketIndex].lowIndex = candleIndex;
            }
            if (checkTimeAndUpdateLines(candleIndex, closing, `${name}_C`, closingTop, closingBottom)) {
                markets[marketIndex].closeIndex = candleIndex;
                markets[marketIndex].isOpen = false;
            }
            if (markets[marketIndex].isOpen) {
                if (high[candleIndex] > high[markets[marketIndex].highIndex]) {
                    markets[marketIndex].highIndex = candleIndex;
                }
                if (low[candleIndex] < low[markets[marketIndex].lowIndex]) {
                    markets[marketIndex].lowIndex = candleIndex;
                }
            }
        }
    }
    checkTimeAndUpdateLines(candleIndex, 0, 'New24Hrs', newDayTop, newDayBottom);
}
paint(labels, {style: 'labels_above', name: 'Labels'});
fill(paint(openingTop, { hidden: true }), paint(openingBottom, { hidden: true }), 'darkGreen', undefined, 'Exchange Open');
fill(paint(closingTop, { hidden: true }), paint(closingBottom, { hidden: true }), 'red', undefined, 'Exchange Close');
fill(paint(newDayTop, { hidden: true }), paint(newDayBottom, { hidden: true }), 'black', undefined, 'New 24Hrs');
const levelsLines = {
    open: series_of(null),
    high: series_of(null),
    low: series_of(null),
    close: series_of(null)
};
let selectedMarketName = '';
if (priceLevelsMarketIndex !== -1) {
    const {openIndex, highIndex, lowIndex, closeIndex, name} = markets[priceLevelsMarketIndex];
    selectedMarketName = name;
    levelsLines.open = horizontal_line(open[openIndex], openIndex);
    levelsLines.high = horizontal_line(high[highIndex], highIndex);
    levelsLines.low = horizontal_line(low[lowIndex], lowIndex);
    levelsLines.close = horizontal_line(close[closeIndex], closeIndex);
}
paint_label_at_line(paint(levelsLines.open, { name: 'Open', color: 'black', style: 'dotted' }), close.length - 1, `${selectedMarketName} Open`);
paint_label_at_line(paint(levelsLines.high, { name: 'High', color: 'green', thickness: 2 }), close.length - 1, `${selectedMarketName} High`);
paint_label_at_line(paint(levelsLines.low, { name: 'Low', color: 'red', thickness: 2 }), close.length - 1, `${selectedMarketName} Low`);
paint_label_at_line(paint(levelsLines.close, { name: 'Close', color: 'black', style: 'dotted' }), close.length - 1, `${selectedMarketName} Close`);</code>