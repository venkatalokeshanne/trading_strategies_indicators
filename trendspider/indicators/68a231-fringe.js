<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Fringe™️');

const moment = library('moment-timezone');

// Add input options to toggle visibility of lines
const showDeviationLines = input.boolean('Show Deviation Lines', true);
const showFriday1600Line = input.boolean('Show Friday 16:00 Line', true);

// Function to check if a given timestamp is a Thursday after 18:00, Friday, or a Saturday following a Friday holiday
const isFridayRangeStart = (timestamp) => {
    const date = moment(timestamp * 1000);
    return (date.day() === 4 && date.hour() >= 18) || date.day() === 5 || (date.day() === 6 && date.subtract(1, 'day').day() === 5);
};

// Function to check if a given timestamp is Friday after 18:00
const isFridayRangeEnd = (timestamp) => {
    const date = moment(timestamp * 1000);
    return date.day() === 5 && date.hour() >= 18;
};

// Function to get the day of the week as text
const getDayOfWeek = (timestamp) => moment(timestamp * 1000).format('ddd');

// Function to check if a given timestamp is Friday at 16:00
const isFriday1600 = (timestamp) => {
    const date = moment(timestamp * 1000);
    return date.day() === 5 && date.hour() === 16 && date.minute() === 0;
};

// Initialize arrays for Friday's range
const fridayHigh = series_of(null);
const fridayLow = series_of(null);
const fridayMid = series_of(null);
const friday853 = series_of(null);
const friday147 = series_of(null);
const friday1111 = series_of(null);
const fridayMinus0111 = series_of(null);

// Initialize array for Friday 16:00 line
const friday1600Line = series_of(null);

let lastFridayRangeStartIndex = -1;
let currentFridayHigh = null;
let currentFridayLow = null;

// Initialize array for custom candle colors
const candleColors = series_of(null);

// Iterate through all candles
for (let i = 0; i < time.length; i++) {
    if (isFridayRangeStart(time[i])) {
        // If it's a new Friday range start, reset the range
        if (lastFridayRangeStartIndex === -1 || i - lastFridayRangeStartIndex > 1) {
            currentFridayHigh = high[i];
            currentFridayLow = low[i];
        } else {
            // Update the range for the current Friday
            currentFridayHigh = Math.max(currentFridayHigh, high[i]);
            currentFridayLow = Math.min(currentFridayLow, low[i]);
        }
        
        // Update the arrays
        fridayHigh[i] = currentFridayHigh;
        fridayLow[i] = currentFridayLow;
        fridayMid[i] = (currentFridayHigh + currentFridayLow) / 2;
        friday853[i] = currentFridayLow + (currentFridayHigh - currentFridayLow) * 0.853;
        friday147[i] = currentFridayLow + (currentFridayHigh - currentFridayLow) * 0.147;
        friday1111[i] = fridayMid[i] + (currentFridayHigh - currentFridayLow) * 1;
        fridayMinus0111[i] = fridayMid[i] - (currentFridayHigh - currentFridayLow) * 1;
        
        lastFridayRangeStartIndex = i;
    } else if (lastFridayRangeStartIndex !== -1 && !isFridayRangeEnd(time[i])) {
        // Extend the lines until the next Friday range start or end
        fridayHigh[i] = fridayHigh[lastFridayRangeStartIndex];
        fridayLow[i] = fridayLow[lastFridayRangeStartIndex];
        fridayMid[i] = fridayMid[lastFridayRangeStartIndex];
        friday853[i] = friday853[lastFridayRangeStartIndex];
        friday147[i] = friday147[lastFridayRangeStartIndex];
        friday1111[i] = friday1111[lastFridayRangeStartIndex];
        fridayMinus0111[i] = fridayMinus0111[lastFridayRangeStartIndex];
    }

    // Check if it's Friday at 16:00 and set the candle color to neon purple
    if (isFriday1600(time[i])) {
        candleColors[i] = '#FF00FF'; // Neon purple color
        friday1600Line[i] = close[i];
    } else if (i > 0 && friday1600Line[i - 1] !== null) {
        friday1600Line[i] = friday1600Line[i - 1];
    }
}

// Paint the lines
const highLine = paint(fridayHigh, { name: 'Fringe High', color: 'purple', style: 'line' });
paint(fridayMid, { name: 'Fringe Mid', color: 'purple', style: 'line' });
paint(fridayLow, { name: 'Fringe Low', color: 'purple', style: 'line' });
paint(friday853, { name: 'Fringe 85.3%', color: 'purple', style: 'line' });
paint(friday147, { name: 'Fringe 14.7%', color: 'purple', style: 'line' });

// Paint deviation lines only if showDeviationLines is true
if (showDeviationLines) {
    paint(friday1111, { name: 'Upper Deviation', color: 'blue', style: 'line' });
    paint(fridayMinus0111, { name: 'Lower Deviation', color: 'blue', style: 'line' });
}

// Paint Friday 16:00 line only if showFriday1600Line is true
if (showFriday1600Line) {
    paint(friday1600Line, { name: 'Friday 16:00', color: 'magenta', style: 'dotted' });
}

// Add day of the week labels
let lastDayOfWeek = '';
for (let i = 0; i < time.length; i++) {
    const dayOfWeek = getDayOfWeek(time[i]);
    if (dayOfWeek !== lastDayOfWeek) {
        paint_label_at_line(
            highLine,
            i,
            dayOfWeek,
            { color: 'gray', vertical_align: 'top' }
        );
        lastDayOfWeek = dayOfWeek;
    }
}

// Color the candles
color_candles(candleColors);
</code>