<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ripster Trend Labels', 'price');

// This indicator displays Ripster-style trend labels based on:
// 1) Price vs TODAY'S pre-market high/low (Price Action label)
// 2) Price vs 34/50 cloud proxy (EMA 50)  (Ripster Clouds 34/50 label)
// 3) Price vs 5/12 cloud proxy (EMA 12)   (Ripster Clouds 5/12 label)

//--------------------------------------------------------
// Inputs
//--------------------------------------------------------
const myShowPremarketLevels = input.boolean('Show Premarket Levels', false);
const myShowCloud3450       = input.boolean('Show 34/50 Cloud', false);
const myShowCloud512        = input.boolean('Show 5/12 Cloud', false);

//--------------------------------------------------------
// 1) Fetch intraday data for EMAs (10-minute, with extended hours)
//--------------------------------------------------------
const myData = await request.history(current.ticker, '10', { ext_session: true });
assert(!myData.error, `Error fetching 10-min data: ${myData.error}`);

// Compute EMAs for the clouds
const myEma50 = ema(myData.close, 50); // 34/50 proxy + actual 50
const myEma12 = ema(myData.close, 12); // 5/12 proxy + actual 12
const myEma34 = ema(myData.close, 34);
const myEma5  = ema(myData.close, 5);

const myLastIndex    = myData.close.length - 1;
const myCurrentPrice = myData.close[myLastIndex];
const myCurrentEma50 = myEma50[myLastIndex];
const myCurrentEma12 = myEma12[myLastIndex];

//--------------------------------------------------------
// 2) Compute TODAY'S pre-market high/low using official pattern
//--------------------------------------------------------
// 30 is the highest timeframe that still has candles not overlapping with
// the regular market session.
const extHoursData = await request.history(constants.ticker, '30', { ext_session: true });
assert(!extHoursData.error, `Error fetching 30-min ext hours data: ${extHoursData.error}`);

const preMarketRangeByDay = {};

// First, compute {high, low} of pre-market per each day in extended session data
for (let extHoursIndex = 0; extHoursIndex < extHoursData.time.length; extHoursIndex += 1) {
    const sessionAtCandle = session_of(
        extHoursData.time[extHoursIndex],
        constants.resolution,
        constants.ext_session_premarket
    );
    const dayOfCandle = sessionAtCandle.session;

    if (!preMarketRangeByDay[dayOfCandle]) {
        preMarketRangeByDay[dayOfCandle] = {
            high: extHoursData.high[extHoursIndex],
            low:  extHoursData.low[extHoursIndex]
        };
    } else {
        preMarketRangeByDay[dayOfCandle].high = Math.max(
            preMarketRangeByDay[dayOfCandle].high,
            extHoursData.high[extHoursIndex]
        );
        preMarketRangeByDay[dayOfCandle].low = Math.min(
            preMarketRangeByDay[dayOfCandle].low,
            extHoursData.low[extHoursIndex]
        );
    }
}

// Determine today's (last session's) pre-market range
const lastSession           = session_of(time[time.length - 1], constants.resolution);
const todaysPremarketRange  = preMarketRangeByDay[lastSession.session];

let myPremarketHigh;
let myPremarketLow;

// If we have a valid premarket range for today, use it.
// Otherwise, fall back to anchoring on current price so logic doesn't break.
if (todaysPremarketRange) {
    myPremarketHigh = todaysPremarketRange.high;
    myPremarketLow  = todaysPremarketRange.low;
} else {
    myPremarketHigh = myCurrentPrice;
    myPremarketLow  = myCurrentPrice;
}

//--------------------------------------------------------
// 3) Price Action label logic (today's pre-market only)
//--------------------------------------------------------
// - Bullish Trend: price > today's pre-market high
// - Bearish Trend: price < today's pre-market low
// - Chop Range:    price inside today's pre-market range
let myPriceAction;
if (myCurrentPrice > myPremarketHigh) {
    myPriceAction = 'Bullish Trend';
} else if (myCurrentPrice < myPremarketLow) {
    myPriceAction = 'Bearish Trend';
} else {
    myPriceAction = 'Chop Range';
}

//--------------------------------------------------------
// 4) Ripster Cloud labels (simple EMA proxies)
//--------------------------------------------------------
const myRipsterCloud1 = myCurrentPrice > myCurrentEma50 ? 'Bullish' : 'Bearish';
const myRipsterCloud2 = myCurrentPrice > myCurrentEma12 ? 'Bullish' : 'Bearish';

//--------------------------------------------------------
// 5) Colors
//--------------------------------------------------------
const myBullishColor    = '#12d962';
const myBearishColor    = '#ff4976';
const myNeutralColor    = '#f0b90b';
const myBackgroundColor = '#008080';
const myTextColor       = '#FFFFFF';

//--------------------------------------------------------
// 6) Paint today's pre-market high and low as horizontal levels
//    starting only from today's regular session start
//--------------------------------------------------------
const todaySessionStart = lastSession.session;
let sessionStartIndex   = null;

for (let i = 0; i < time.length; i += 1) {
    const candleSession = session_of(time[i], constants.resolution);
    if (candleSession.session === todaySessionStart) {
        sessionStartIndex = i;
        break;
    }
}

const myPremarketHighSeries = series_of(null);
const myPremarketLowSeries  = series_of(null);

if (myShowPremarketLevels && sessionStartIndex !== null) {
    for (let i = sessionStartIndex; i < time.length; i += 1) {
        myPremarketHighSeries[i] = myPremarketHigh;
        myPremarketLowSeries[i]  = myPremarketLow;
    }
}

paint(myPremarketHighSeries, {
    name: 'Premarket High',
    color: myBullishColor,
    style: 'dotted',
    width: 2
});

paint(myPremarketLowSeries, {
    name: 'Premarket Low',
    color: myBearishColor,
    style: 'dotted',
    width: 2
});

//--------------------------------------------------------
// 7) Land the EMA clouds onto the current chart timeframe
//--------------------------------------------------------
const myEma34Landed = land_points_onto_series(myData.time, myEma34, time, 'ge');
const myEma34Interpolated = interpolate_sparse_series(myEma34Landed, 'constant');

const myEma50Landed = land_points_onto_series(myData.time, myEma50, time, 'ge');
const myEma50Interpolated = interpolate_sparse_series(myEma50Landed, 'constant');

const myEma5Landed = land_points_onto_series(myData.time, myEma5, time, 'ge');
const myEma5Interpolated = interpolate_sparse_series(myEma5Landed, 'constant');

const myEma12Landed = land_points_onto_series(myData.time, myEma12, time, 'ge');
const myEma12Interpolated = interpolate_sparse_series(myEma12Landed, 'constant');

//--------------------------------------------------------
// 8) Paint the EMA clouds
//--------------------------------------------------------
// 34/50 Cloud
const myEma34ToPaint = myShowCloud3450 ? myEma34Interpolated : series_of(null);
const myEma50ToPaint = myShowCloud3450 ? myEma50Interpolated : series_of(null);

const myLine34 = paint(myEma34ToPaint, {
    name: 'EMA 34',
    color: '#2196F3',
    style: 'line',
    width: 2
});

const myLine50 = paint(myEma50ToPaint, {
    name: 'EMA 50',
    color: '#9C27B0',
    style: 'line',
    width: 2
});

// Always call fill; if series are null, nothing shows.
// This ensures fill is present when the indicator is saved with the option enabled.
fill(myLine34, myLine50, '#2196F3', 0.2);

// 5/12 Cloud
const myEma5ToPaint  = myShowCloud512 ? myEma5Interpolated  : series_of(null);
const myEma12ToPaint = myShowCloud512 ? myEma12Interpolated : series_of(null);

const myLine5 = paint(myEma5ToPaint, {
    name: 'EMA 5',
    color: '#FF9800',
    style: 'line',
    width: 2
});

const myLine12 = paint(myEma12ToPaint, {
    name: 'EMA 12',
    color: '#4CAF50',
    style: 'line',
    width: 2
});

// Same here: always call fill.
fill(myLine5, myLine12, '#FF9800', 0.2);

//--------------------------------------------------------
// 9) Overlay table
//--------------------------------------------------------
paint_overlay('Ripster Trend Labels v2', { position: 'top_right', order: 'above_all' }, {
    paddingLeft: 20,
    paddingRight: 70,
    paddingTop: 2,
    paddingBottom: 10,
    rows: [
        {
            cells: [
                {
                    text: 'Price Action',
                    color: myTextColor,
                    background: myBackgroundColor,
                    padding: '5px 10px',
                    fontSize: '14px'
                },
                {
                    text: myPriceAction,
                    color: 'black',
                    background:
                        myPriceAction === 'Bullish Trend'
                            ? myBullishColor
                            : myPriceAction === 'Bearish Trend'
                            ? myBearishColor
                            : myNeutralColor,
                    padding: '5px 10px',
                    fontWeight: 'bold',
                    fontSize: '14px'
                }
            ]
        },
        {
            cells: [
                {
                    text: 'Ripster Clouds 34/50',
                    color: myTextColor,
                    background: myBackgroundColor,
                    padding: '5px 10px',
                    fontSize: '14px'
                },
                {
                    text: myRipsterCloud1,
                    color: 'black',
                    background: myRipsterCloud1 === 'Bullish' ? myBullishColor : myBearishColor,
                    padding: '5px 10px',
                    fontWeight: 'bold',
                    fontSize: '14px'
                }
            ]
        },
        {
            cells: [
                {
                    text: 'Ripster Clouds 5/12',
                    color: myTextColor,
                    background: myBackgroundColor,
                    padding: '5px 10px',
                    fontSize: '14px'
                },
                {
                    text: myRipsterCloud2,
                    color: 'black',
                    background: myRipsterCloud2 === 'Bullish' ? myBullishColor : myBearishColor,
                    padding: '5px 10px',
                    fontWeight: 'bold',
                    fontSize: '14px'
                }
            ]
        }
    ]
});</code>