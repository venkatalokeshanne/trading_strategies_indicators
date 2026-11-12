<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only
describe_indicator('Engulfing Levels');

// Find the engulfings
const bodyTop = max_of(open, close);
const bodyBottom = min_of(open, close);
const bodyEngulfings = for_every(bodyTop, shift(bodyTop, 1), bodyBottom, shift(bodyBottom, 1), (bt, pbt, bb, pbb) => bt > pbt && bb < pbb);

// This contains the number of areas we want to paint.
let numberOfRemainingAreas = 5;

// Start looping from the last candle since we want to paint the last 5 areas
for (let candleIndex = bodyEngulfings.length - 1; candleIndex > 0; candleIndex--) {
    // if the element of bodyEngulfings is true it means that we have an engulfing on this index
    // we also check that we haven't painted more than 5 areas yet
    if (bodyEngulfings[candleIndex] && numberOfRemainingAreas > 0) {
        // Determine the color based on whether the candle is green or red
        const fillColor = close[candleIndex] >= open[candleIndex] ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 0, 0, 0.2)';
        
        // Here we paint the areas. Each line should have different name. This is why we added the index of the area in the name
        fill(
            paint(horizontal_line(high[candleIndex], candleIndex), { name: `Top line ${numberOfRemainingAreas}`, color: 'blue' }),
            paint(horizontal_line(low[candleIndex], candleIndex), { name: `Bottom line ${numberOfRemainingAreas}`, color: 'blue' }),
            fillColor
        );
        
        // Reduce the remaining areas number
        numberOfRemainingAreas--;
    }
}

// This may look strange but just in case we have less than 5 engulfings we must paint the remaining lines even if they are empty
// The indicator can work without it but our saved indicator may not.
while(numberOfRemainingAreas > 0) {
    fill(
        paint(constants.empty_series, { name: `Top line ${numberOfRemainingAreas}`, color: 'blue' }),
        paint(constants.empty_series, { name: `Bottom line ${numberOfRemainingAreas}`, color: 'blue' }),
        'rgba(0, 0, 0, 0)' // Transparent fill for empty areas
    );
    numberOfRemainingAreas--;
}
</code>