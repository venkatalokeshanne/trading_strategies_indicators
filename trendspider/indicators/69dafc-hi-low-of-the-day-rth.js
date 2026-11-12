<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Hi/Low of the Day RTH');

// Auto-detect asset type — crypto skips RTH filter
const isCrypto = (current.assetType !== 'stock' && current.assetType !== 'etf');

// Initialize variables for High of the Day
const highOfDayByDay = {};
const highOfDayLabels = series_of(null);

// Initialize variables for Low of the Day
const lowOfDayByDay = {};
const lowOfDayLabels = series_of(null);

// Define market hours (9:30 AM to 4:00 PM ET) — only used for stocks/ETFs
const marketOpen = { hours: 9, minutes: 30 };
const marketClose = { hours: 16, minutes: 0 };

// Function to check if a timestamp is within market hours
function isMarketHours(timestamp) {
    if (isCrypto) return true; // Crypto trades 24/7, all bars count
    const timeOfDay = time_of(timestamp);
    return (
        (timeOfDay.hours > marketOpen.hours || (timeOfDay.hours === marketOpen.hours && timeOfDay.minutes >= marketOpen.minutes)) &&
        (timeOfDay.hours < marketClose.hours || (timeOfDay.hours === marketClose.hours && timeOfDay.minutes <= marketClose.minutes))
    );
}

// Initialize signal series
const myNhodSignal = series_of(false);
const myNlodSignal = series_of(false);

// Compute high and low of the day for each trading session
for (let i = 0; i < time.length; i++) {
    const sessionAtCandle = bar_at(time[i], 'D');
    const dayOfCandle = sessionAtCandle.session;
    
    if (isMarketHours(time[i])) {
        // High of the Day calculation
        if (!highOfDayByDay[dayOfCandle]) {
            highOfDayByDay[dayOfCandle] = { value: high[i], index: i };
            myNhodSignal[i] = true;
        } else {
            if (high[i] > highOfDayByDay[dayOfCandle].value) {
                highOfDayByDay[dayOfCandle] = { value: high[i], index: i };
                myNhodSignal[i] = true;
            }
        }
        
        // Low of the Day calculation
        if (!lowOfDayByDay[dayOfCandle]) {
            lowOfDayByDay[dayOfCandle] = { value: low[i], index: i };
            myNlodSignal[i] = true;
        } else {
            if (low[i] < lowOfDayByDay[dayOfCandle].value) {
                lowOfDayByDay[dayOfCandle] = { value: low[i], index: i };
                myNlodSignal[i] = true;
            }
        }
    }
}

// Draw horizontal lines for high and low of the day
const rangeHigh = series_of(null);
const rangeLow = series_of(null);

for (let i = 0; i < time.length; i++) {
    const sessionAtCandle = bar_at(time[i], 'D');
    const dayOfCandle = sessionAtCandle.session;
    
    if (highOfDayByDay[dayOfCandle]) {
        rangeHigh[i] = highOfDayByDay[dayOfCandle].value;
    }
    
    if (lowOfDayByDay[dayOfCandle]) {
        rangeLow[i] = lowOfDayByDay[dayOfCandle].value;
    }
}

// Paint the horizontal lines
paint(rangeHigh, { style: 'ladder', color: '#07DD05', thickness: 1, name: 'NHOD' });
paint(rangeLow, { style: 'ladder', color: 'red', thickness: 1, name: 'NLOD' });

// Add labels at the highest or lowest point of the LAST session only
const lastSession = session_of(time[time.length - 1], constants.resolution);

for (let day in highOfDayByDay) {
    if (highOfDayByDay.hasOwnProperty(day)) {
        const highPoint = highOfDayByDay[day];
        if (session_of(time[highPoint.index], constants.resolution).session === lastSession.session) {
            highOfDayLabels[highPoint.index] = 'NHOD: ' + highPoint.value.toFixed(2);
        }
    }
}

for (let day in lowOfDayByDay) {
    if (lowOfDayByDay.hasOwnProperty(day)) {
        const lowPoint = lowOfDayByDay[day];
        if (session_of(time[lowPoint.index], constants.resolution).session === lastSession.session) {
            lowOfDayLabels[lowPoint.index] = 'NLOD: ' + lowPoint.value.toFixed(2);
        }
    }
}

paint(highOfDayLabels, { style: 'labels_above', color: 'white', backgroundColor: 'green', verticalOffset: 10, name: 'Hi Label' });
paint(lowOfDayLabels, { style: 'labels_below', color: 'white', backgroundColor: 'red', verticalOffset: 10, name: 'Lo Label' });

// Register signals for NHOD and NLOD
register_signal(myNhodSignal, 'New High of Day');
register_signal(myNlodSignal, 'New Low of Day');
</code>