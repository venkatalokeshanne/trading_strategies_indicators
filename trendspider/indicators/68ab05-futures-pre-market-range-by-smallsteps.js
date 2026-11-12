<code x-ref="code" class="hljs" data-clipboard-text>/* This indicator is designed for use with futures contracts such as MES1!, MNQ1!, and M2K1!. 
It plots the high and low of the pre-market (overnight) session and optionally highlights the corresponding candles.

To ensure accurate timing, adjust the Start and End times along with the local-to-Mountain Time offset based on your location. 
Note: The typical end minute is either 29 or 14.

Breakout and breakdown signals are generated when the price closes above or below the pre-market range lines. 
Caution: These signals may produce false positives.

I have been using this indicator for a while now, submitting to #TSBuild25 and TrendSpider store. */


describe_indicator('Futures pre-market range by SmallSteps', 'overlay');

// Check if the chart resolution is less than 120 minutes
assert(
    Number(current.resolution) < 120 || current.resolution.endsWith('S') || current.resolution.endsWith('T'),
    "This indicator only supports chart resolutions less than 120 minutes."
);

// Define NYSE market hours as input properties
const nyseStartHour = input.number('Start Hour', 17, { min: 0, max: 23 });
const nyseStartMinute = input.number('Start Minute', 0, { min: 0, max: 59 });
const nyseEndHour = input.number('End Hour', 8, { min: 0, max: 23 });
const nyseEndMinute = input.number('End Minute', 29, { min: 0, max: 59 });

// Create an input property for futures time which is 1 hour behind NY time
const useFuturesTime = input.boolean('Use Time Diff Cal', false, {hide_in_legend: true});
const localTimeDiff = input.number('local-Mountain Time Diff', 1, { min: 0, max: 11, hide_in_legend: true });

// Create input properties to display or hide breakdown and false breakout signals
const showBreakoutSignal = input.boolean('Breakout', true);
const showBreakdownSignal = input.boolean('Breakdown', true);

// New boolean input to decide whether to signal between the start and end time
const signalDuringRange = input.boolean('Signal pre-mkt', false, {hide_in_legend: true});
const colorCandles = input.boolean('Color pre-mkt', false);

// Function to adjust time based on the useFuturesTime input
function adjustTime(hour) {
    return useFuturesTime ? (hour - localTimeDiff + 24) % 24 : hour % 24;
}

// Initialize arrays to store candle colors and signals
const myCandleColors = series_of(null);
const myInRangeStartSignal = series_of(false);
const myInRangeEndSignal = series_of(false);

// Process each candle to determine if it's within the specified time range
for (let i = 0; i < time.length; i++) {
    const myDate = time_of(time[i]);
    const myStartHour = adjustTime(nyseStartHour);
    const myEndHour = adjustTime(nyseEndHour);

    // Check if the candle is within the specified time range
    let myInRange;
    if (myStartHour < myEndHour) {
        myInRange = 
            (myDate.hours > myStartHour || (myDate.hours === myStartHour && myDate.minutes >= nyseStartMinute)) &&
            (myDate.hours < myEndHour || (myDate.hours === myEndHour && myDate.minutes <= nyseEndMinute));
    } else {
        myInRange = 
            (myDate.hours > myStartHour || (myDate.hours === myStartHour && myDate.minutes >= nyseStartMinute)) ||
            (myDate.hours < myEndHour || (myDate.hours === myEndHour && myDate.minutes <= nyseEndMinute));
    }

    // Assign color to candles within the specified time range
    myCandleColors[i] = myInRange ? 'gray' : null;

    // Create signals for range start and end
    myInRangeStartSignal[i] = i > 0 && myCandleColors[i - 1] !== 'gray' && myCandleColors[i] === 'gray';
    myInRangeEndSignal[i] = i > 0 && myCandleColors[i - 1] === 'gray' && myCandleColors[i] !== 'gray';
}

if(colorCandles) {
    color_candles(myCandleColors);
}

// Initialize arrays to store high and low values
const myRangeHigh = series_of(null);
const myRangeLow = series_of(null);
let myCurrentHigh = null;
let myCurrentLow = null;
let myInRange = false;

// Process each candle to determine the high and low within the specified range
for (let i = 0; i < time.length; i++) {
    if (myInRangeStartSignal[i]) {
        myInRange = true;
        myCurrentHigh = high[i];
        myCurrentLow = low[i];
    } else if (myInRangeEndSignal[i]) {
        myInRange = false;
    }

    if (myInRange) {
        myCurrentHigh = Math.max(myCurrentHigh, high[i]);
        myCurrentLow = Math.min(myCurrentLow, low[i]);
        myRangeHigh[i] = myCurrentHigh;
        myRangeLow[i] = myCurrentLow;
    }
    
    if (!myInRange) {
        myCurrentHigh = null;
        myCurrentLow = null;
        myRangeHigh[i] = myRangeHigh[i-1];
        myRangeLow[i] = myRangeLow[i-1];
    }
}

// Paint the high and low lines
const onhPainted = paint(myRangeHigh, { color: 'gray', name: 'ON-High', style: 'ladder' }); 
paint_label_at_line(onhPainted, close.length - 10, 'on-H', { color: 'gray' });
const onlPainted = paint(myRangeLow, { color: 'gray', name: 'ON-Low', style: 'ladder' });
paint_label_at_line(onlPainted, close.length - 10, 'on-L', { color: 'gray' });

// Calculate breakdown signal using either of two previous candles' lower range
const myBreakdownSignal = for_every(close, high, low, myRangeLow, myCandleColors, (_c, _h, _l, _rl, _cc, _prevSignal, _index) => {
    if (_index < 2) return 0; // Not enough data for the first three candles
    
    // Check if we should signal during the range
    if (!signalDuringRange && _cc === 'gray') return 0;

    // Check if current close is below the lower band of all of the last. 
    if(_prevSignal === null || _prevSignal === 0 ) { 
        if( _c < myRangeLow[_index - 1] && _l < myRangeLow[_index - 1] 
           && (_h > myRangeLow[_index - 1]  ||  high[_index -1 ] > myRangeLow[_index - 2] )) {
            return 'S';
        }
    }
    return 0;
});

register_signal(myBreakdownSignal, 'Breakdown');

if (showBreakdownSignal) {
   paint(myBreakdownSignal, { style: 'labels_above', color: 'red', text: '▼', textColor: 'white', backgroundColor: 'rgba(255, 0, 0, 0.5)', name: 'Breakdown Signal'});
}

// Calculate breakout signal
const myBreakoutSignal = for_every(close, high, low, myRangeHigh, myCandleColors, (_c, _h, _l, _rh, _cc, _prevSignal, _index) => {
    if (_index < 2) return 0; // Not enough data for the first three candles
    
    // Check if we should signal during the range
    if (!signalDuringRange && _cc === 'gray') return 0;

    // Check if current close is above the upper band of all of the last. 
    if(_prevSignal === null || _prevSignal === 0 ) { 
        if( _c > myRangeHigh[_index - 1] && _h > myRangeHigh[_index - 1] 
           && (_l < myRangeHigh[_index - 1]  ||  low[_index -1 ] < myRangeHigh[_index - 2] )) {
            return 'L';
        }
    }
    return 0;
});

register_signal(myBreakoutSignal, 'Breakout');

if (showBreakoutSignal) {
    paint(myBreakoutSignal, { style: 'labels_below', color: 'green', text: '▲', textColor: 'white', backgroundColor: 'rgba(0, 255, 0, 0.5)', name: 'Breakout Signal'});
}
</code>