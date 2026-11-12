<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Returns Overlay Table');

// Boolean inputs to toggle each row
const showDTD = input.boolean('Show Day-to-Date', true);
const showWTD = input.boolean('Show Week-to-Date', true);
const showMTD = input.boolean('Show Month-to-Date', true);
const showQTD = input.boolean('Show Quarter-to-Date', true);
const showYTD = input.boolean('Show Year-to-Date', true);
const show1Y = input.boolean('Show 1 Year', true);

// Get the current close price (last bar)
const myCurrentClose = close[close.length - 1];
const myCurrentTime = time[time.length - 1];

// Helper function to calculate return percentage
const calculateReturn = (_referenceValue) => {
    if (_referenceValue === null || _referenceValue === undefined || isNaN(_referenceValue)) {
        return null;
    }
    return ((myCurrentClose - _referenceValue) / _referenceValue) * 100;
};

// Helper function to format return value
const formatReturn = (_returnValue) => {
    if (_returnValue === null || isNaN(_returnValue)) {
        return 'N/A';
    }
    const mySign = _returnValue >= 0 ? '+' : '';
    return `${mySign}${_returnValue.toFixed(2)}%`;
};

// Helper function to get color for return value
const getReturnColor = (_returnValue) => {
    if (_returnValue === null || isNaN(_returnValue)) {
        return '#999999';
    }
    if (_returnValue > 0) {
        return '#12d962';
    } else if (_returnValue < 0) {
        return '#ff4444';
    } else {
        return '#cccccc';
    }
};

// Get current bar's time components
const myCurrentBarTime = time_of(myCurrentTime);

// DTD - Day-to-Date (from open of current day)
let myDtdReturn = null;
if (showDTD) {
    for (let i = 0; i < close.length; i++) {
        const myBarTime = time_of(time[i]);
        if (myBarTime.dayOfMonth === myCurrentBarTime.dayOfMonth &&
            myBarTime.month === myCurrentBarTime.month &&
            myBarTime.year === myCurrentBarTime.year) {
            myDtdReturn = calculateReturn(open[i]);
            break;
        }
    }
}

// Fetch daily data for WTD, MTD, YTD calculations
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

// WTD - Week-to-Date (last close before the start of current Mon-Sun week)
let myWtdReturn = null;
if (showWTD) {
    const moment = library('moment-timezone');
    const myCurrentMoment = moment(myCurrentTime * 1000);
    const myDow = myCurrentMoment.day();
    const myDaysFromMonday = (myDow === 0) ? 6 : (myDow - 1);
    const myCurrentMonday = moment(myCurrentTime * 1000).subtract(myDaysFromMonday, 'days').startOf('day');
    const myCurrentMondayTimestamp = myCurrentMonday.valueOf() / 1000;
    
    let myWtdAnchor = NaN;
    for (let i = myDailyData.time.length - 1; i >= 0; i--) {
        if (myDailyData.time[i] < myCurrentMondayTimestamp) {
            myWtdAnchor = myDailyData.close[i];
            break;
        }
    }
    
    myWtdReturn = calculateReturn(myWtdAnchor);
}

// MTD - Month-to-Date (last close before the 1st of current month)
let myMtdReturn = null;
if (showMTD) {
    const moment = library('moment-timezone');
    const myFirstOfMonth = moment(myCurrentTime * 1000).startOf('month');
    const myFirstOfMonthTimestamp = myFirstOfMonth.valueOf() / 1000;
    
    let myMtdAnchor = NaN;
    for (let i = myDailyData.time.length - 1; i >= 0; i--) {
        if (myDailyData.time[i] < myFirstOfMonthTimestamp) {
            myMtdAnchor = myDailyData.close[i];
            break;
        }
    }
    
    myMtdReturn = calculateReturn(myMtdAnchor);
}

// QTD - Quarter-to-Date (from close of last bar of previous quarter)
let myQtdReturn = null;
if (showQTD) {
    for (let i = myDailyData.time.length - 1; i >= 0; i--) {
        const myBarTime = time_of(myDailyData.time[i]);
        if (myBarTime.quarter < myCurrentBarTime.quarter ||
            myBarTime.year < myCurrentBarTime.year) {
            myQtdReturn = calculateReturn(myDailyData.close[i]);
            break;
        }
    }
}

// YTD - Year-to-Date (last close before Jan 1 of current year)
let myYtdReturn = null;
if (showYTD) {
    const moment = library('moment-timezone');
    const myFirstOfYear = moment(myCurrentTime * 1000).startOf('year');
    const myFirstOfYearTimestamp = myFirstOfYear.valueOf() / 1000;
    
    let myYtdAnchor = NaN;
    for (let i = myDailyData.time.length - 1; i >= 0; i--) {
        if (myDailyData.time[i] < myFirstOfYearTimestamp) {
            myYtdAnchor = myDailyData.close[i];
            break;
        }
    }
    
    myYtdReturn = calculateReturn(myYtdAnchor);
}

// 1Y - 1 Year (from bar 365 days ago)
let myOneYearReturn = null;
if (show1Y) {
    const myOneYearAgoTime = myCurrentTime - (365 * 24 * 60 * 60);
    let myClosestIndex = null;
    let myMinDiff = Infinity;
    
    for (let i = 0; i < time.length; i++) {
        const myDiff = Math.abs(time[i] - myOneYearAgoTime);
        if (myDiff < myMinDiff) {
            myMinDiff = myDiff;
            myClosestIndex = i;
        }
    }
    
    if (myClosestIndex !== null) {
        myOneYearReturn = calculateReturn(close[myClosestIndex]);
    }
}

// Build table rows - each row has label and value in single text
const myTableRows = [];

if (showDTD) {
    myTableRows.push({
        cells: [{
            text: `DTD: ${formatReturn(myDtdReturn)}`,
            color: myDtdReturn !== null ? getReturnColor(myDtdReturn) : '#e0e0e0',
            alignment: 'left',
            padding: '6px 12px'
        }]
    });
}

if (showWTD) {
    myTableRows.push({
        cells: [{
            text: `WTD: ${formatReturn(myWtdReturn)}`,
            color: myWtdReturn !== null ? getReturnColor(myWtdReturn) : '#e0e0e0',
            alignment: 'left',
            padding: '6px 12px'
        }]
    });
}

if (showMTD) {
    myTableRows.push({
        cells: [{
            text: `MTD: ${formatReturn(myMtdReturn)}`,
            color: myMtdReturn !== null ? getReturnColor(myMtdReturn) : '#e0e0e0',
            alignment: 'left',
            padding: '6px 12px'
        }]
    });
}

if (showQTD) {
    myTableRows.push({
        cells: [{
            text: `QTD: ${formatReturn(myQtdReturn)}`,
            color: myQtdReturn !== null ? getReturnColor(myQtdReturn) : '#e0e0e0',
            alignment: 'left',
            padding: '6px 12px'
        }]
    });
}

if (showYTD) {
    myTableRows.push({
        cells: [{
            text: `YTD: ${formatReturn(myYtdReturn)}`,
            color: myYtdReturn !== null ? getReturnColor(myYtdReturn) : '#e0e0e0',
            alignment: 'left',
            padding: '6px 12px'
        }]
    });
}

if (show1Y) {
    myTableRows.push({
        cells: [{
            text: `1Y: ${formatReturn(myOneYearReturn)}`,
            color: myOneYearReturn !== null ? getReturnColor(myOneYearReturn) : '#e0e0e0',
            alignment: 'left',
            padding: '6px 12px'
        }]
    });
}

// Paint the overlay table with comfortable padding from edges
paint_overlay(
    'Returns Table',
    { position: 'top_right', offset_x: -70, offset_y: 20 },
    {
        background_color: 'rgba(20, 20, 20, 0.85)',
        border_color: '#555555',
        border_width: 1,
        border_radius: 4,
        rows: myTableRows
    }
);</code>