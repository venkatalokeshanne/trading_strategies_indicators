<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only
describe_indicator('Fair Value Gap with Labels and Toggle', 'price', { shortName: 'FVG' });
const gapFactor = input('Gap factor', 1, { min: 0.01, max: 50 });
const labelsValues = ['A','B','C','D','E','F','G','H','I','J'];
const whichToShow = labelsValues.map(label => input.boolean(`Show Gap ${label}`, true));
// An object containing all the necessary data for each gap
const gapObject = () => ({
    topPrice: null,
    bottomPrice: null,
    ascending: null,
    topLine: series_of(null),
    bottomLine: series_of(null),
    index: -1
});
const maxGaps = 10;
// An array with deep copies of the gap object. One for each gap
const gapArray = [];
// This array must have at least 10 gap objects to avoid errors when we have fewer gaps on the chart
for (let gapIndex = 0; gapIndex < maxGaps; gapIndex++) {
    gapArray.push(gapObject());
}
const gapBars = series_of(null);
const topDots = series_of(null);
const bottomDots = series_of(null);
let gapNumber = 10;
// When a new gap is needed we check if there is a free one or else we use the oldest one
const getAvailableGapIndex = () => {
    gapArray.push(gapObject());
    return gapNumber++;
};
const priceAtr = atr(14);
for (let candleIndex = 2; candleIndex < close.length; candleIndex++) {
    // Check if there is a gap
    const gapSize = priceAtr[candleIndex] !== null ? gapFactor * priceAtr[candleIndex] : null;
    const isUpGap =
        gapSize !== null &&
        low[candleIndex] - high[candleIndex - 2] > gapSize &&
        low[candleIndex] < high[candleIndex - 1] &&
        high[candleIndex - 2] > low[candleIndex - 1] &&
        high[candleIndex - 1] < high[candleIndex];
    const isDownGap =
        gapSize !== null &&
        low[candleIndex - 2] - high[candleIndex] > gapSize &&
        low[candleIndex - 2] < high[candleIndex - 1] &&
        high[candleIndex] > low[candleIndex - 1] &&
        low[candleIndex - 1] > low[candleIndex];
    if (isUpGap || isDownGap) {
        const availableGapIndex = getAvailableGapIndex();
        gapArray[availableGapIndex].index = candleIndex;
        if (isUpGap) {
            gapArray[availableGapIndex].ascending = true;
            gapArray[availableGapIndex].topPrice = low[candleIndex];
            gapArray[availableGapIndex].bottomPrice = high[candleIndex - 2];
        }
        else if (isDownGap) {
            gapArray[availableGapIndex].ascending = false;
            gapArray[availableGapIndex].topPrice = low[candleIndex - 2];
            gapArray[availableGapIndex].bottomPrice = high[candleIndex];
        }
        gapBars[candleIndex] = {
            high: gapArray[availableGapIndex].topPrice,
            low: gapArray[availableGapIndex].bottomPrice
        };
        topDots[candleIndex] = gapArray[availableGapIndex].topPrice;
        bottomDots[candleIndex] = gapArray[availableGapIndex].bottomPrice;
    }
    // Update the values of the gaps
    for (let gapIndex = 0; gapIndex < gapNumber; gapIndex++) {
        // Do not update values of already filled gaps
        if (gapArray[gapIndex].filled) {
            continue;
        }
        // Check if the gap should shrink due to wick entrance
        // Do not shrink if a new gap completely covers this one
        if (
            (high[candleIndex - 1] < gapArray[gapIndex].bottomPrice && low[candleIndex] > gapArray[gapIndex].topPrice) ||
            (low[candleIndex - 1] > gapArray[gapIndex].topPrice && high[candleIndex] < gapArray[gapIndex].bottomPrice)
        ) {
            // Toggle this gap direction since the price is now in the other side
            gapArray[gapIndex].ascending = !gapArray[gapIndex].ascending;
        }
        else if (gapArray[gapIndex].ascending && gapArray[gapIndex].topPrice > low[candleIndex]) {
            gapArray[gapIndex].topPrice = low[candleIndex];
        }
        else if (!gapArray[gapIndex].ascending && gapArray[gapIndex].bottomPrice < high[candleIndex]) {
            gapArray[gapIndex].bottomPrice = high[candleIndex];
        }
        // Remove gap if it is fully covered by the prices
        if (gapArray[gapIndex].topPrice <= gapArray[gapIndex].bottomPrice) {
            // Keep the latest values for the lines before removing current gap
            gapArray[gapIndex].topLine[candleIndex] = gapArray[gapIndex].topLine[candleIndex - 1];
            gapArray[gapIndex].bottomLine[candleIndex] = gapArray[gapIndex].bottomLine[candleIndex - 1];
            gapArray[gapIndex].filled = true;
        }
        else {
            // Update the lines of the gaps
            gapArray[gapIndex].topLine[candleIndex] = gapArray[gapIndex].topPrice;
            gapArray[gapIndex].bottomLine[candleIndex] = gapArray[gapIndex].bottomPrice;
        }
    }
}
// remove bars for older than last 'maxGaps' gaps.
for (let candleIndex = 0; candleIndex < gapArray[gapNumber - maxGaps].index - 1; candleIndex++) {
    gapBars[candleIndex] = {
        high: null,
        low: null
    };
    topDots[candleIndex] = null;
    bottomDots[candleIndex] = null;
}
whichToShow[9] && fill(
    paint(gapArray[gapNumber - maxGaps].topLine, { name: 'J/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps].bottomLine, { name: 'J/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'J'
);
whichToShow[8] && fill(
    paint(gapArray[gapNumber - maxGaps + 1].topLine, { name: 'I/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 1].bottomLine, { name: 'I/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'I'
);
whichToShow[7] && fill(
    paint(gapArray[gapNumber - maxGaps + 2].topLine, { name: 'H/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 2].bottomLine, { name: 'H/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'H'
);
whichToShow[6] && fill(
    paint(gapArray[gapNumber - maxGaps + 3].topLine, { name: 'G/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 3].bottomLine, { name: 'G/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'G'
);
whichToShow[5] && fill(
    paint(gapArray[gapNumber - maxGaps + 4].topLine, { name: 'F/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 4].bottomLine, { name: 'F/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'F'
);
whichToShow[4] && fill(
    paint(gapArray[gapNumber - maxGaps + 5].topLine, { name: 'E/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 5].bottomLine, { name: 'E/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'E'
);
whichToShow[3] && fill(
    paint(gapArray[gapNumber - maxGaps + 6].topLine, { name: 'D/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 6].bottomLine, { name: 'D/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'D'
);
whichToShow[2] && fill(
    paint(gapArray[gapNumber - maxGaps + 7].topLine, { name: 'C/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 7].bottomLine, { name: 'C/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'C'
);
whichToShow[1] && fill(
    paint(gapArray[gapNumber - maxGaps + 8].topLine, { name: 'B/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 8].bottomLine, { name: 'B/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'B'
);
whichToShow[0] && fill(
    paint(gapArray[gapNumber - maxGaps + 9].topLine, { name: 'A/Top', color: '#1b65bf', ignoreWhenScaling: true }),
    paint(gapArray[gapNumber - maxGaps + 9].bottomLine, { name: 'A/Bot', color: '#1b65bf', ignoreWhenScaling: true }),
    '#1b65bf',
    undefined,
    'A'
);
// remove bars for disabled gaps
gapArray.slice(-maxGaps).forEach(
    (x,i) => {
        if (!whichToShow[maxGaps - i - 1]) {
            gapBars[x.index] = null;
            topDots[x.index] = null;
            bottomDots[x.index] = null;
        };
    }
);
paint(gapBars, { name: 'Gap Bar', style: 'columnrange' });
// Keep the reference to these dots to paint the labels above them
const topDotsRef = paint(topDots, { name: 'Top Dots', color: 'black', style: 'dotted', thickness: 3 });
paint(bottomDots, { name: 'Bottom Dots', color: 'black', style: 'dotted', thickness: 3 });
// Add labels to the gaps
labelsValues.reverse();
gapArray.slice(-maxGaps).forEach(
    (x,i) => {
        if (whichToShow[maxGaps - i - 1]) {
            // paint labels on enabled gaps
            paint_label_at_line(
                topDotsRef,
                x.index,
                labelsValues[i],
                {
                    border_width: '1px',
                    border_color: 'black',
                    border_radius: '50%',
                    background_color: 'white'
                }
            );
        };
    }
);</code>