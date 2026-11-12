<code x-ref="code" class="hljs" data-clipboard-text>// Combined indicator: Opening Range, Pre-Market, Previous Day Levels, and High/Low of the Day
// Combines functionality from ORB_Levels and Hi_Lo_of_the_Day indicators

describe_indicator('Ultimate Key Levels', 'price', { 
    shortName: 'Ult Levels ' 
});

// Ensure the indicator does not work on Session, Daily, Weekly, Monthly, Quarterly, or Yearly charts
assert(
    !['D', 'W', 'M', 'Q', 'Y'].includes(constants.resolution),
    `not applicable to "${constants.resolution}" charts`
);

// ===== GLOBAL TOGGLE =====
const showLabels = input.boolean('Show Labels', false); // default: no labels

// ===== ORB INPUT FIELDS =====
const startHour   = input.number('ORB Start Hour',   9,  { min: 0, max: 23 });
const startMinute = input.number('ORB Start Minute', 30, { min: 0, max: 59 });
const endHour     = input.number('ORB End Hour',     10, { min: 0, max: 23 });
const endMinute   = input.number('ORB End Minute',   0,  { min: 0, max: 59 });

// ===== PREVIOUS DAY LEVELS INPUT FIELDS =====
const lookbackPeriod = input.number('Lookback Period', 1, { min: 1, max: 10 });

// ===== MARKET HOURS DEFINITION (for Hi/Lo of Day) =====
const marketOpen = { hours: 9, minutes: 30 };
const marketClose = { hours: 16, minutes: 0 };

// Function to check if a timestamp is within market hours
function isMarketHours(timestamp) {
    const timeOfDay = time_of(timestamp);
    return (
        (timeOfDay.hours > marketOpen.hours || (timeOfDay.hours === marketOpen.hours && timeOfDay.minutes >= marketOpen.minutes)) &&
        (timeOfDay.hours < marketClose.hours || (timeOfDay.hours === marketClose.hours && timeOfDay.minutes <= marketClose.minutes))
    );
}

// ===== PART 1: OPENING RANGE BANDS FUNCTIONALITY =====
function getOpeningRangeHighLow() {
    const openingRangeHighs = series_of(null);
    const openingRangeLows  = series_of(null);
    const labelIndices = { high: [], low: [] };
    let currentDay = null;
    let openingRangeHigh = -Infinity;
    let openingRangeLow  =  Infinity;
    let rangeSetTime = null;

    for (let i = 0; i < time.length; i++) {
        const date = time_of(time[i]);
        const day  = date.dayOfYear;

        // Reset for a new day
        if (day !== currentDay) {
            currentDay = day;
            openingRangeHigh = -Infinity;
            openingRangeLow  =  Infinity;
            rangeSetTime = null;
        }

        // Within user-defined ORB window
        if (
            (date.hours > startHour || (date.hours === startHour && date.minutes >= startMinute)) &&
            (date.hours < endHour   || (date.hours === endHour   && date.minutes <  endMinute))
        ) {
            if (high[i] > openingRangeHigh) openingRangeHigh = high[i];
            if (low[i]  < openingRangeLow)  openingRangeLow  = low[i];
        }

        // End of ORB window -> mark label index once
        if (date.hours === endHour && date.minutes === endMinute && !rangeSetTime) {
            rangeSetTime = time[i];
            labelIndices.high.push(i);
            labelIndices.low.push(i);
        }

        openingRangeHighs[i] = openingRangeHigh;
        openingRangeLows[i]  = openingRangeLow;
    }

    return { openingRangeHighs, openingRangeLows, labelIndices };
}

// ===== PART 2: PRE-MARKET RANGE FUNCTIONALITY =====
async function getPreMarketRange() {
    // 30 is the highest time frame which still has candles not overlapping with the market session
    const extHoursData = await request.history(constants.ticker, '30', { ext_session: true });
    assert(!extHoursData.error, `Error fetching data for ${constants.ticker}`);
    const preMarketRangeByDay = {};

    // Compute { high, low } of pre-market for each day in ext session
    for (let i = 0; i < extHoursData.time.length; i++) {
        const sessionAtCandle = session_of(
            extHoursData.time[i],
            constants.resolution,
            constants.ext_session_premarket
        );
        const dayOfCandle = sessionAtCandle.session;

        if (!preMarketRangeByDay[dayOfCandle]) {
            preMarketRangeByDay[dayOfCandle] = {
                high: extHoursData.high[i],
                low:  extHoursData.low[i]
            };
        } else {
            preMarketRangeByDay[dayOfCandle].high = Math.max(preMarketRangeByDay[dayOfCandle].high, extHoursData.high[i]);
            preMarketRangeByDay[dayOfCandle].low  = Math.min(preMarketRangeByDay[dayOfCandle].low,  extHoursData.low[i]);
        }
    }
    return preMarketRangeByDay;
}

// ===== PART 3: PREVIOUS DAY LEVELS FUNCTIONALITY =====
const dailyData = await request.history(constants.ticker, 'D');
assert(!dailyData.error, `Error fetching daily data: ${dailyData.error}`);

const highLevels  = series_of(null);
const lowLevels   = series_of(null);
const closeLevels = series_of(null);

for (let i = 0; i < lookbackPeriod; i++) {
    const dailyIndex = dailyData.close.length - 2 - i; // -2 to get the previous completed day
    if (dailyIndex >= 0) {
        const prevDayHigh  = dailyData.high[dailyIndex];
        const prevDayLow   = dailyData.low[dailyIndex];
        const prevDayClose = dailyData.close[dailyIndex];
        const startIndex   = time.findIndex(t => t >= dailyData.time[dailyIndex + 1]);

        if (startIndex !== -1) {
            for (let j = startIndex; j < time.length; j++) {
                highLevels[j]  = prevDayHigh;
                lowLevels[j]   = prevDayLow;
                closeLevels[j] = prevDayClose;
            }
        }
    }
}

// Function to find the beginning of the session
const findSessionStart = (index) => {
    const currentSession = session_of(time[index], constants.resolution);
    while (index > 0 && session_of(time[index - 1], constants.resolution).session === currentSession.session) {
        index--;
    }
    return index;
};

// ===== PART 4: HIGH/LOW OF THE DAY FUNCTIONALITY =====
const highOfDayByDay = {};
const lowOfDayByDay = {};
const highOfDayLabels = series_of(null);
const lowOfDayLabels = series_of(null);
const myNhodSignal = series_of(false);
const myNlodSignal = series_of(false);

// Compute high and low of the day for each trading session during normal market hours
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

// ===== CALCULATE ALL RANGES =====
const { openingRangeHighs, openingRangeLows, labelIndices } = getOpeningRangeHighLow();
const preMarketRangeByDay = await getPreMarketRange();

const rangeHigh = series_of(null);
const rangeLow  = series_of(null);
const lastSession = session_of(time[time.length - 1], constants.resolution);

// Assign pre-market high/low range to each candle
for (let i = 0; i < time.length; i++) {
    const sessionAtCandle = session_of(time[i], constants.resolution);
    const isLastSession   = sessionAtCandle.session == lastSession.session;
    const extHoursRange   = preMarketRangeByDay[sessionAtCandle.session];

    if (isLastSession && extHoursRange) {
        rangeHigh[i] = extHoursRange.high;
        rangeLow[i]  = extHoursRange.low;
    }

    if ((rangeHigh[i] != rangeHigh[i - 1]) || (rangeLow[i] != rangeLow[i - 1])) {
        rangeHigh[i - 1] = null;
        rangeLow[i - 1]  = null;
    }
}

// Create Hi/Lo of Day series
const hodRangeHigh = series_of(null);
const hodRangeLow = series_of(null);

for (let i = 0; i < time.length; i++) {
    const sessionAtCandle = bar_at(time[i], 'D');
    const dayOfCandle = sessionAtCandle.session;
    
    if (highOfDayByDay[dayOfCandle]) {
        hodRangeHigh[i] = highOfDayByDay[dayOfCandle].value;
    }
    
    if (lowOfDayByDay[dayOfCandle]) {
        hodRangeLow[i] = lowOfDayByDay[dayOfCandle].value;
    }
}

// ===== PAINT ALL INDICATORS ON THE CHART =====

// 1) ORB lines + fill
const orbHighLine = paint(openingRangeHighs, { style: 'line', color: '#bbbbbb', thickness: 0.5, name: 'OR High' });
const orbLowLine  = paint(openingRangeLows,  { style: 'line', color: '#bbbbbb', thickness: 0.5, name: 'OR Low'  });
fill(orbHighLine, orbLowLine, '#A3A3A3CC', 0.25, 'OR Range');

// ORB labels (gated by checkbox)
if (showLabels) {
    labelIndices.high.forEach(index => {
        paint_label_at_line(orbHighLine, index, 'ORBH', {
            color: 'white',
            background_color: 'green',
            vertical_align: 'middle'
        });
    });
    labelIndices.low.forEach(index => {
        paint_label_at_line(orbLowLine, index, 'ORBL', {
            color: 'white',
            background_color: 'red',
            vertical_align: 'middle'
        });
    });
}

// 2) Pre-market lines
const pmHighLine = paint(rangeHigh, { style: 'ladder', thickness: 1, color: 'palegreen', name: 'PM High' });
const pmLowLine  = paint(rangeLow,  { style: 'ladder', thickness: 1, color: 'pink',       name: 'PM Low'  });

// Pre-market labels (gated by checkbox)
if (showLabels) {
    paint_label_at_line(pmHighLine, close.length - 25, 'PMH', {
        color: 'black',
        background_color: 'palegreen',
        vertical_align: 'middle'
    });
    paint_label_at_line(pmLowLine, close.length - 25, 'PML', {
        color: 'black',
        background_color: 'pink',
        vertical_align: 'middle'
    });
}

// 3) Previous Day Levels - with default colors and dotted style
const prevDayHighLine = paint(highLevels,  { color: 'lime',  style: 'dotted',  name: 'Previous Day High',  thickness: 1.5 });
const prevDayLowLine  = paint(lowLevels,   { color: 'crimson',   style: 'dotted',   name: 'Previous Day Low',   thickness: 1.5 });
const prevDayCloseLine= paint(closeLevels, { color: 'DodgerBlue', style: 'dotted', name: 'Previous Day Close', thickness: 1.5 });

// Previous Day labels (gated by checkbox)
if (showLabels) {
    const sessionStartIndex = findSessionStart(close.length - 1);
    paint_label_at_line(prevDayHighLine,  sessionStartIndex, 'PDay H', { color: 'white', background_color: 'lime',  vertical_align: 'middle' });
    paint_label_at_line(prevDayLowLine,   sessionStartIndex, 'PDay L', { color: 'white', background_color: 'crimson',   vertical_align: 'middle' });
    paint_label_at_line(prevDayCloseLine, sessionStartIndex, 'PDay C', { color: 'white', background_color: 'DodgerBlue', vertical_align: 'middle' });
}

// 4) High/Low of the Day lines
paint(hodRangeHigh, { style: 'ladder', color: '#00FF00', thickness: .5, name: 'HOD' });
paint(hodRangeLow, { style: 'ladder', color: '#FF0000', thickness: .5, name: 'LOD' });

// Add labels at the highest or lowest point of each session (for current day only)
for (let day in highOfDayByDay) {
    if (highOfDayByDay.hasOwnProperty(day)) {
        const highPoint = highOfDayByDay[day];
        if (session_of(time[highPoint.index], constants.resolution).session === lastSession.session) {
            highOfDayLabels[highPoint.index] = `NHOD: ${highPoint.value.toFixed(2)}`;
        }
    }
}

for (let day in lowOfDayByDay) {
    if (lowOfDayByDay.hasOwnProperty(day)) {
        const lowPoint = lowOfDayByDay[day];
        if (session_of(time[lowPoint.index], constants.resolution).session === lastSession.session) {
            lowOfDayLabels[lowPoint.index] = `NLOD: ${lowPoint.value.toFixed(2)}`;
        }
    }
}

paint(highOfDayLabels, { style: 'labels_above', color: 'white', backgroundColor: 'green', backgroundOpacity: '.7' , verticalOffset: 10, name: 'NHOD Label' });
paint(lowOfDayLabels, { style: 'labels_below', color: 'white', backgroundColor: 'red', backgroundOpacity: '.7' ,verticalOffset: 10, name: 'NLOD Label' });

// Register signals for NHOD and NLOD
register_signal(myNhodSignal, 'New High of Day');
register_signal(myNlodSignal, 'New Low of Day');</code>