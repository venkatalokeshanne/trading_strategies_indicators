<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Liquidity Levels', 'price', { shortName: 'Liquidity' });

// Find the high and low william's fractals
const fractalHigh = fractal_high(high, 51);
const fractalLow = fractal_low(low, 51);

// These variables contain the maximum number of lines we want to paint
let remainingTopLines = 5;
let remainingBottomLines = 5;

// Start from the last candle to first, since we want to paint the latest lines
for (let candleIndex = high.length - 1; candleIndex >= 0; candleIndex--) {
    // If this candle's index fractal isn't 'null', there is a fractal. Also check if it haven't reached the maximum number of lines
    if (fractalHigh[candleIndex] !== null && remainingTopLines > 0) {
        // paint a horizontal line with value the high of the fractal candle that starts at this index
        paint(horizontal_line(high[candleIndex], candleIndex), 'Top line ' + remainingTopLines, 'red');
        // since we painted one line reduce the number of the remaining top lines
        remainingTopLines--;
    }
    // do the same for low
    if (fractalLow[candleIndex] !== null && remainingBottomLines > 0) {
        paint(horizontal_line(low[candleIndex], candleIndex), 'Bottom line ' + remainingBottomLines, 'green');
        remainingBottomLines--;
    }
}

// if we haven't reached the maximum number of lines paint empty series for the rest of the lines
while (remainingTopLines > 0) {
    paint(series_of(null), 'Top line ' + remainingTopLines, 'red');
    remainingTopLines--;
}

while (remainingBottomLines > 0) {
    paint(series_of(null), 'Bottom line ' + remainingBottomLines, 'red');
    remainingBottomLines--;
}</code>