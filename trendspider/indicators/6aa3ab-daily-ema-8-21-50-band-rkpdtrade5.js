<code x-ref="code" class="hljs" data-clipboard-text>// ============================================================================
// Daily EMA 8/21/50 Band [RKPDTRADE5]
// TrendSpider JavaScript
//
// True Daily EMA 8 / 21 / 50
//
// Defaults:
// Source = Close
// Offset = 0
//
// EMA 8  = Green solid line
// EMA 21 = Aqua solid line
// EMA 50 = Coral solid line
//
// EMA Band:
// Green = EMA 8 above EMA 21
// Red   = EMA 8 below EMA 21
// ============================================================================

describe_indicator(
    'Daily EMA 8/21/50 Band [RKPDTRADE5]',
    'price'
);


// ============================================================================
// INPUTS
// ============================================================================

const sourceInput = input.select(
    'Source',
    'Close',
    [
        'Close',
        'Open',
        'High',
        'Low',
        'HL2',
        'HLC3',
        'OHLC4'
    ]
);


const offset = input.number(
    'Offset',
    0,
    {
        min: -100,
        max: 100,
        step: 1
    }
);


// ============================================================================
// REQUEST DAILY DATA
// ============================================================================

const dailyData = await request.history(
    current.ticker,
    'D'
);


// ============================================================================
// DAILY SOURCE CALCULATIONS
// ============================================================================

const dailyHL2 = for_every(
    dailyData.high,
    dailyData.low,
    (h, l) => {

        if (
            h == null ||
            l == null
        ) {
            return null;
        }

        return (h + l) / 2;
    }
);


const dailyHLC3 = for_every(
    dailyData.high,
    dailyData.low,
    dailyData.close,
    (h, l, c) => {

        if (
            h == null ||
            l == null ||
            c == null
        ) {
            return null;
        }

        return (h + l + c) / 3;
    }
);


const dailyOHLC4 = for_every(
    dailyData.open,
    dailyData.high,
    dailyData.low,
    dailyData.close,
    (o, h, l, c) => {

        if (
            o == null ||
            h == null ||
            l == null ||
            c == null
        ) {
            return null;
        }

        return (
            o +
            h +
            l +
            c
        ) / 4;
    }
);


// ============================================================================
// SOURCE SELECTION
// ============================================================================

let dailySource = dailyData.close;


if (sourceInput === 'Open') {

    dailySource = dailyData.open;

}
else if (sourceInput === 'High') {

    dailySource = dailyData.high;

}
else if (sourceInput === 'Low') {

    dailySource = dailyData.low;

}
else if (sourceInput === 'HL2') {

    dailySource = dailyHL2;

}
else if (sourceInput === 'HLC3') {

    dailySource = dailyHLC3;

}
else if (sourceInput === 'OHLC4') {

    dailySource = dailyOHLC4;

}


// ============================================================================
// DAILY EMA CALCULATIONS
// ============================================================================

const dailyEMA8 = ema(
    dailySource,
    8
);


const dailyEMA21 = ema(
    dailySource,
    21
);


const dailyEMA50 = ema(
    dailySource,
    50
);


// ============================================================================
// MAP DAILY EMA VALUES TO CURRENT CHART
// ============================================================================

const ema8Landed = land_points_onto_series(
    dailyData.time,
    dailyEMA8,
    time
);


const ema21Landed = land_points_onto_series(
    dailyData.time,
    dailyEMA21,
    time
);


const ema50Landed = land_points_onto_series(
    dailyData.time,
    dailyEMA50,
    time
);


// ============================================================================
// HOLD DAILY VALUES BETWEEN DAILY BARS
// ============================================================================

const ema8Mapped = interpolate_sparse_series(
    ema8Landed,
    'constant'
);


const ema21Mapped = interpolate_sparse_series(
    ema21Landed,
    'constant'
);


const ema50Mapped = interpolate_sparse_series(
    ema50Landed,
    'constant'
);


// ============================================================================
// OFFSET FUNCTION
// ============================================================================

function offsetSeries(series, bars) {

    if (bars === 0) {
        return series;
    }

    const output = series_of(null);

    for (
        let i = 0;
        i < series.length;
        i++
    ) {

        const sourceIndex =
            i - bars;


        if (
            sourceIndex < 0 ||
            sourceIndex >= series.length
        ) {

            output[i] = null;

        }
        else {

            output[i] =
                series[sourceIndex];

        }
    }

    return output;
}


// ============================================================================
// APPLY OFFSET
// ============================================================================

const ema8 = offsetSeries(
    ema8Mapped,
    offset
);


const ema21 = offsetSeries(
    ema21Mapped,
    offset
);


const ema50 = offsetSeries(
    ema50Mapped,
    offset
);


// ============================================================================
// COLORS
// ============================================================================

const EMA8_COLOR =
    '#4CAF50';

const EMA21_COLOR =
    '#16B9D4';

const EMA50_COLOR =
    '#FF7A75';


// ============================================================================
// 8-DAY EMA — SOLID
// ============================================================================

paint(
    ema8,
    {
        name: '8-Day EMA',
        color: EMA8_COLOR,
        style: 'line',
        width: 2
    }
);


// ============================================================================
// 21-DAY EMA — SOLID
// ============================================================================

paint(
    ema21,
    {
        name: '21-Day EMA',
        color: EMA21_COLOR,
        style: 'line',
        width: 2
    }
);


// ============================================================================
// 50-DAY EMA — SOLID
// ============================================================================

paint(
    ema50,
    {
        name: '50-Day EMA',
        color: EMA50_COLOR,
        style: 'line',
        width: 2
    }
);


// ============================================================================
// EMA 8 / EMA 21 BAND
//
// Green = EMA 8 > EMA 21
// Red   = EMA 8 < EMA 21
// ============================================================================

color_cloud(
    ema8,
    ema21,
    'rgba(70,130,75,0.20)',
    'rgba(145,65,75,0.20)',
    'Bullish EMA Band',
    'Bearish EMA Band'
);


// ============================================================================
// BULLISH CROSS
// ============================================================================

const bullishCross = for_every(
    ema8,
    ema21,
    (fast, slow, _, index) => {

        if (index < 1) {
            return false;
        }


        const previousFast =
            ema8[index - 1];

        const previousSlow =
            ema21[index - 1];


        if (
            fast == null ||
            slow == null ||
            previousFast == null ||
            previousSlow == null
        ) {
            return false;
        }


        return (
            previousFast <= previousSlow &&
            fast > slow
        );
    }
);


// ============================================================================
// BEARISH CROSS
// ============================================================================

const bearishCross = for_every(
    ema8,
    ema21,
    (fast, slow, _, index) => {

        if (index < 1) {
            return false;
        }


        const previousFast =
            ema8[index - 1];

        const previousSlow =
            ema21[index - 1];


        if (
            fast == null ||
            slow == null ||
            previousFast == null ||
            previousSlow == null
        ) {
            return false;
        }


        return (
            previousFast >= previousSlow &&
            fast < slow
        );
    }
);


// ============================================================================
// TRENDSPIDER SIGNALS
// ============================================================================

register_signal(
    bullishCross,
    'Daily EMA 8 Cross Above EMA 21'
);


register_signal(
    bearishCross,
    'Daily EMA 8 Cross Below EMA 21'
);</code>