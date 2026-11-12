<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only. 
describe_indicator("Zig Zag Channel with Settings");
let position = input.select('Position', 'auto', ['auto', 0, 1, 2, 3, 4, 5]);
const depth = input.number('Depth', 20);
const deviation = input.number('Deviation', 1);
const backstep = input.number('Backstep', 2);
// Get zig zag points with the default parameters
const zigZagPointsObject = zigzag_points(depth, deviation, backstep);
// Define the series in which we will merge the high and low zigzag points
const zigZagPoints = series_of(null);
// Assign the high value in the indexes of high zig zag points
zigZagPointsObject.highIndexes.forEach(pointIndex => zigZagPoints[pointIndex] = high[pointIndex]);
// Assign the low value in the indexes of low zig zag points
zigZagPointsObject.lowIndexes.forEach(pointIndex => zigZagPoints[pointIndex] = low[pointIndex]);
// Connect the points with lines
const zigZagLine = interpolate_sparse_series(zigZagPoints);
// Get indexed points of Zig Zag so that we can get the points
const indexedPointsOfZigZag = indexed_points_of(zigZagPoints);
assert(indexedPointsOfZigZag && indexedPointsOfZigZag.length > 3, `Not enough zig zag points. Try loading more candles or changing timeframe`);
const computeChannel = position => {
    assert(position < indexedPointsOfZigZag.length - 3, `Not enough zig zag points for this position. Try lower position number.`);
    // Get the points
    const A = indexedPointsOfZigZag[indexedPointsOfZigZag.length - position - 3];
    const B = indexedPointsOfZigZag[indexedPointsOfZigZag.length - position - 2];
    const C = indexedPointsOfZigZag[indexedPointsOfZigZag.length - position - 1];
    // Get start index
    const startIndex = A.candleIndex;
    
    // Compute line starting from A and through C
    const line1 = line(A.candleIndex, A.value, C.candleIndex, C.value);
    
    // Compute distance between the line and the B Zig Zag point
    const distanceBetweenLineACandB = B.value - line1[B.candleIndex];
    
    // Compute second line
    const line2 = add(line1, distanceBetweenLineACandB);
    
    // Compute middle line
    const middleLine = add(line1, distanceBetweenLineACandB / 2);
    
    // Compute quarter lines
    const line3 = add(line1, distanceBetweenLineACandB / 4);
    const line4 = add(line1, 3 * distanceBetweenLineACandB / 4);
    
    
    // Rename lines according to their position
    let topLine = [];
    let bottomLine = [];
    let upperQuarterLine = [];
    let lowerQuarterLine = [];
    const APointIsHigh = A.value > B.value;
    
    if (APointIsHigh) {
        topLine = line1;
        bottomLine = line2;
        upperQuarterLine = line3;
        lowerQuarterLine = line4;
    } else {
        topLine = line2;
        bottomLine = line1;
        upperQuarterLine = line4;
        lowerQuarterLine = line3;
    }
    return {topLine, bottomLine, upperQuarterLine, lowerQuarterLine, middleLine, startIndex};
}
let channelObject = {};
if (position == 'auto') {
    const lastIndex = close.length - 1;
    position = 0;
    while (position < indexedPointsOfZigZag.length - 3) {
        const testChannel = computeChannel(position + 1);
        const lastCloseIsNotInTheChannel = (testChannel.topLine[lastIndex] < close[lastIndex]) || (testChannel.bottomLine[lastIndex] > close[lastIndex]);
        if (lastCloseIsNotInTheChannel) {
            break;
        }
        position++;
    }
}
channelObject = computeChannel(position);
const {topLine, bottomLine, upperQuarterLine, lowerQuarterLine, middleLine, startIndex} = computeChannel(position);
const topLineRef = paint(topLine, 'Top Line', 'red');
const bottomLineRef = paint(bottomLine, 'Bottom Line', 'green');
    
fill(
    topLineRef,
    bottomLineRef,
    'blue',
    0.1
)
const middleLineRef = paint(middleLine, 'Middle Line', 'grey');
const upperQuarterLineRef = paint(upperQuarterLine, 'Upper Quarter Line', 'red');
const lowerQuarterLineRef = paint(lowerQuarterLine, 'Lower Quarter Line', 'green');
paint(zigZagLine, 'ZigZag Line', 'black');
// Paint projections
const getProjectionSeries = originalLine =>
    add(shift(originalLine, -startIndex), originalLine[originalLine.length-1] - originalLine[startIndex]);
fill(
    paint_projection(topLineRef, getProjectionSeries(topLine)),
    paint_projection(bottomLineRef, getProjectionSeries(bottomLine)),
    'blue',
    0.1
)
paint_projection(middleLineRef, getProjectionSeries(middleLine));
paint_projection(upperQuarterLineRef, getProjectionSeries(upperQuarterLine));
paint_projection(lowerQuarterLineRef, getProjectionSeries(lowerQuarterLine));</code>